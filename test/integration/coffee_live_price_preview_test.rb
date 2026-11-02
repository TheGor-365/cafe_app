require 'test_helper'

class CoffeeLivePricePreviewTest < ActionDispatch::IntegrationTest
  setup do
    category = Category.create!(heading: 'Coffee Preview QA', display: true)
    @product = Product.create!(category: category, name: 'Preview Cappuccino',
                               price: 4.25, available: true)
    ProductVariant.create!(product: @product, code: 'S', label: 'Small', price_cents: 425)
    ProductVariant.create!(product: @product, code: 'M', label: 'Medium', price_cents: 500)
    ProductModifierOption.create!(product: @product, group_code: 'milk',
                                 code: 'oat', label: 'Oat milk', price_cents: 60)
  end

  test 'menu renders safe cents metadata and initial server-calculated preview' do
    get menu_path(category_id: @product.category_id)
    assert_response :success
    assert_select "form[data-coffee-price-form][data-base-price-cents='425']", count: 1 do
      assert_select "select[name='order_item[product_variant_id]'] option[data-price-cents='500']", count: 1
      assert_select "select[name='order_item[modifier_option_ids][]'] option[data-price-cents='60']", count: 1
      assert_select "select[name='order_item[modifier_option_ids][]'] option[data-price-cents='0']", minimum: 1
      assert_select 'output[data-coffee-price-output][aria-live=polite]', count: 1
      assert_select '[data-coffee-total-price]', text: 'Total: $4.25'
      assert_select 'input[data-coffee-quantity]', count: 1
    end
    assert_select '.coffee-product-card__price', text: /From.*\$4.25/
  end

  test 'preview never replaces server-side price validation' do
    medium = @product.product_variants.find_by!(code: 'M')
    milk = @product.product_modifier_options.first
    post order_items_path, params: { order_item: {
      product_id: @product.id, quantity: 2,
      product_variant_id: medium.id, modifier_option_ids: [milk.id.to_s],
      unit_price: '0.01'
    }}
    assert_redirected_to cart_path
    line = OrderItem.order(:id).last
    assert_equal BigDecimal('5.60'), line[:unit_price]
    assert_equal BigDecimal('11.20'), line[:total]
  end

  test 'no JavaScript is needed to submit drink form' do
    get menu_path(category_id: @product.category_id)
    assert_select "form[action='#{order_items_path}'][method='post'][data-coffee-price-form]", count: 1
    assert_select 'script', text: /computePriceCents/, count: 0
  end
end
