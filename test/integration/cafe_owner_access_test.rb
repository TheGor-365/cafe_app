require 'test_helper'

class CafeOwnerAccessTest < ActionDispatch::IntegrationTest
  TOKEN = 'owner-claim-test-token-fake-0123456789012345678901234567'.freeze

  def with_owner_configuration
    keys = %w[CAFE_OWNER_USERNAME CAFE_OWNER_CLAIM_TOKEN]
    original = keys.map { |k| [k, ENV[k]] }.to_h
    ENV['CAFE_OWNER_USERNAME'] = 'Eric'
    ENV['CAFE_OWNER_CLAIM_TOKEN'] = TOKEN
    yield
  ensure
    original.each { |k, value| value.nil? ? ENV.delete(k) : ENV[k] = value }
  end

  test 'only the matching signed-in owner with the correct secret can claim admin once' do
    with_owner_configuration do
      user = User.create!(username: 'Eric', email: 'eric-cafe-owner-qa@example.test',
                          password: 'StrongPassword123', password_confirmation: 'StrongPassword123')
      post user_session_path, params: { user: { email: user.email, password: 'StrongPassword123' } }
      assert_response :redirect
      get account_path
      assert_response :success
      assert_select "a[href='#{new_owner_access_path}']", text: 'Activate owner access'
      get new_owner_access_path
      assert_response :success
      assert_select 'form[action=?]', owner_access_path
      assert_select 'input[type=password][name=owner_access_code]'

      post owner_access_path, params: { owner_access_code: 'wrong-owner-claim-code' }
      assert_redirected_to new_owner_access_path
      assert_not user.reload.admin?

      post owner_access_path, params: { owner_access_code: TOKEN }
      assert_redirected_to products_path
      assert user.reload.admin?

      get products_path
      assert_response :success
      get categories_path
      assert_response :success
      get admin_demo_orders_path
      assert_response :success
    end
  end

  test 'a second registered user cannot use the owner code to become admin' do
    with_owner_configuration do
      other = User.create!(username: 'Other_Cafe_User', email: 'other-cafe-qa@example.test',
                           password: 'StrongPassword123', password_confirmation: 'StrongPassword123')
      post user_session_path, params: { user: { email: other.email, password: 'StrongPassword123' } }
      get account_path
      assert_response :success
      assert_select "a[href='#{new_owner_access_path}]", count: 0
      post owner_access_path, params: { owner_access_code: TOKEN }
      assert_redirected_to new_owner_access_path
      assert_not other.reload.admin?
    end
  end

  test 'owner-claim endpoint is unavailable without Railway configuration' do
    get new_owner_access_path
    assert_redirected_to new_user_session_path
  end

  test 'ordinary signup cannot set admin flag even with forged params' do
    assert_difference 'User.count', 1 do
      post user_registration_path, params: { user: {
        username: 'Cafe_Unprivileged_QA', email: 'cafe-unprivileged@example.test',
        password: 'StrongPassword123', password_confirmation: 'StrongPassword123',
        admin: true
      } }
    end
    assert_not User.find_by!(email: 'cafe-unprivileged@example.test').admin?
  end
end
