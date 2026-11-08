require 'test_helper'

class CafeUserRegistrationSecurityTest < ActionDispatch::IntegrationTest
  test 'registration requires a valid username and cannot elevate admin' do
    assert_no_difference 'User.count' do
      post user_registration_path, params: { user: {
        username: '', email: 'blank-cafe-user@example.test',
        password: 'DemoUser123456', password_confirmation: 'DemoUser123456'
      }}
    end

    assert_difference 'User.count', 1 do
      post user_registration_path, params: { user: {
        username: 'new_cafe_guest_qa', email: 'guest-user-qa@example.test',
        password: 'DemoUser123456', password_confirmation: 'DemoUser123456',
        admin: true
      }}
    end

    user = User.find_by!(email: 'guest-user-qa@example.test')
    assert_equal false, user.admin?
    assert_equal 'new_cafe_guest_qa', user.username
  end

  test 'username is unique regardless of case and errors are handled without database exception' do
    User.create!(username: 'Existing_Cafe_QA', email: 'existing-cafe@example.test',
                 password: 'DemoUser123456', password_confirmation: 'DemoUser123456')

    assert_no_difference 'User.count' do
      post user_registration_path, params: { user: {
        username: 'existing_cafe_qa', email: 'second-cafe@example.test',
        password: 'DemoUser123456', password_confirmation: 'DemoUser123456'
      }}
    end

    assert_includes response.body, 'Username has already been taken'
  end

  test 'newly registered account can sign out and sign back in with its own password' do
    post user_registration_path, params: { user: {
      username: 'cafe_relogin_qa', email: 'relogin-cafe@example.test',
      password: 'DemoUser123456', password_confirmation: 'DemoUser123456'
    }}
    assert_response :redirect
    get account_path
    assert_response :success

    delete destroy_user_session_path
    assert_response :redirect
    get account_path
    assert_redirected_to new_user_session_path

    post user_session_path, params: { user: {
      email: 'relogin-cafe@example.test', password: 'DemoUser123456'
    }}
    assert_response :redirect
    get account_path
    assert_response :success
    assert_select 'main.cafe-account h1', text: /cafe_relogin_qa/
  end

  test 'registration form exposes required username with clear constraints' do
    get new_user_registration_path
    assert_response :success
    assert_select 'input[name="user[username]"][required][minlength="3"][maxlength="40"]', count: 1
    assert_includes response.body, '3–40 letters, numbers or underscores'
    assert_select 'input[name="user[admin]"]', count: 0
  end
end
