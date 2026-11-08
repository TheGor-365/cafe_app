require 'test_helper'
require_relative '../../lib/cafe_preview_access_gate'

class CafePreviewAccessGateTest < ActiveSupport::TestCase
  class FakeWarden
    def initialize(authenticated)
      @authenticated = authenticated
    end

    def authenticated?(scope)
      scope == :user && @authenticated
    end
  end

  def setup
    @calls = []
    calls = @calls
    downstream = lambda do |env|
      calls << [env['REQUEST_METHOD'], env['PATH_INFO']]
      authenticated = env['HTTP_TEST_AUTH_SUCCESS'] == 'yes'
      env['warden'] = FakeWarden.new(authenticated)
      if authenticated
        [302, { 'Location' => '/', 'Set-Cookie' => '_cafe_test=devise; Path=/; HttpOnly' }, []]
      else
        [200, { 'Content-Type' => 'text/html' }, ['Rails form']]
      end
    end
    @gate = CafePreviewAccessGate.new(downstream, secret: 'test-only-signing-secret-long-enough-123456789')
    @request = Rack::MockRequest.new(@gate)
  end

  test 'anonymous homepage shows exactly ordinary sign in and register options' do
    response = @request.get('/')
    assert_equal 200, response.status
    assert_includes response.body, 'Sign in'
    assert_includes response.body, 'Create account'
    assert_includes response.body, '/users/sign_up'
    assert_includes response.body, '/users/sign_in'
    refute_includes response.body, 'preview access password'
    assert_nil response['WWW-Authenticate']
    assert_empty @calls
  end

  test 'Devise account forms and their styles are reachable without any shared preview credentials' do
    %w[/users/sign_in /users/sign_up /users/password/new /assets/application.css /packs/js/application.js].each do |path|
      response = @request.get(path)
      assert_equal 200, response.status, path
      assert_equal 'Rails form', response.body, path
    end
    assert_equal 5, @calls.size
  end

  test 'an authenticating Devise post issues a signed HttpOnly session cookie and retains the Rails cookie' do
    response = @request.post('/users/sign_in', 'HTTP_TEST_AUTH_SUCCESS' => 'yes')
    assert_equal 302, response.status
    cookie_header = response['Set-Cookie']
    assert_includes cookie_header, '_cafe_test=devise'
    assert_includes cookie_header, '__Host-cafe_preview='
    assert_includes cookie_header, 'Secure'
    assert_includes cookie_header, 'HttpOnly'
    cookie = cookie_header[/__Host-cafe_preview=[^;]+/]

    page = @request.get('/menu', 'HTTP_COOKIE' => cookie)
    assert_equal 200, page.status
    assert_equal 'Rails form', page.body
    assert_includes @calls, ['GET', '/menu']
  end

  test 'registration also unlocks browsing only after a genuine Devise sign in' do
    failed = @request.post('/users')
    assert_equal 200, failed.status
    assert_nil failed['Set-Cookie']
    assert_empty @calls.select { |_, path| path == '/products' }

    success = @request.post('/users', 'HTTP_TEST_AUTH_SUCCESS' => 'yes')
    cookie = success['Set-Cookie'][/__Host-cafe_preview=[^;]+/]
    assert cookie
    assert_equal 200, @request.get('/products', 'HTTP_COOKIE' => cookie).status
  end

  test 'anonymous access to cart and admin is blocked' do
    assert_equal 200, @request.get('/cart').status
    assert_includes @request.get('/admin/demo_orders').body, 'Sign in'
    assert_equal 403, @request.post('/admin/demo_orders/1/status').status
    refute @calls.any? { |_, path| path == '/admin/demo_orders' }
  end

  test 'invalid cookie cannot bypass authentication' do
    r = @request.post('/users/sign_in', 'HTTP_TEST_AUTH_SUCCESS' => 'yes')
    cookie = r['Set-Cookie'][/__Host-cafe_preview=[^;]+/]
    invalid = @request.get('/menu', 'HTTP_COOKIE' => cookie + 'x')
    assert_includes invalid.body, 'Create account'
    refute @calls.any? { |_, path| path == '/menu' }
  end

  test 'Devise sign out clears preview browser cookie' do
    r = @request.post('/users/sign_in', 'HTTP_TEST_AUTH_SUCCESS' => 'yes')
    cookie = r['Set-Cookie'][/__Host-cafe_preview=[^;]+/]
    signed_out = @request.delete('/users/sign_out', 'HTTP_COOKIE' => cookie)
    assert_includes signed_out['Set-Cookie'], 'Max-Age=0'
    post_override = @request.post('/users/sign_out', 'HTTP_COOKIE' => cookie, :input => '_method=delete')
    assert_includes post_override['Set-Cookie'], 'Max-Age=0'
  end

  test 'health probe stays unauthenticated and queries database' do
    assert_equal 200, @request.get(CafePreviewAccessGate::HEALTH_PATH).status
    assert_equal 'ok', @request.get(CafePreviewAccessGate::HEALTH_PATH).body
  end

  test 'weak signing secret fails closed' do
    assert_raises(ArgumentError) do
      CafePreviewAccessGate.new(->(_env) { [200, {}, ['ok']] }, secret: 'short')
    end
  end
end
