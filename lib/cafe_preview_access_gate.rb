# Browser-friendly authentication for the isolated, private Railway preview.
# The unsupported legacy Rails stack must not be exposed without this gate.
require 'rack/request'
require 'rack/utils'
require 'base64'
require 'securerandom'
require 'openssl'

class CafePreviewAccessGate
  HEALTH_PATH = '/__cafe_health'.freeze
  LOGIN_PATH = '/__cafe_access'.freeze
  LOGIN_DESTINATIONS = {
    'register' => '/users/sign_up',
    'sign_in' => '/users/sign_in',
    'browse' => '/'
  }.freeze
  SESSION_COOKIE = '__Host-cafe_preview'.freeze
  CSRF_COOKIE = '__Host-cafe_preview_csrf'.freeze
  SESSION_TTL = 8 * 60 * 60
  CSRF_TTL = 10 * 60
  MAX_BODY_BYTES = 4096

  def initialize(app, username:, password:, secret:)
    unless password.to_s.bytesize >= 24 && secret.to_s.bytesize >= 32
      raise ArgumentError, 'Private preview requires a 24+ byte password and a 32+ byte signing secret'
    end
    @app = app
    @username = username.to_s
    @password = password.to_s
    # A password rotation invalidates all previously issued preview cookies.
    @key = OpenSSL::HMAC.digest('SHA256', secret.to_s, "cafe-preview-session-v1:#{@password}")
  end

  def call(env)
    request = Rack::Request.new(env)
    return healthcheck if request.get? && request.path_info == HEALTH_PATH
    return @app.call(env) if authorized?(request)
    return login(request) if request.post? && request.path_info == LOGIN_PATH

    # No WWW-Authenticate challenge: Chrome was repeatedly retrying HTTP 401.
    return login_page if request.get? || request.head?

    [403, security_headers.merge('Content-Type' => 'text/plain; charset=utf-8'), ['Forbidden']]
  end

  private

  def authorized?(request)
    valid_token?(request.cookies[SESSION_COOKIE], 'session') ||
      valid_basic?(request.get_header('HTTP_AUTHORIZATION'))
  end

  def valid_basic?(header)
    return false unless header.to_s.start_with?('Basic ')
    encoded = header.split(' ', 2)[1]
    return false if encoded.to_s.empty? || encoded.to_s.bytesize > 2048
    user, pass = Base64.strict_decode64(encoded).split(':', 2)
    valid_credentials?(user, pass)
  rescue ArgumentError, TypeError
    false
  end

  def valid_credentials?(user, pass)
    return false unless user.is_a?(String) && pass.is_a?(String)
    return false if user.bytesize > 512 || pass.bytesize > 512
    equal?(user, @username) && equal?(pass, @password)
  end

  def equal?(a, b)
    Rack::Utils.secure_compare(
      OpenSSL::Digest::SHA256.digest(a.to_s),
      OpenSSL::Digest::SHA256.digest(b.to_s)
    )
  end

  def login(request)
    return too_large if request.content_length.to_i > MAX_BODY_BYTES
    return bad_request unless request.media_type == 'application/x-www-form-urlencoded'

    body = request.body.read(MAX_BODY_BYTES + 1)
    return too_large if body.bytesize > MAX_BODY_BYTES
    params = Rack::Utils.parse_nested_query(body)

    csrf = params['csrf']
    cookie_token = request.cookies[CSRF_COOKIE]
    unless csrf.is_a?(String) && cookie_token.is_a?(String) &&
           valid_token?(cookie_token, 'csrf') && equal?(csrf, cookie_token)
      return login_page(error: 'Session expired. Reload this page.', status: 403)
    end

    intent = LOGIN_DESTINATIONS.key?(params['intent']) ? params['intent'] : 'browse'
    if valid_credentials?(params['username'], params['password'])
      return [303, security_headers.merge(
        'Location' => LOGIN_DESTINATIONS.fetch(intent),
        'Set-Cookie' => cookie(SESSION_COOKIE, new_token('session', SESSION_TTL), SESSION_TTL)
      ), []]
    end

    login_page(error: 'Incorrect preview credentials.', status: 401, intent: intent)
  rescue ArgumentError
    bad_request
  end

  def bad_request
    [400, security_headers.merge('Content-Type' => 'text/plain; charset=utf-8'), ['Invalid request']]
  end

  def too_large
    [413, security_headers.merge('Content-Type' => 'text/plain; charset=utf-8'), ['Request too large']]
  end

  def login_page(error: nil, status: 200, intent: 'register')
    csrf = new_token('csrf', CSRF_TTL)
    message = error ? "<p class=\"error\" role=\"alert\">#{Rack::Utils.escape_html(error)}</p>" : ''
    html = <<~HTML
      <!doctype html>
      <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Private Preview Access | Gor's Coffee</title>
        <style>
          *{box-sizing:border-box}
          body{margin:0;background:radial-gradient(circle at 10% 0%,#30251f 0,#17171b 47%,#131419 100%);
            color:#f7f2eb;font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif;
            min-height:100vh;display:grid;place-items:center;padding:24px}
          main{max-width:460px;width:100%;background:#242127;border:1px solid #504239;
            border-radius:20px;padding:clamp(24px,5vw,38px);box-shadow:0 24px 75px #0007}
          .eyebrow{margin:0;color:#e4b977;letter-spacing:.16em;text-transform:uppercase;
            font-size:12px;font-weight:800}
          h1{font-size:clamp(29px,5vw,36px);letter-spacing:-.04em;line-height:1.2;margin:13px 0 10px;color:#f6d4a3}
          p{color:#d2c8bf;margin:0 0 18px}
          .step{background:#342e2c;color:#e5d5c2;border-left:3px solid #daa866;
            border-radius:7px;padding:11px 13px;font-size:14px;margin:24px 0}
          label{display:block;font-weight:700;margin:19px 0 6px;font-size:14px}
          input{width:100%;background:#141419;border:1px solid #766b62;color:#fff;
            padding:13px 14px;border-radius:9px;font:inherit;min-height:48px}
          input:focus-visible,button:focus-visible{outline:3px solid #f2c98b;outline-offset:3px}
          .actions{display:grid;gap:10px;margin-top:23px}
          button{min-height:48px;border:0;border-radius:9px;font:inherit;font-weight:750;cursor:pointer;padding:12px}
          .primary{background:#e3b774;color:#22170f}
          .primary:hover{background:#f0c78c}
          .secondary{background:transparent;border:1px solid #af9583;color:#f5e8d5}
          .secondary:hover{background:#392f2c}
          .small{font-size:13px;color:#bbaea2;line-height:1.65;margin:19px 0 0}
          .error{color:#ffbeb2;font-weight:600;margin:10px 0}
          @media(max-width:420px){body{padding:12px}main{padding:25px 21px}}
        </style>
      </head>
      <body><main>
        <p class="eyebrow">Portfolio demo · Private access</p>
        <h1>Gor's Coffee</h1>
        <p>Explore the coffee shop, create your own demo account, or sign in to an existing one.</p>
        <div class="step"><strong>Step 1 of 2 — Unlock this private preview.</strong>
          These are the preview access credentials configured in Railway, not your café account email and password.</div>
        #{message}
        <form method="post" action="#{LOGIN_PATH}" autocomplete="off">
          <input type="hidden" name="csrf" value="#{csrf}">
          <label for="username">Preview access username</label>
          <input id="username" name="username" required autocomplete="off" maxlength="512">
          <label for="password">Preview access password</label>
          <input id="password" type="password" name="password" required autocomplete="off" maxlength="512">
          <div class="actions">
            <button class="primary" type="submit" name="intent" value="register">Create a demo account</button>
            <button class="secondary" type="submit" name="intent" value="sign_in">Sign in to my account</button>
            <button class="secondary" type="submit" name="intent" value="browse">Browse as a guest</button>
          </div>
        </form>
        <p class="small"><strong>Step 2:</strong> After unlocking, you will go directly to registration, sign-in or the sample menu. For a new account, choose your own email and password. No real orders or payments.</p>
      </main></body></html>
    HTML
    [status, security_headers.merge(
      'Content-Type' => 'text/html; charset=utf-8',
      'Set-Cookie' => cookie(CSRF_COOKIE, csrf, CSRF_TTL)
    ), [html]]
  end

  def new_token(purpose, ttl)
    data = "#{Time.now.to_i + ttl}:#{SecureRandom.hex(20)}"
    encoded = Base64.urlsafe_encode64(data, padding: false)
    mac = OpenSSL::HMAC.hexdigest('SHA256', @key, "#{purpose}:#{encoded}")
    "#{encoded}.#{mac}"
  end

  def valid_token?(token, purpose)
    return false unless token.is_a?(String) && token.bytesize.between?(70, 256)
    encoded, mac = token.split('.', 2)
    return false unless encoded && mac && mac.match?(/\A[0-9a-f]{64}\z/)
    expected = OpenSSL::HMAC.hexdigest('SHA256', @key, "#{purpose}:#{encoded}")
    return false unless Rack::Utils.secure_compare(mac, expected)
    expires, nonce = Base64.urlsafe_decode64(encoded).split(':', 2)
    return false unless expires && nonce &&
                        expires.match?(/\A\d{10}\z/) && nonce.match?(/\A[0-9a-f]{40}\z/)
    expires.to_i > Time.now.to_i
  rescue ArgumentError
    false
  end

  def cookie(name, value, ttl)
    "#{name}=#{value}; Path=/; Max-Age=#{ttl}; Secure; HttpOnly; SameSite=Strict"
  end

  def security_headers
    {
      'Cache-Control' => 'no-store',
      'Referrer-Policy' => 'no-referrer',
      'X-Content-Type-Options' => 'nosniff',
      'Content-Security-Policy' => "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    }
  end

  def healthcheck
    ActiveRecord::Base.connection.select_value('SELECT 1')
    [200, { 'Content-Type' => 'text/plain; charset=utf-8', 'Cache-Control' => 'no-store' }, ['ok']]
  rescue StandardError
    [503, { 'Content-Type' => 'text/plain; charset=utf-8', 'Cache-Control' => 'no-store' }, ['unavailable']]
  end
end
