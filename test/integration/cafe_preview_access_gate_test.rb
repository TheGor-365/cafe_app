require 'test_helper'
require 'base64'
require_relative '../../lib/cafe_preview_access_gate'

class CafePreviewAccessGateTest < ActiveSupport::TestCase
  def setup
    downstream = ->(_env) { [200, { 'Content-Type' => 'text/plain' }, ['demo']] }
    @gate = CafePreviewAccessGate.new(
      downstream,
      username: 'portfolio',
      password: 'local-test-password-123456789',
      secret: 'ci-only-preview-cookie-signing-secret-123456'
    )
    @request = Rack::MockRequest.new(@gate)
  end

  test 'anonymous browser gets a login page, not a repeated 401 Basic challenge' do
    response = @request.get('/')
    assert_equal 200, response.status
    assert_includes response.body, 'Private portfolio preview'
    assert_includes response.body, 'name="csrf"'
    assert_nil response['WWW-Authenticate']
    assert_includes response['Set-Cookie'], 'Secure'
    assert_includes response['Set-Cookie'], 'HttpOnly'
    assert_includes response['Set-Cookie'], 'SameSite=Strict'
    refute_includes response.body, 'local-test-password'
  end

  test 'incorrect HTTP Basic credentials never reach the Rails app' do
    header = 'Basic ' + Base64.strict_encode64('portfolio:wrong-password')
    response = @request.get('/menu', 'HTTP_AUTHORIZATION' => header)
    assert_equal 200, response.status
    refute_equal 'demo', response.body
    assert_nil response['WWW-Authenticate']
  end

  test 'existing valid HTTP Basic credentials still reach Rails for test clients' do
    header = 'Basic ' + Base64.strict_encode64('portfolio:local-test-password-123456789')
    response = @request.get('/menu', 'HTTP_AUTHORIZATION' => header)
    assert_equal 200, response.status
    assert_equal 'demo', response.body
  end

  test 'browser login sets a signed Secure HttpOnly cookie and grants access' do
    page = @request.get('/')
    csrf = page.body[/name="csrf" value="([^"]+)"/, 1]
    assert csrf
    csrf_cookie = page['Set-Cookie'].split(';').first

    login = @request.post(CafePreviewAccessGate::LOGIN_PATH,
      'CONTENT_TYPE' => 'application/x-www-form-urlencoded',
      'HTTP_COOKIE' => csrf_cookie,
      :input => Rack::Utils.build_query(
        csrf: csrf, username: 'portfolio', password: 'local-test-password-123456789'
      ))
    assert_equal 303, login.status
    assert_equal '/', login['Location']
    assert_includes login['Set-Cookie'], 'Secure'
    assert_includes login['Set-Cookie'], 'HttpOnly'

    session_cookie = login['Set-Cookie'].split(';').first
    response = @request.get('/menu', 'HTTP_COOKIE' => session_cookie)
    assert_equal 200, response.status
    assert_equal 'demo', response.body

    tampered = @request.get('/menu', 'HTTP_COOKIE' => session_cookie + 'x')
    assert_includes tampered.body, 'Private portfolio preview'
  end

  test 'browser form rejects missing csrf without reaching the application' do
    response = @request.post(CafePreviewAccessGate::LOGIN_PATH,
      'CONTENT_TYPE' => 'application/x-www-form-urlencoded',
      :input => Rack::Utils.build_query(
        username: 'portfolio', password: 'local-test-password-123456789'
      ))
    assert_equal 403, response.status
    refute_equal 'demo', response.body
  end

  test 'browser form rejects wrong credentials and never repeats a Basic challenge' do
    page = @request.get('/')
    csrf = page.body[/name="csrf" value="([^"]+)"/, 1]
    response = @request.post(CafePreviewAccessGate::LOGIN_PATH,
      'CONTENT_TYPE' => 'application/x-www-form-urlencoded',
      'HTTP_COOKIE' => page['Set-Cookie'].split(';').first,
      :input => Rack::Utils.build_query(csrf: csrf, username: 'portfolio', password: 'wrong'))
    assert_equal 401, response.status
    assert_nil response['WWW-Authenticate']
    assert_includes response.body, 'Incorrect access credentials'
  end

  test 'the DB health probe remains accessible without credentials' do
    response = @request.get(CafePreviewAccessGate::HEALTH_PATH)
    assert_equal 200, response.status
    assert_equal 'ok', response.body
  end

  test 'weak or missing passwords or signing secrets fail closed during boot' do
    app = ->(_env) { [200, {}, ['ok']] }
    assert_raises(ArgumentError) do
      CafePreviewAccessGate.new(app, username: 'portfolio', password: 'short', secret: 'a' * 40)
    end
    assert_raises(ArgumentError) do
      CafePreviewAccessGate.new(app, username: 'portfolio', password: 'a' * 30, secret: 'short')
    end
  end
end
