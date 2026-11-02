require 'test_helper'

class SessionLayoutIsolationTest < ActionDispatch::IntegrationTest
  setup do
    @previous_caching = ActionController::Base.perform_caching
    @previous_store = Rails.cache
    ActionController::Base.perform_caching = true
    Rails.cache = ActiveSupport::Cache::MemoryStore.new

    @password = SecureRandom.hex(24)
    @member = User.create!(
      username: 'isolation_user_2026',
      email: 'isolation@example.test',
      password: @password,
      admin: false
    )
  end

  teardown do
    ActionController::Base.perform_caching = @previous_caching
    Rails.cache = @previous_store
  end

  test 'signed-in session identity is never cached into guest HTML' do
    member_browser = open_session
    guest_browser = open_session

    member_browser.post user_session_path,
      params: { user: { email: @member.email, password: @password } }
    assert_equal 302, member_browser.response.status

    member_browser.get menu_path
    assert_equal 200, member_browser.response.status
    assert_includes member_browser.response.body, @member.username

    guest_browser.get menu_path
    assert_equal 200, guest_browser.response.status
    assert_not_includes guest_browser.response.body, @member.username
    assert_includes guest_browser.response.body, 'Sign in'

    member_browser.delete destroy_user_session_path
    member_browser.get menu_path
    assert_equal 200, member_browser.response.status
    assert_not_includes member_browser.response.body, @member.username
  end
end
