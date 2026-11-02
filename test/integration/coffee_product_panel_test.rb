require 'test_helper'

class CoffeeProductPanelTest < ActionDispatch::IntegrationTest
  setup do
    category = Category.create!(heading: 'Panel QA Coffee', display: true)
    @drink = Product.create!(category: category, name: 'Panel QA Latte',
                             description: 'Demo latte with choices', price: 4.25, available: true)
    @size = ProductVariant.create!(product: @drink, code: 'M',
                                   label: 'Medium', price_cents: 500)
    @milk = ProductModifierOption.create!(product: @drink, group_code: 'milk',
                                          code: 'oat', label: 'Oat milk', price_cents: 60)
    @pastry = Product.create!(category: category, name: 'Panel QA Pastry',
                              description: 'Demo bakery item', price: 3.50, available: true)
  end

  test 'menu cards expose one compact trigger with options inside details fallback' do
    get menu_path(category_id: @drink.category_id)
    assert_response :success

    assert_select 'article.coffee-product-card', count: 2
    assert_select 'details[data-coffee-config]', count: 2
    assert_select 'article.coffee-product-card > .coffee-product-card__content > form', count: 0
    assert_select 'details[data-coffee-config] > summary.coffee-config__trigger', count: 2
    assert_select 'summary.coffee-config__trigger[aria-label=?]', "Customize #{@drink.name}", count: 1

    assert_select "div[data-coffee-config-panel][aria-labelledby='coffee-config-title-#{@drink.id}']", count: 1 do
      assert_select "form[action='#{order_items_path}'][method='post'][data-coffee-price-form]", count: 1 do
        assert_select "input[name='order_item[product_id]'][value='#{@drink.id}']", count: 1
        assert_select "select[name='order_item[product_variant_id]']", count: 1
        assert_select "select[name='order_item[modifier_option_ids][]']", minimum: 1
        assert_select 'output[data-coffee-price-output]', count: 1
        assert_select "input[type='submit']", count: 1
      end
      assert_select 'button[type=button][data-coffee-config-close]', count: 1
    end
    assert_select 'summary.coffee-config__trigger[aria-label=?]', "Add #{@pastry.name}", count: 1
  end

  test 'plain HTTP form submission still works without JavaScript enhancement' do
    post order_items_path, params: {
      order_item: { product_id: @drink.id, product_variant_id: @size.id,
                    modifier_option_ids: [@milk.id.to_s], quantity: 2 }
    }
    assert_redirected_to cart_path
    item = OrderItem.order(:id).last
    assert_equal BigDecimal('5.60'), item[:unit_price]
    assert_equal BigDecimal('11.20'), item[:total]
  end

  test 'unavailable sizes remain non-purchasable inside the panel' do
    @size.update!(available: false)
    get menu_path(category_id: @drink.category_id)
    assert_response :success
    assert_select "div[data-coffee-config-panel][aria-labelledby='coffee-config-title-#{@drink.id}']" do
      assert_select 'input[type=submit][disabled]', count: 1
      assert_select '.coffee-product-card__unavailable', count: 1
    end
  end

  test 'panel styles compile under legacy SassC without changing outer layout' do
    css = Rails.root.join('app/assets/stylesheets/cafe_product_panel.scss')
    rendered = SassC::Engine.new(File.read(css), syntax: :scss).render
    assert_includes rendered, '.coffee-config.is-modal'
    assert_includes rendered, 'position: fixed'
    assert_includes rendered, 'overflow-y: auto'
    assert_includes rendered, 'focus-visible'
  end
end
