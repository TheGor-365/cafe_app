require 'test_helper'

class CoffeeUnifiedShellTest < ActionDispatch::IntegrationTest
  test 'guest has one account navigation and no blank avatar segment across routes' do
    [root_path, menu_path, cart_path, info_path, catering_path,
     new_user_session_path, new_user_registration_path].each do |path|
      get path
      assert_response :success, "GET #{path}"
      assert_select 'div.cafe-page', count: 1
      assert_select 'div.page-container > div.col-1', count: 0
      assert_select 'div.page-container > nav.cafe-account-widget[aria-label=Account]', count: 1 do
        assert_select "a[href='#{new_user_session_path}']", text: 'Sign in', count: 1
        assert_select "a[href='#{new_user_registration_path}']", text: 'Sign up', count: 1
      end
    end
  end

  test 'authenticated identity, logout and admin navigation remain functional' do
    user = User.create!(username: 'coffee_shell_qa',
                        email: 'shell-qa@example.test',
                        password: 'SafePass123', password_confirmation: 'SafePass123',
                        admin: true)
    post user_session_path, params: { user: { email: user.email, password: 'SafePass123' } }
    assert_response :redirect

    get menu_path
    assert_response :success
    assert_select 'nav.cafe-account-widget' do
      assert_select "a[href='#{edit_user_registration_path}']", text: /coffee_shell_qa/, count: 1
      assert_select "a[href='#{destroy_user_session_path}'][data-method=delete]", text: 'Sign out', count: 1
      assert_select "a[href='#{new_user_session_path}']", count: 0
    end
    assert_select 'nav.cafe-sidebar' do
      assert_select "a[href='#{products_path}']", count: 1
      assert_select "a[href='#{categories_path}']", count: 1
    end

    delete destroy_user_session_path
    get menu_path
    assert_response :success
    assert_select "nav.cafe-account-widget a[href='#{new_user_session_path}']", count: 1
    assert_not_includes response.body, user.username
  end

  test 'fixed background and responsive account styles compile under SassC' do
    source = Rails.root.join('app/assets/stylesheets/zzzzz_cafe_unified_shell.scss').read
    css = SassC::Engine.new(source, syntax: :scss).render

    assert_includes css, '.cafe-page::before'
    assert_includes css, 'position: fixed'
    assert_includes css, 'pointer-events: none'
    assert_includes css, '.cafe-page.menu-page::before'
    assert_includes css, '.cafe-page.catering-page::before'
    assert_includes css, '.cafe-page.info-page::before'
    assert_includes css, '.cafe-page.review-page::before'
    assert_includes css, '.cafe-page.cart-page::before'
    assert_includes css, 'grid-template-areas: "nav main account"'
    assert_includes css, 'grid-template-areas: "nav" "account" "main"'
    assert_includes css, '@media (max-width: 760px)'
    assert_includes css, '@media (max-width: 360px)'
    assert_includes css, 'min-height: 44px'
    assert_includes css, ':focus-visible'
    assert_includes css, 'nav.cafe-sidebar {'
    assert_includes css, 'nav.cafe-account-widget {'
    assert_includes css, '.cafe-brandbar.title-card {'
    assert_includes css, 'position: sticky'
    assert_includes css, 'height: 100vh'
    assert_includes css, 'max-height: 100vh'
    assert_includes css, 'overflow-y: auto'
    assert_includes css, 'top: 60px'
    assert_includes css, 'top: 120px'
  end
end
