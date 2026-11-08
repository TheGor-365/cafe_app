require 'test_helper'

class CoffeeDemoCheckoutTest < ActionDispatch::IntegrationTest
  setup do
    @category = Category.create!(heading: 'Demo checkout QA', display: true)
    @product = Product.create!(category: @category, name: 'Sample americano',
                               price: 4.25, available: true)
  end

  def add_item(session = self)
    session.post order_items_path, params: { order_item: {
      product_id: @product.id, quantity: 2
    } }
    assert_equal 302, session.response.status
    OrderItem.where(product_id: @product.id).order(:id).last
  end

  def submit_order(session = self, values = {})
    input = { pickup_name: 'Demo Guest', pickup_slot: 'asap',
              pickup_note: 'Fictional testing only' }.merge(values)
    session.post demo_orders_path, params: { demo_order: input }
  end

  def sign_in(user)
    post user_session_path, params: { user: {
      email: user.email, password: 'SafePass123'
    } }
    assert_response :redirect
  end

  test 'empty cart cannot be submitted or checkout page opened' do
    get demo_checkout_path
    assert_redirected_to cart_path
    assert_no_difference('Order.where(status: "pending").count') { submit_order }
    assert_redirected_to cart_path
  end

  test 'guest checkout saves a frozen price and starts an empty new cart' do
    line = add_item
    get demo_checkout_path
    assert_response :success
    assert_select "form[action='#{demo_orders_path}'][method='post']", count: 1

    assert_difference('Order.where(status: "pending").count', 1) do
      submit_order(self, status: 'completed', total: '0.01', user_id: '1')
    end
    placed = line.order.reload
    assert_equal 'pending', placed.status
    assert_nil placed.user_id
    assert_equal BigDecimal('8.50'), placed.total
    assert_equal BigDecimal('8.50'), placed[:subtotal]
    assert_redirected_to demo_order_path(placed)
    follow_redirect!
    assert_response :success
    assert_select '#demo-order-title', text: /Order #/
    assert_includes response.body, @product.name

    get cart_path
    assert_select '.cafe-cart__empty', count: 1
    assert_raises(ActiveRecord::RecordNotFound) do
      patch order_item_path(line), params: { order_item: { quantity: 1 } }
    end
    assert_equal 2, line.reload.quantity
  end

  test 'invalid sample fields cannot advance cart state' do
    line = add_item
    assert_no_difference('Order.where(status: "pending").count') do
      submit_order(self, pickup_name: 'X', pickup_slot: 'now', pickup_note: 'a' * 201)
    end
    assert_response :unprocessable_entity
    assert_equal 'cart', line.order.reload.status
  end

  test 'guest order confirmation is accessible only to same browser session' do
    buyer = open_session
    stranger = open_session
    line = add_item(buyer)
    submit_order(buyer)
    assert_equal 302, buyer.response.status
    buyer.get demo_order_path(line.order)
    assert_equal 200, buyer.response.status
    # Rails test mode raises RecordNotFound rather than rendering its production 404.
    assert_raises(ActiveRecord::RecordNotFound) do
      stranger.get demo_order_path(line.order)
    end
  end

  test 'signed in owner can see only own account history' do
    user = User.create!(username: 'demo_customer', email: 'demo-customer@example.test',
                        password: 'SafePass123', password_confirmation: 'SafePass123')
    sign_in(user)
    line = add_item
    submit_order
    order = line.order.reload
    assert_equal user.id, order.user_id
    get account_path
    assert_response :success
    assert_select "a[href='#{demo_order_path(order)}']", count: 1
  end

  test 'admin queue is denied to guests and ordinary users' do
    get admin_demo_orders_path
    assert_redirected_to new_user_session_path
    user = User.create!(username: 'demo_normal', email: 'normal@example.test',
                        password: 'SafePass123', password_confirmation: 'SafePass123')
    sign_in(user)
    get admin_demo_orders_path
    assert_response :forbidden
  end

  test 'admin can process only a legal sequence without changing price' do
    line = add_item
    submit_order
    placed = line.order.reload
    admin = User.create!(username: 'demo_admin', email: 'admin-checkout@example.test',
                         password: 'SafePass123', password_confirmation: 'SafePass123', admin: true)
    sign_in(admin)
    get admin_demo_orders_path
    assert_response :success
    assert_select '#demo-admin-title', count: 1
    assert_select "a[href='#{demo_order_path(placed)}']", minimum: 1

    patch admin_demo_order_status_path(placed), params: {
      demo_order: { status: 'completed', total: '0.01', user_id: admin.id }
    }
    assert_redirected_to admin_demo_orders_path
    assert_equal 'pending', placed.reload.status

    %w[accepted preparing ready completed].each do |step|
      patch admin_demo_order_status_path(placed), params: {
        demo_order: { status: step }
      }
      assert_redirected_to admin_demo_orders_path
      assert_equal step, placed.reload.status
      assert_equal BigDecimal('8.50'), placed.total
    end
    patch admin_demo_order_status_path(placed), params: {
      demo_order: { status: 'accepted' }
    }
    assert_equal 'completed', placed.reload.status
  end
end
