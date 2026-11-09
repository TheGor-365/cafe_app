require 'test_helper'

class CafePublicAccessSmokeTest < ActionDispatch::IntegrationTest
  test 'visitors see storefront, ordinary Devise sign in and sign up without preview password' do
    get root_path
    assert_response :success
    assert_select 'a[href=?]', new_user_session_path, minimum: 1
    assert_select 'a[href=?]', new_user_registration_path, minimum: 1
    assert_not_includes response.body, 'Preview access password'

    get new_user_session_path
    assert_response :success
    assert_select 'main.cafe-auth h1', text: 'Sign in'

    get new_user_registration_path
    assert_response :success
    assert_select 'main.cafe-auth h1', text: 'Create an account'
    assert_select 'input[name="user[admin]"]', count: 0
  end

  test 'anonymous visitors receive the actual first-party SVG favicon' do
    get '/favicon.svg?v=20261109'
    assert_response :success
    assert_match %r{image/svg\+xml}, response.media_type
    assert_includes response.body, 'Gor'
    assert_not_includes response.body, 'Private portfolio preview'
  end

  test 'Railway healthcheck remains public and checks the database' do
    get '/__cafe_health'
    assert_response :success
    assert_equal 'ok', response.body
    assert_match %r{text/plain}, response.media_type
  end

  test 'regular authenticated users still cannot open admin management' do
    get products_path
    assert_redirected_to new_user_session_path

    account = User.create!(
      username: 'cafe_public_guest_qa',
      email: 'cafe-public-guest-qa@example.test',
      password: 'SafePass12345', password_confirmation: 'SafePass12345'
    )
    assert_not account.admin?
    post user_session_path, params: {
      user: { email: account.email, password: 'SafePass12345' }
    }
    assert_response :redirect

    get products_path
    assert_response :forbidden
    get categories_path
    assert_response :forbidden
    get admin_demo_orders_path
    assert_response :forbidden
  end

  test 'production Rack entrypoint has no additional password gate' do
    config = Rails.root.join('config.ru').read
    refute_includes config, 'CafePreviewAccessGate'
    assert_includes config, 'run Rails.application'
  end
end
