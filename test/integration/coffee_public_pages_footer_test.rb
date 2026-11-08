require 'test_helper'

class CoffeePublicPagesAndFooterTest < ActionDispatch::IntegrationTest
  setup do
    @category = Category.create!(heading: 'Public Pages QA Coffee', display: true)
    @drink = Product.create!(category: @category, name: 'QA Vanilla Latte',
                             description: 'A sample café drink', price: 4.50, available: true)
    @variant = ProductVariant.create!(product: @drink, code: 'M',
                                      label: 'Medium · 350 ml', price_cents: 525)
    @syrup = ProductModifierOption.create!(product: @drink, group_code: 'syrup',
                                           code: 'vanilla', label: 'Vanilla syrup',
                                           price_cents: 55)
  end

  test 'about page is contentful and links FAQ location and contact from footer' do
    get info_path
    assert_response :success
    assert_select 'title', text: /About & FAQ/
    assert_select 'main.cafe-content-page h1', text: /A coffee experience/
    assert_select 'section#faq details', count: 5
    assert_select 'section#location .cafe-content-page__map-placeholder', count: 1
    assert_select 'section#contact a[href=?]', 'https://github.com/TheGor-365/cafe_app', count: 1
    assert_select 'footer.cafe-site-footer nav[aria-label="Footer navigation"]' do
      assert_select "a[href='#{info_path(anchor: 'faq')}']", count: 1
      assert_select "a[href='#{info_path(anchor: 'location')}']", count: 1
      assert_select "a[href='#{info_path(anchor: 'contact')}']", count: 1
    end
    assert_includes response.body, 'No physical café address'
    refute_includes response.body, 'Opening hours:'
  end

  test 'catering is a transparent concept with functioning menu and FAQ links' do
    get catering_path
    assert_response :success
    assert_select 'title', text: /Catering Concept/
    assert_select 'main.cafe-content-page h1', text: /good company/
    assert_select 'main.cafe-content-page article.cafe-content-page__card', count: 3
    assert_select "main a[href='#{menu_path}']", minimum: 1
    assert_select "main a[href='#{info_path(anchor: 'faq')}']", count: 1
    assert_select "main a[href='#{info_path(anchor: 'contact')}']", count: 1
    assert_select 'footer.cafe-site-footer', count: 1
    assert_includes response.body, 'No booking form'
  end

  test 'available product detail reuses the real menu configurator and server cart' do
    get product_path(@drink)
    assert_response :success
    assert_select 'title', text: /QA Vanilla Latte/
    assert_select 'main.coffee-product-detail h1', text: @drink.name
    assert_select "a[href='#{menu_path(category_id: @category.id)}']", minimum: 1
    assert_select 'main.coffee-product-detail .coffee-product-card', count: 1 do
      assert_select 'details[data-coffee-config]', count: 1
      assert_select "form[action='#{order_items_path}'][method='post']", count: 1 do
        assert_select 'input[name="order_item[product_id]"][value=?]', @drink.id.to_s
        assert_select 'select[name="order_item[product_variant_id]"]', count: 1
        assert_select 'select[name="order_item[modifier_option_ids][]"]', count: 1
        assert_select 'input[data-coffee-quantity-input][min=1][max=20]', count: 1
      end
    end
    assert_select 'footer.cafe-site-footer', count: 1

    post order_items_path, params: { order_item: {
      product_id: @drink.id, product_variant_id: @variant.id,
      modifier_option_ids: [@syrup.id.to_s], quantity: 2
    } }
    assert_redirected_to cart_path
    line = OrderItem.last
    assert_equal BigDecimal('5.80'), line[:unit_price]
    assert_equal BigDecimal('11.60'), line[:total]
  end

  test 'unavailable product keeps details visible but cannot be added' do
    @drink.update!(available: false)
    get product_path(@drink)
    assert_response :success
    assert_select 'main.coffee-product-detail h1', text: @drink.name
    assert_select '.coffee-product-detail__unavailable[role=status]', count: 1
    assert_select 'main.coffee-product-detail form[action=?]', order_items_path, count: 0
    assert_select 'a[href=?]', menu_path, minimum: 1
  end

  test 'global footer is present on home menu and cart without imaginary contact data' do
    [root_path, menu_path, cart_path].each do |route|
      get route
      assert_response :success
      assert_select 'footer.cafe-site-footer', count: 1 do
        assert_select 'nav[aria-label="Footer navigation"]', count: 1
        assert_select "a[href='#{catering_path}']", count: 1
        assert_select "a[href='#{info_path}']", count: 1
      end
    end
  end

  test 'new public-page styles render with SassC and include mobile rules' do
    path = Rails.root.join('app/assets/stylesheets/cafe_public_pages.scss')
    compiled = SassC::Engine.new(File.read(path), syntax: :scss).render
    assert_includes compiled, '.coffee-product-detail'
    assert_includes compiled, '.cafe-content-page__map-placeholder'
    assert_includes compiled, '.cafe-site-footer'
    assert_includes compiled, '@media (max-width: 400px)'
    refute_includes compiled, 'clamp('
  end
end
