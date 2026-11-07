require 'test_helper'

class CoffeeMobileBottomDockTest < ActionDispatch::IntegrationTest
  test 'guest has five accessible icon destinations' do
    [root_path, menu_path, cart_path, catering_path, info_path].each do |path|
      get path
      assert_response :success
      assert_select 'nav.cafe-mobile-dock[aria-label="Mobile navigation"]', count: 1 do
        assert_select 'a.cafe-dock__link', count: 5
        assert_select 'svg.cafe-dock__icon[aria-hidden=true]', count: 5
        [root_path, menu_path, cart_path, catering_path, info_path].each do |href|
          assert_select "a.cafe-dock__link[href='#{href}']", count: 1
        end
        assert_select 'details.cafe-dock__more', count: 0
      end
      assert_select 'nav.cafe-sidebar', count: 1
    end
  end

  test 'current route and zero cart quantity appear in native links' do
    get info_path
    assert_response :success
    assert_select "nav.cafe-mobile-dock a[href='#{info_path}'][aria-current=page]", count: 1
    get cart_path
    assert_response :success
    assert_select "nav.cafe-mobile-dock a[href='#{cart_path}'][aria-current=page]", count: 1
    assert_select 'nav.cafe-mobile-dock .cafe-dock__badge', text: '0', count: 1
  end

  test 'signed in admin retains account and management links in a native More menu' do
    user = User.create!(username: 'cafe_dock_admin', email: 'dock-admin@example.test',
                        password: 'SafePass123', password_confirmation: 'SafePass123',
                        admin: true)
    post user_session_path, params: { user: { email: user.email, password: 'SafePass123' } }
    assert_response :redirect
    get menu_path
    assert_response :success
    assert_select 'nav.cafe-mobile-dock details.cafe-dock__more', count: 1 do
      assert_select 'summary.cafe-dock__summary', count: 1
      [account_path, edit_user_registration_path, products_path, categories_path].each do |href|
        assert_select "a[href='#{href}']", count: 1
      end
    end
  end

  test 'SassC parses fixed bottom dock and viewport safe area' do
    css = SassC::Engine.new(File.read(Rails.root.join('app/assets/stylesheets/zzzzzzz_cafe_mobile_dock.scss')),
                            syntax: :scss).render
    assert_includes css, '@media (max-width: 760px)'
    assert_includes css, '@media (min-width: 761px)'
    assert_includes css, 'position: fixed'
    assert_includes css, 'bottom: 0'
    assert_includes css, 'safe-area-inset-bottom'
    assert_includes css, 'grid-template-areas: "account" "main"'
    assert_includes css, 'nav.cafe-sidebar'
    assert_includes css, 'min-height: 52px'
  end
end
