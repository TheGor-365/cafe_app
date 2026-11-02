require 'test_helper'

class CoffeeAuthAndAccountTest < ActionDispatch::IntegrationTest
  test 'signed-out visitors see branded functional registration and sign-in forms' do
    get new_user_session_path
    assert_response :success
    assert_select 'main.cafe-auth h1', text: 'Sign in'
    assert_select "form[action='#{user_session_path}'][method=post]" do
      assert_select 'input[name="user[email]"]', count: 1
      assert_select 'input[name="user[password]"]', count: 1
    end
    assert_select 'input.cafe-auth__submit', count: 1

    get new_user_registration_path
    assert_response :success
    assert_select 'main.cafe-auth h1', text: 'Create an account'
    assert_select "form[action='#{user_registration_path}'][method=post]" do
      assert_select 'input[name="user[email]"]', count: 1
      assert_select 'input[name="user[username]"]', count: 1
      assert_select 'input[name="user[avatar]"]', count: 0
      assert_select 'input[name="user[avatar_cache]"]', count: 0
    end
    assert_includes response.body, 'temporarily unavailable'
  end

  test 'registration does not require an avatar and lands in an authenticated session' do
    assert_difference 'User.count', 1 do
      post user_registration_path, params: { user: {
        username: 'new_coffee_qa_user', email: 'new-coffee-qa@example.test',
        password: 'SixChars123', password_confirmation: 'SixChars123'
      }}
    end
    assert_response :redirect
    follow_redirect!
    assert_response :success

    get account_path
    assert_response :success
    assert_select 'main.cafe-account h1', text: /new_coffee_qa_user/
  end

  test 'account requires authentication and never exposes personal information to guests' do
    get account_path
    assert_redirected_to new_user_session_path
    follow_redirect!
    assert_response :success
    assert_select 'main.cafe-auth h1', text: 'Sign in'
  end

  test 'account shows only own profile and session basket with clear limits' do
    user = User.create!(username: 'coffee_profile_qa', email: 'profile-qa@example.test',
                        password: 'ValidPass123', password_confirmation: 'ValidPass123')
    post user_session_path, params: { user: { email: user.email, password: 'ValidPass123' } }
    assert_response :redirect

    get account_path
    assert_response :success
    assert_select 'title', text: /My Account/
    assert_select 'main.cafe-account h1', text: /coffee_profile_qa/
    assert_select 'main.cafe-account', text: /profile-qa@example.test/
    assert_select "a[href='#{edit_user_registration_path}']", minimum: 1
    assert_select "a[href='#{cart_path}']", minimum: 1
    assert_select 'nav.cafe-sidebar' do
      assert_select "a[href='#{account_path}'][aria-current=page]", count: 1
    end
    assert_includes response.body, 'not linked to your account'
    assert_select 'main.cafe-account', text: /There are no past orders/, count: 0
  end

  test 'profile settings remain fully functional without broken avatar input' do
    user = User.create!(username: 'coffee_edit_qa', email: 'edit-qa@example.test',
                        password: 'ValidPass123', password_confirmation: 'ValidPass123')
    post user_session_path, params: { user: { email: user.email, password: 'ValidPass123' } }
    assert_response :redirect

    get edit_user_registration_path
    assert_response :success
    assert_select 'main.cafe-auth h1', text: 'Edit your profile'
    assert_select "form[action='#{user_registration_path}']" do
      assert_select 'input[name="user[current_password]"]', count: 1
      assert_select 'input[name="user[avatar]"]', count: 0
    end
    assert_select "a[href='#{account_path}']", count: 1
    assert_select 'a.cafe-auth__delete', count: 1
  end

  test 'recovery forms are branded without implying email delivery is operational' do
    get new_user_password_path
    assert_response :success
    assert_select 'main.cafe-auth h1', text: 'Forgot your password?'
    assert_includes response.body, 'Email delivery is not yet verified'
  end

  test 'legacy SassC compiles account styles and supports 320px mobile' do
    file = Rails.root.join('app/assets/stylesheets/zzz_cafe_auth_account.scss')
    css = SassC::Engine.new(file.read, syntax: :scss).render
    assert_includes css, '.cafe-auth__submit'
    assert_includes css, '.cafe-account__grid'
    assert_includes css, '@media (max-width: 360px)'
    assert_includes css, 'min-height: 46px'
  end
end
