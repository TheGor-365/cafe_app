require 'test_helper'

class CafeCompactMobileAccountTest < ActionDispatch::IntegrationTest
  test 'public mobile homepage has icon links for standard Devise entry' do
    get root_path
    assert_response :success
    assert_select '.cafe-brandbar .cafe-brandbar__brand', text: /Gor.s Coffee/, count: 1
    assert_select '.cafe-brandbar .cafe-mobile-account-actions', count: 1
    assert_select 'main.cafe-home .cafe-mobile-account-actions', count: 0
    assert_select '.cafe-brandbar .cafe-mobile-account-actions a[aria-label="Sign in"][href=?]', new_user_session_path, count: 1
    assert_select '.cafe-brandbar .cafe-mobile-account-actions a[aria-label="Sign up"][href=?]', new_user_registration_path, count: 1
    assert_select '.cafe-brandbar .cafe-mobile-account-actions svg[aria-hidden="true"]', count: 2
    assert_select 'nav.cafe-mobile-dock', count: 1
  end

  test 'mobile app shortcuts link account and retain native Devise DELETE sign out' do
    user = User.create!(
      username: 'mobile_account_qa', email: 'mobile-account-qa@example.test',
      password: 'ValidPass123', password_confirmation: 'ValidPass123'
    )
    post user_session_path, params: { user: { email: user.email, password: 'ValidPass123' } }
    assert_response :redirect

    get root_path
    assert_response :success
    assert_select '.cafe-brandbar .cafe-mobile-account-actions a[aria-label="My account"][href=?]', account_path, count: 1
    assert_select '.cafe-brandbar .cafe-mobile-account-actions form[action=?][method=post]', destroy_user_session_path, count: 1 do
      assert_select 'button[aria-label="Sign out"][type=submit]', count: 1
      assert_select 'input[name=_method][value=delete]', count: 1
    end
    assert_select '.cafe-brandbar .cafe-mobile-account-actions a[aria-label="Sign in"]', count: 0

    # On other routes the compact account actions live in the brandbar,
    # not a tall separate account strip.
    get menu_path
    assert_response :success
    assert_select '.cafe-brandbar .cafe-mobile-account-actions a[aria-label="My account"]', count: 1
    assert_select '.cafe-brandbar .cafe-mobile-account-actions button[aria-label="Sign out"]', count: 1
  end

  test 'admin destinations remain in the existing mobile More dock' do
    admin = User.create!(
      username: 'mobile_admin_qa', email: 'mobile-admin-qa@example.test',
      password: 'ValidPass123', password_confirmation: 'ValidPass123',
      admin: true
    )
    post user_session_path, params: { user: { email: admin.email, password: 'ValidPass123' } }
    get root_path
    assert_response :success
    assert_select 'nav.cafe-mobile-dock a[href=?]', products_path, count: 1
    assert_select 'nav.cafe-mobile-dock a[href=?]', categories_path, count: 1
    assert_select 'nav.cafe-mobile-dock a[href=?]', admin_demo_orders_path, count: 1
  end

  test 'final mobile stylesheet removes extra account strip but keeps universal brandbar and icons' do
    path = Rails.root.join('app/assets/stylesheets/zzzzzzzzz_cafe_mobile_account_compact.scss')
    css = SassC::Engine.new(path.read, syntax: :scss).render
    assert_includes css, 'max-width: 760px'
    assert_includes css, 'nav.cafe-account-widget'
    assert_includes css, 'display: none !important'
    assert_includes css, 'grid-template-areas: "main"'
    assert_includes css, '.cafe-brandbar.title-card'
    refute_includes css, '.home-page .page-container.row > .col-8#cafe-main-content > .cafe-brandbar.title-card'
    refute_includes css, '.cafe-home__hero-content > .cafe-mobile-account-actions'
    assert_includes css, 'min-height: 44px'
    assert_includes css, ':focus-visible'
  end
end
