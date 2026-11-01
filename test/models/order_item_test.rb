require 'test_helper'

class OrderItemTest < ActiveSupport::TestCase
  setup do
    @product = products(:one)
    @order = orders(:one)
  end

  test "persists unit price times quantity exactly once" do
    [1, 2, 3].each do |quantity|
      item = OrderItem.create!(order: @order, product: @product, quantity: quantity)
      expected = @product.price * quantity

      assert_equal expected, item.total
      assert_equal expected, item.reload[:total]
      assert_equal @product.price, item[:unit_price]
    end
  end

  test "updating quantity recalculates total without squaring quantity" do
    item = OrderItem.create!(order: @order, product: @product, quantity: 2)
    item.update!(quantity: 3)

    assert_equal @product.price * 3, item.reload[:total]
    assert_equal @product.price * 3, item.total
  end

  test "keeps original unit price when product price later changes" do
    item = OrderItem.create!(order: @order, product: @product, quantity: 1)
    original_price = item[:unit_price]

    @product.update_column(:price, original_price + 25)
    item.update!(quantity: 2)

    assert_equal original_price, item.reload[:unit_price]
    assert_equal original_price * 2, item[:total]
  end

  test "rejects missing zero negative and fractional quantities" do
    [nil, 0, -1, 1.5].each do |quantity|
      item = OrderItem.new(order: @order, product: @product, quantity: quantity)
      assert_not item.valid?, "quantity #{quantity.inspect} should be invalid"
    end
  end
end
