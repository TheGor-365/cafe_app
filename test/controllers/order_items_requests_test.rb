require 'test_helper'

class OrderItemsRequestsTest < ActionDispatch::IntegrationTest
  setup do
    @product = products(:one)
  end

  test "adds a cart line using the server-side product price" do
    assert_difference 'OrderItem.count', 1 do
      post order_items_path, params: { order_item: {
        product_id: @product.id, quantity: 2, unit_price: 0.01, total: 0.01
      } }, xhr: true
    end

    assert_response :success
    item = OrderItem.order(:id).last
    assert_equal @product.price, item[:unit_price]
    assert_equal @product.price * 2, item[:total]
  end

  test "rejects invalid quantities on add" do
    assert_no_difference 'OrderItem.count' do
      post order_items_path, params: { order_item: {
        product_id: @product.id, quantity: 0
      } }, xhr: true
    end
    assert_response :unprocessable_entity
  end

  test "updates quantity but ignores product substitution" do
    post order_items_path, params: { order_item: {
      product_id: @product.id, quantity: 1
    } }, xhr: true
    assert_response :success
    item = OrderItem.order(:id).last

    patch order_item_path(item), params: { order_item: {
      product_id: products(:two).id, quantity: 3
    } }, xhr: true
    assert_response :success
    assert_equal @product.id, item.reload.product_id
    assert_equal @product.price * 3, item[:total]
  end

  test "rejects invalid quantities on update without changing cart" do
    post order_items_path, params: { order_item: {
      product_id: @product.id, quantity: 2
    } }, xhr: true
    assert_response :success
    item = OrderItem.order(:id).last

    patch order_item_path(item), params: { order_item: {
      quantity: 0
    } }, xhr: true
    assert_response :unprocessable_entity
    assert_equal 2, item.reload.quantity
  end
end
