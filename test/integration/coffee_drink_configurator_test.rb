require 'test_helper'

class CoffeeDrinkConfiguratorTest < ActionDispatch::IntegrationTest
  setup do
    @category = Category.create!(heading: 'Drink QA', display: true)
    @drink = Product.create!(category: @category, name: 'QA Cappuccino',
                             description: 'Demo coffee', price: 4.25, available: true)
    @small = ProductVariant.create!(product: @drink, code: 'S', label: 'Small · 240 ml', price_cents: 425)
    @medium = ProductVariant.create!(product: @drink, code: 'M', label: 'Medium · 350 ml', price_cents: 500)
    @milk = ProductModifierOption.create!(product: @drink, group_code: 'milk',
             code: 'oat', label: 'Oat milk', price_cents: 60)
    @syrup = ProductModifierOption.create!(product: @drink, group_code: 'syrup',
             code: 'vanilla', label: 'Vanilla syrup', price_cents: 55)
    @extra_shot = ProductModifierOption.create!(product: @drink, group_code: 'shot',
             code: 'espresso', label: 'Extra shot', price_cents: 90)
  end

  test 'menu shows real sizes and one select per extra group' do
    get menu_path
    assert_response :success
    assert_select "select[name='order_item[product_variant_id]']", minimum: 1
    assert_select "select[name='order_item[modifier_option_ids][]']", minimum: 3
    assert_includes response.body, 'Medium'
    assert_includes response.body, 'Oat milk'
  end

  test 'server computes price and stores selected extras as snapshots' do
    assert_difference('OrderItem.count', 1) do
      assert_difference('OrderItemModifier.count', 2) do
        post order_items_path, params: { order_item: {
          product_id: @drink.id, quantity: 2, product_variant_id: @medium.id,
          modifier_option_ids: ['', @milk.id.to_s, @syrup.id.to_s, ''],
          unit_price: 0.01, total: 0.01
        } }
      end
    end
    assert_redirected_to cart_path

    line = OrderItem.order(:id).last
    assert_equal @medium.id, line.product_variant_id
    assert_equal 'Medium · 350 ml', line.variant_label_snapshot
    assert_equal BigDecimal('6.15'), line[:unit_price]
    assert_equal BigDecimal('12.30'), line[:total]

    follow_redirect!
    assert_includes response.body, 'Oat milk'
    assert_includes response.body, 'Vanilla syrup'
    assert_includes response.body, '12.30'

    @milk.update!(label: 'Renamed oat', price_cents: 999)
    @medium.update!(label: 'Medium updated', price_cents: 10000)
    patch order_item_path(line), params: { order_item: {
      quantity: 3, product_variant_id: @small.id, modifier_option_ids: [@extra_shot.id]
    } }
    assert_redirected_to cart_path
    assert_equal BigDecimal('18.45'), line.reload[:total]
    assert_equal 'Medium · 350 ml', line.variant_label_snapshot
    assert_equal ['Oat milk', 'Vanilla syrup'], line.order_item_modifiers.pluck(:label_snapshot).sort
  end

  test 'drink must have a matching available size' do
    invalid = [
      { product_id: @drink.id, quantity: 1 },
      { product_id: @drink.id, quantity: 1, product_variant_id: 0 },
      { product_id: @drink.id, quantity: 1, product_variant_id: @small.id }
    ]
    @small.update!(available: false)
    invalid.each do |attrs|
      assert_no_difference('OrderItem.count') do
        post order_items_path, params: { order_item: attrs }
      end
      assert_redirected_to menu_path
    end
  end

  test 'rejects foreign option, duplicate group and forged option ids' do
    other = Product.create!(category: @category, name: 'QA Stranger Tea', price: 2.0)
    foreign = ProductModifierOption.create!(product: other, group_code: 'milk',
                   code: 'soy', label: 'Soy milk', price_cents: 60)
    bad = [
      [foreign.id.to_s], [@milk.id.to_s, @milk.id.to_s],
      [@milk.id.to_s, foreign.id.to_s], ['1abc'], ['-1'],
      [@milk.id.to_s, @syrup.id.to_s, @extra_shot.id.to_s, @milk.id.to_s]
    ]
    bad.each do |ids|
      assert_no_difference('OrderItem.count') do
        post order_items_path, params: { order_item: {
          product_id: @drink.id, quantity: 1, product_variant_id: @medium.id,
          modifier_option_ids: ids
        } }
      end
      assert_redirected_to menu_path
    end
  end

  test 'does not bypass a configured drink when all sizes are unavailable' do
    @small.update!(available: false)
    @medium.update!(available: false)

    assert_no_difference('OrderItem.count') do
      post order_items_path, params: { order_item: {
        product_id: @drink.id, quantity: 1
      } }
    end
    assert_redirected_to menu_path
  end

  test 'rejects unavailable add-on and unrecognized variant' do
    @milk.update!(available: false)
    assert_no_difference('OrderItem.count') do
      post order_items_path, params: { order_item: {
        product_id: @drink.id, quantity: 1, product_variant_id: @medium.id,
        modifier_option_ids: [@milk.id.to_s]
      } }
    end
    other = Product.create!(category: @category, name: 'QA Other Drink', price: 2.0)
    other_variant = ProductVariant.create!(product: other, code: 'S', label: 'Small', price_cents: 200)
    assert_no_difference('OrderItem.count') do
      post order_items_path, params: { order_item: {
        product_id: @drink.id, quantity: 1, product_variant_id: other_variant.id
      } }
    end
  end

  test 'non-customizable bakery item remains purchasable' do
    pastry = Product.create!(category: @category, name: 'QA Scone', price: 3.25)
    assert_difference('OrderItem.count', 1) do
      post order_items_path, params: { order_item: { product_id: pastry.id, quantity: 1 } }
    end
    assert_redirected_to cart_path
    assert_equal BigDecimal('3.25'), OrderItem.order(:id).last[:unit_price]
  end
end
