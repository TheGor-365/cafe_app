require 'test_helper'

class CoffeeHomeCartFlowTest < ActionDispatch::IntegrationTest
  setup do
    @category = Category.create!(heading: 'Coffee Flow QA', display: true)
    @product = Product.create!(category: @category, name: 'QA Honey Latte',
                               description: 'A demo drink', price: 4.75,
                               available: true, featured: true)
  end

  test 'home has demo messaging, featured product and working menu CTA' do
    get root_path
    assert_response :success
    assert_select 'h1#cafe-home-heading', text: /Good coffee/
    assert_select "a[href='#{menu_path}']", minimum: 1
    assert_select "a[href='#{cart_path}']", minimum: 1
    assert_includes response.body, @product.name
    assert_includes response.body, 'Portfolio project'
  end

  test 'new guest sees useful empty cart' do
    get cart_path
    assert_response :success
    assert_select 'h1#cafe-cart-title'
    assert_select '.cafe-cart__empty', count: 1
    assert_select "a[href='#{menu_path}']", minimum: 1
  end

  test 'HTML form can add change quantity and remove product' do
    get menu_path
    assert_response :success
    assert_select "form[action='#{order_items_path}'][method='post']", minimum: 1

    assert_difference('OrderItem.count', 1) do
      post order_items_path, params: { order_item: { product_id: @product.id, quantity: 2 } }
    end
    assert_redirected_to cart_path
    follow_redirect!
    assert_response :success
    assert_includes response.body, @product.name
    assert_select '.cafe-cart__summary', text: /9.50/
    assert_select 'nav[aria-label="Main navigation"]', text: /Cart \(2\)/

    item = OrderItem.order(:id).last
    patch order_item_path(item), params: { order_item: {
      quantity: 3, product_id: products(:two).id, unit_price: 0.01
    } }
    assert_redirected_to cart_path
    assert_equal @product.id, item.reload.product_id
    assert_equal BigDecimal('14.25'), item[:total]

    follow_redirect!
    assert_select '.cafe-cart__summary', text: /14.25/
    assert_select 'nav[aria-label="Main navigation"]', text: /Cart \(3\)/

    assert_difference('OrderItem.count', -1) do
      delete order_item_path(item)
    end
    assert_redirected_to cart_path
    follow_redirect!
    assert_select '.cafe-cart__empty', count: 1
  end

  test 'unavailable product is rejected with no cart line' do
    @product.update!(available: false)
    assert_no_difference 'OrderItem.count' do
      post order_items_path, params: { order_item: { product_id: @product.id, quantity: 1 } }
    end
    assert_redirected_to menu_path
  end

  test 'invalid quantity is rejected in HTML mode without a saved line' do
    assert_no_difference 'OrderItem.count' do
      post order_items_path, params: { order_item: { product_id: @product.id, quantity: 0 } }
    end
    assert_redirected_to menu_path
  end

  test 'anonymous sessions do not share cart contents' do
    buyer = open_session
    other_guest = open_session
    buyer.post order_items_path, params: { order_item: { product_id: @product.id, quantity: 2 } }
    assert_equal 302, buyer.response.status
    buyer.get cart_path
    assert_includes buyer.response.body, @product.name
    other_guest.get cart_path
    assert_includes other_guest.response.body, 'Your cart is empty'
    assert_not_includes other_guest.response.body, @product.name
  end
end
