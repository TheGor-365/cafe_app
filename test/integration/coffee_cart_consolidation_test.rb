require 'test_helper'

class CoffeeCartConsolidationTest < ActionDispatch::IntegrationTest
  setup do
    @category = Category.create!(heading: 'Merge QA', display: true)
    @drink = Product.create!(category: @category, name: 'QA House Latte',
                             price: 4.25, available: true)
    @medium = ProductVariant.create!(product: @drink, code: 'M',
                                     label: 'Medium 350 ml', price_cents: 500)
    @large = ProductVariant.create!(product: @drink, code: 'L',
                                    label: 'Large 470 ml', price_cents: 575)
    @milk = ProductModifierOption.create!(product: @drink, group_code: 'milk',
               code: 'oat', label: 'Oat milk', price_cents: 60)
    @syrup = ProductModifierOption.create!(product: @drink, group_code: 'syrup',
               code: 'vanilla', label: 'Vanilla', price_cents: 55)
  end

  def add_drink(quantity, variant: @medium, extras: [@milk, @syrup])
    post order_items_path, params: { order_item: {
      product_id: @drink.id, quantity: quantity,
      product_variant_id: variant.id,
      modifier_option_ids: extras.map { |extra| extra.id.to_s }
    } }
  end

  test 'repeated identical drinks become one cart line and retain server price' do
    assert_difference('OrderItem.count', 1) { add_drink(2) }
    assert_redirected_to cart_path

    first = OrderItem.last
    assert_equal BigDecimal('6.15'), first[:unit_price]
    assert_difference('OrderItem.count', 0) do
      assert_difference('OrderItemModifier.count', 0) { add_drink(3) }
    end
    assert_redirected_to cart_path
    assert_equal first.id, OrderItem.last.id
    assert_equal 5, first.reload.quantity
    assert_equal BigDecimal('30.75'), first[:total]
    assert_equal BigDecimal('30.75'), first.order.reload[:subtotal]
    assert_equal 2, first.order_item_modifiers.count

    follow_redirect!
    assert_select '.cafe-cart__item', count: 1
    assert_select 'nav[aria-label="Main navigation"]', text: /Cart \(5\)/
    assert_select '.cafe-cart__summary', text: /30.75/
  end

  test 'modifier input order does not affect identity of a cart line' do
    add_drink(1, extras: [@milk, @syrup])
    assert_difference('OrderItem.count', 0) do
      add_drink(2, extras: [@syrup, @milk])
    end
    assert_equal 3, OrderItem.last.quantity
  end

  test 'different size or extras remain different lines' do
    add_drink(1)
    assert_difference('OrderItem.count', 1) do
      add_drink(1, variant: @large)
    end
    assert_difference('OrderItem.count', 1) do
      add_drink(1, extras: [@milk])
    end
    assert_equal 3, OrderItem.where(product: @drink).count
  end

  test 'changed catalog prices do not merge new purchases into old price snapshots' do
    add_drink(2)
    previous = OrderItem.last
    @medium.update!(price_cents: 600)
    @milk.update!(price_cents: 75)
    assert_difference('OrderItem.count', 1) { add_drink(1) }
    latest = OrderItem.last
    assert_equal BigDecimal('6.15'), previous.reload[:unit_price]
    assert_equal BigDecimal('7.30'), latest[:unit_price]
    assert_equal BigDecimal('19.60'), latest.order.reload[:subtotal]
  end

  test 'quantity cannot be merged past twenty and the original remains intact' do
    add_drink(18)
    before_line = OrderItem.last
    assert_no_difference('OrderItem.count') do
      assert_no_difference('OrderItemModifier.count') { add_drink(3) }
    end
    assert_redirected_to cart_path
    assert_equal 18, before_line.reload.quantity
    assert_equal BigDecimal('110.70'), before_line.order.reload[:subtotal]
    follow_redirect!
    assert_includes response.body, 'Maximum 20 items'
  end

  test 'combine button merges identical historical rows without adding more drinks' do
    add_drink(2)
    current = OrderItem.last

    duplicate = OrderItem.create!(
      order: current.order, product: @drink, quantity: 3,
      product_variant: @medium, variant_label_snapshot: current.variant_label_snapshot,
      unit_price: current.unit_price
    )
    current.order_item_modifiers.each do |extra|
      duplicate.order_item_modifiers.create!(
        product_modifier_option: extra.product_modifier_option,
        group_code_snapshot: extra.group_code_snapshot,
        label_snapshot: extra.label_snapshot,
        price_cents_snapshot: extra.price_cents_snapshot
      )
    end

    get cart_path
    assert_response :success
    assert_select "form[action='#{consolidate_cart_path}']", count: 1

    assert_difference('OrderItem.count', -1) do
      assert_difference('OrderItemModifier.count', -2) do
        post consolidate_cart_path
      end
    end
    assert_redirected_to cart_path
    assert_equal 5, current.reload.quantity
    assert_equal BigDecimal('30.75'), current.order.reload[:subtotal]
    follow_redirect!
    assert_select '.cafe-cart__item', count: 1
    assert_select "form[action='#{consolidate_cart_path}']", count: 0
  end

  test 'identical items exceeding twenty are never merged by manual action' do
    add_drink(15)
    first = OrderItem.last
    extra = OrderItem.create!(order: first.order, product: @drink,
             product_variant: @medium, variant_label_snapshot: first.variant_label_snapshot,
             quantity: 10, unit_price: first.unit_price)
    first.order_item_modifiers.each do |modifier|
      extra.order_item_modifiers.create!(
        product_modifier_option: modifier.product_modifier_option,
        group_code_snapshot: modifier.group_code_snapshot,
        label_snapshot: modifier.label_snapshot,
        price_cents_snapshot: modifier.price_cents_snapshot
      )
    end
    assert_no_difference('OrderItem.count') { post consolidate_cart_path }
    assert_redirected_to cart_path
    assert_equal [10, 15], first.order.order_items.order(:quantity).pluck(:quantity)
  end

  test 'plain bakery items also merge without options' do
    pastry = Product.create!(category: @category, name: 'QA Croissant',
                             price: 3.70, available: true)
    post order_items_path, params: { order_item: { product_id: pastry.id, quantity: 2 } }
    assert_difference('OrderItem.count', 0) do
      post order_items_path, params: { order_item: { product_id: pastry.id, quantity: 3 } }
    end
    line = OrderItem.find_by!(product: pastry)
    assert_equal 5, line.quantity
    assert_equal BigDecimal('18.50'), line[:total]
  end

  test 'older saved unconfigured items remain editable when a size is introduced later' do
    pastry = Product.create!(category: @category, name: 'QA Legacy Latte', price: 3.00)
    post order_items_path, params: { order_item: { product_id: pastry.id, quantity: 1 } }
    saved = OrderItem.last
    ProductVariant.create!(product: pastry, code: 'M', label: 'Medium', price_cents: 350)
    patch order_item_path(saved), params: { order_item: { quantity: 2 } }
    assert_redirected_to cart_path
    assert_equal BigDecimal('6.00'), saved.reload[:total]
  end

  test 'different guest sessions cannot consolidate each others cart lines' do
    buyer = open_session
    stranger = open_session
    buyer.post order_items_path, params: { order_item: {
      product_id: @drink.id, quantity: 2, product_variant_id: @medium.id,
      modifier_option_ids: [@milk.id.to_s]
    } }
    assert_equal 302, buyer.response.status
    saved = OrderItem.last

    stranger.post consolidate_cart_path
    assert_equal 302, stranger.response.status
    stranger.get cart_path
    assert_includes stranger.response.body, 'Your cart is empty'
    assert_equal 2, saved.reload.quantity
  end
end
