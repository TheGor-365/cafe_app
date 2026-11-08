require 'test_helper'
require 'base64'
require_relative '../../lib/cafe_preview_access_gate'

class CafePreviewAccessGateTest < ActiveSupport::TestCase
  def setup
    downstream = ->(_env) { [200, { 'Content-Type' => 'text/plain' }, ['demo']] }
    @gate = CafePreviewAccessGate.new(
      downstream, username: 'portfolio', password: 'local-test-password-123456789'
    )
    @request = Rack::MockRequest.new(@gate)
  end

  test 'anonymous visitors cannot reach the demo app' do
    assert_equal 401, @request.get('/').status
  end

  test 'incorrect Basic credentials are rejected' do
    header = 'Basic ' + Base64.strict_encode64('portfolio:wrong-password')
    assert_equal 401, @request.get('/', 'HTTP_AUTHORIZATION' => header).status
  end

  test 'the correct Basic credentials can reach the demo app' do
    header = 'Basic ' + Base64.strict_encode64('portfolio:local-test-password-123456789')
    response = @request.get('/', 'HTTP_AUTHORIZATION' => header)
    assert_equal 200, response.status
    assert_equal 'demo', response.body
  end

  test 'the health probe is accessible without Basic credentials' do
    response = @request.get(CafePreviewAccessGate::HEALTH_PATH)
    assert_equal 200, response.status
    assert_equal 'ok', response.body
  end

  test 'weak or missing passwords fail closed during boot' do
    app = ->(_env) { [200, {}, ['ok']] }
    assert_raises(ArgumentError) { CafePreviewAccessGate.new(app, username: 'portfolio', password: 'short') }
    assert_raises(ArgumentError) { CafePreviewAccessGate.new(app, username: 'portfolio', password: '') }
  end
end
