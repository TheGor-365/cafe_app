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

    if valid_credentials?(params['username'], params['password'])
      return [303, security_headers.merge(
        'Location' => '/',
        'Set-Cookie' => cookie(SESSION_COOKIE, new_token('session', SESSION_TTL), SESSION_TTL)
      ), []]
    end

    login_page(error: 'Incorrect access credentials.', status: 401)
  rescue ArgumentError
    bad_request
  end

  def bad_request
    [400, security_headers.merge('Content-Type' => 'text/plain; charset=utf-8'), ['Invalid request']]
  end

  def too_large
    [413, security_headers.merge('Content-Type' => 'text/plain; charset=utf-8'), ['Request too large']]
  end

  def login_page(error: nil, status: 200)
    csrf = new_token('csrf', CSRF_TTL)
    message = error ? "<p class=\"error\">#{Rack::Utils.escape_html(error)}</p>" : ''
    html = <<~HTML
      <!doctype html>
      <html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Gor's Coffee — Private preview</title>
      <style>
        *{box-sizing:border-box}body{margin:0;background:#16171b;color:#f7f6f2;font:16px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;display:grid;min-height:100vh;place-items:center;padding:22px}
        main{background:#202127;border:1px solid #3e3b36;max-width:420px;width:100%;border-radius:18px;padding:32px;box-shadow:0 20px 50px #0005}
        h1{font-size:29px;margin:0 0 8px;color:#eac18a}p{color:#bbb8b2}label{display:block;font-weight:600;margin:20px 0 6px}
        input{width:100%;background:#131418;border:1px solid #64615b;color:#fff;padding:13px;border-radius:9px;font:inherit}
        button{width:100%;margin-top:26px;background:#dbac70;color:#211810;border:0;border-radius:9px;font-weight:700;font-size:16px;padding:14px;cursor:pointer}
        .small{font-size:13px;margin:16px 0 0}.error{color:#ffaaa0}
      </style></head><body><main>
        <h1>Gor's Coffee</h1><p>Private portfolio preview / Закрытая демонстрация</p>
        #{message}
        <form method="post" action="#{LOGIN_PATH}" autocomplete="off">
          <input type="hidden" name="csrf" value="#{csrf}">
          <label for="username">Username / Логин</label>
          <input id="username" name="username" required autocomplete="username">
          <label for="password">Password / Пароль</label>
          <input id="password" type="password" name="password" required autocomplete="current-password">
          <button type="submit">Enter preview / Войти</button>
        </form>
        <p class="small">Use access credentials configured for cafe-web in Railway. All orders are fictional.</p>
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
