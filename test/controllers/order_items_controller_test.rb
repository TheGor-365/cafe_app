require 'test_helper'

class OrderItemsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @category = Category.create!(heading: 'HTTP verb QA category', display: true)
    @product = Product.create!(category: @category, name: 'HTTP QA biscuit',
                               price: 2.50, available: true)
  end

  test 'POST adds, PATCH changes quantity, DELETE removes a real cart line' do
    assert_difference('OrderItem.count', 1) do
      post order_items_path, params: { order_item: {
        product_id: @product.id, quantity: 1
      } }
    end
    assert_redirected_to cart_path
    line = OrderItem.where(product_id: @product.id).order(:id).last

    patch order_item_path(line), params: {
      order_item: { quantity: 3, unit_price: 0.01 }
    }
    assert_redirected_to cart_path
    assert_equal 3, line.reload.quantity
    assert_equal BigDecimal('2.50'), line.unit_price

    assert_difference('OrderItem.count', -1) do
      delete order_item_path(line)
    end
    assert_redirected_to cart_path
  end

  test 'one guest cannot alter another guest session cart line' do
    owner = open_session
    stranger = open_session
    owner.post order_items_path, params: { order_item: {
      product_id: @product.id, quantity: 2
    } }
    assert_equal 302, owner.response.status
    line = OrderItem.where(product_id: @product.id).order(:id).last
    assert_raises(ActiveRecord::RecordNotFound) do
      stranger.patch order_item_path(line), params: { order_item: { quantity: 1 } }
    end
    assert_equal 2, line.reload.quantity
  end
end
