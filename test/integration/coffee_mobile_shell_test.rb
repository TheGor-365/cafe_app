require 'test_helper'

class CoffeeMobileShellTest < ActionDispatch::IntegrationTest
  test 'guest navigation remains an accessible unhidden list of working destinations' do
    get menu_path
    assert_response :success
    assert_select 'meta[name=viewport][content=?]', 'width=device-width, initial-scale=1'
    assert_select 'nav.cafe-sidebar[aria-label="Main navigation"][tabindex="0"]', count: 1 do
      assert_select "a[href='#{root_path}']", count: 1
      assert_select "a[href='#{menu_path}'][aria-current=page]", count: 1
      assert_select "a[href='#{cart_path}']", count: 1
      assert_select "a[href='#{catering_path}']", count: 1
      assert_select "a[href='#{info_path}']", count: 1
      assert_select "a[href='#{products_path}']", count: 0
      assert_select "a[href='#{categories_path}']", count: 0
    end
  end

  test 'cart navigation announces active page and retains explicit quantity update' do
    get cart_path
    assert_response :success
    assert_select 'nav.cafe-sidebar' do
      assert_select "a[href='#{cart_path}'][aria-current=page]", count: 1
      assert_select "a[href='#{menu_path}'][aria-current=page]", count: 0
    end
    assert_select 'footer.cafe-site-footer', count: 1
  end

  test 'SassC compiles mobile QA stylesheet and preserves the existing column shell' do
    source = Rails.root.join('app/assets/stylesheets/zzz_cafe_mobile_quality.scss')
    css = SassC::Engine.new(File.read(source), syntax: :scss).render

    assert_includes css, '@media (max-width: 760px)'
    assert_includes css, '@media (max-width: 360px)'
    assert_includes css, '@media (min-width: 761px) and (max-width: 980px)'
    assert_includes css, 'scroll-snap-type: x proximity'
    assert_includes css, 'overflow-x: auto'
    assert_includes css, 'min-height: 44px'
    assert_includes css, '.cafe-cart__update-form'
    assert_includes css, '.coffee-config.is-modal'
    assert_includes css, '@media (prefers-reduced-motion: reduce)'
    assert_includes css, 'grid-area'
    refute_match(/display:\s*none\s*!important/, css)
  end

  test 'menu search controls and native product configuration are still present' do
    category = Category.create!(heading: 'Mobile QA category', display: true)
    Product.create!(category: category, name: 'Mobile QA Espresso',
                    description: 'Sample demo coffee', price: 3.10, available: true)
    get menu_path(category_id: category.id)
    assert_response :success
    assert_select "form[role=search]" do
      assert_select "input[type=search]", count: 1
      assert_select "select[name=filter]", count: 1
    end
    assert_select 'details[data-coffee-config]', count: 1 do
      assert_select 'form[action=?]', order_items_path, count: 1
    end
  end
end
