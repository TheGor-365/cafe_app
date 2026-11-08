# One-step browser authentication for the isolated Railway portfolio preview.
# Devise remains the source of truth for user credentials and sessions.
# No second shared preview password or HTTP Basic challenge is presented.
require 'rack/request'
require 'rack/utils'
require 'base64'
require 'securerandom'
require 'openssl'

class CafePreviewAccessGate
  HEALTH_PATH = '/__cafe_health'.freeze
  SESSION_COOKIE = '__Host-cafe_preview'.freeze
  SESSION_TTL = 8 * 60 * 60

  PUBLIC_PAGES = {
    '/users/sign_in' => ['GET', 'HEAD', 'POST'],
    '/users/sign_up' => ['GET', 'HEAD'],
    '/users' => ['POST'],
    '/users/password/new' => ['GET', 'HEAD'],
    '/users/password/edit' => ['GET', 'HEAD'],
    '/users/password' => ['POST', 'PUT', 'PATCH']
  }.freeze
  PUBLIC_ASSETS = %r{\A/(?:assets|packs)/[a-zA-Z0-9_./%+-]+\z}.freeze
  STATIC_PATHS = %w[/favicon.svg /favicon.ico /robots.txt].freeze

  def initialize(app, secret:)
    raise ArgumentError, 'A 32+ byte preview signing secret is required' if secret.to_s.bytesize < 32
    @app = app
    @key = OpenSSL::HMAC.digest('SHA256', secret.to_s, 'cafe-browser-preview-v2')
  end

  def call(env)
    request = Rack::Request.new(env)
    return healthcheck if request.get? && request.path_info == HEALTH_PATH

    # Existing signed-in users can visit their app without another gate.
    # Devise continues to authorize every admin and account action.
    return pass_authenticated(env, request) if valid_token?(request.cookies[SESSION_COOKIE])

    return @app.call(env) if public_asset?(request)
    return route_to_devise(env, request) if public_devise?(request)
    return landing if request.get? || request.head?

    [403, headers('text/plain; charset=utf-8'), ['Sign in required']]
  end

  private

  def pass_authenticated(env, request)
    status, response_headers, body = @app.call(env)
    # Signing out invalidates the browser preview authorization too.
    if request.path_info == '/users/sign_out' && %w[POST DELETE].include?(request.request_method)
      return [status, append_cookie(response_headers, expired_cookie), body]
    end
    [status, response_headers, body]
  end

  def route_to_devise(env, request)
    status, response_headers, body = @app.call(env)
    warden = env['warden']

    # Issue the preview cookie only AFTER Devise authenticates the user's
    # actual account. Failed sign-in, invalid CSRF and invalid signup never pass.
    if warden && warden.authenticated?(:user)
      return [status, append_cookie(response_headers, session_cookie), body]
    end

    [status, response_headers, body]
  end

  def public_devise?(request)
    (PUBLIC_PAGES[request.path_info] || []).include?(request.request_method)
  end

  def public_asset?(request)
    return false unless request.get? || request.head?
    STATIC_PATHS.include?(request.path_info) || PUBLIC_ASSETS.match?(request.path_info)
  end

  def landing
    html = <<~HTML
      <!doctype html>
      <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="theme-color" content="#211b17">
        <title>Welcome | Gor's Coffee</title>
        <style>
          *{box-sizing:border-box}
          body{margin:0;background:radial-gradient(circle at 15% 10%,#463125 0,#1b1819 53%,#121316 100%);
            color:#f5f0e9;font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif;min-height:100vh;
            display:grid;place-items:center;padding:20px}
          main{max-width:460px;width:100%;background:#272021;border:1px solid #6a4c37;
            border-radius:22px;padding:clamp(25px,5vw,39px);box-shadow:0 20px 65px #0008}
          .brand{display:flex;align-items:center;gap:12px;color:#f2ce99}
          .mark{display:grid;place-items:center;background:#af7c48;border-radius:10px;color:white;
            width:44px;height:44px;font-size:14px;font-weight:800}
          .brand h1{font-size:27px;letter-spacing:-.03em;margin:0}
          h2{font-size:32px;letter-spacing:-.035em;line-height:1.15;margin:35px 0 15px}
          p{color:#d3c6b8;margin:0 0 22px}
          .choices{display:grid;gap:12px;margin:26px 0}
          a{display:flex;min-height:53px;align-items:center;justify-content:center;text-decoration:none;
            border-radius:10px;font-weight:750;font-size:16px}
          .primary{background:#ecc18a;color:#28190f}
          .secondary{border:1px solid #b39276;color:#f4dfc5}
          a:focus-visible{outline:3px solid #ecc18a;outline-offset:4px}
          .note{font-size:12px;color:#b9aca0;border-top:1px solid #55483f;padding-top:18px;margin:0}
        </style>
      </head>
      <body><main>
        <header class="brand"><span class="mark">GC</span><h1>Gor's Coffee</h1></header>
        <h2>Your coffee corner.</h2>
        <p>Sign in to continue, or create an account to explore the menu and manage your orders.</p>
        <nav class="choices" aria-label="Account access">
          <a class="primary" href="/users/sign_in">Sign in</a>
          <a class="secondary" href="/users/sign_up">Create account</a>
        </nav>
        <p class="note">Portfolio project. No real purchases or payments.</p>
      </main></body></html>
    HTML
    [200, headers('text/html; charset=utf-8'), [html]]
  end

  def headers(content_type)
    {
      'Content-Type' => content_type,
      'Cache-Control' => 'no-store',
      'Referrer-Policy' => 'no-referrer',
      'X-Content-Type-Options' => 'nosniff',
      'Content-Security-Policy' => "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'"
    }
  end

  def session_cookie
    expiry = Time.now.to_i + SESSION_TTL
    data = Base64.urlsafe_encode64("#{expiry}:#{SecureRandom.hex(20)}", padding: false)
    mac = OpenSSL::HMAC.hexdigest('SHA256', @key, "session:#{data}")
    "#{SESSION_COOKIE}=#{data}.#{mac}; Path=/; Max-Age=#{SESSION_TTL}; Secure; HttpOnly; SameSite=Lax"
  end

  def expired_cookie
    "#{SESSION_COOKIE}=; Path=/; Max-Age=0; Secure; HttpOnly; SameSite=Lax"
  end

  def append_cookie(original, cookie)
    h = original.dup
    k = h.keys.find { |key| key.to_s.downcase == 'set-cookie' } || 'Set-Cookie'
    existing = h[k]
    h[k] = existing.nil? || existing.to_s.empty? ? cookie : "#{existing}\n#{cookie}"
    h
  end

  def valid_token?(token)
    return false unless token.is_a?(String) && token.bytesize.between?(70, 256)
    data, mac = token.split('.', 2)
    return false unless data && mac && mac.match?(/\A[0-9a-f]{64}\z/)

    expected = OpenSSL::HMAC.hexdigest('SHA256', @key, "session:#{data}")
    return false unless Rack::Utils.secure_compare(mac, expected)

    expiry, nonce = Base64.urlsafe_decode64(data).split(':', 2)
    expiry.to_s.match?(/\A\d{10}\z/) &&
      nonce.to_s.match?(/\A[0-9a-f]{40}\z/) && expiry.to_i > Time.now.to_i
  rescue ArgumentError
    false
  end

  def healthcheck
    ActiveRecord::Base.connection.select_value('SELECT 1')
    [200, { 'Content-Type' => 'text/plain; charset=utf-8', 'Cache-Control' => 'no-store' }, ['ok']]
  rescue StandardError
    [503, { 'Content-Type' => 'text/plain; charset=utf-8', 'Cache-Control' => 'no-store' }, ['unavailable']]
  end
end
