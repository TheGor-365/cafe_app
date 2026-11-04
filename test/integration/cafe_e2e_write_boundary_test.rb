# frozen_string_literal: true
require 'test_helper'

# Security tests run against a brand-new disposable Rails test PostgreSQL
# created by GitHub Actions, NEVER the owner's private fourth QA database.
# Only synthetic test users/catalog and fake avatar field values are used.
class CafeE2EWriteBoundaryTest < ActionDispatch::IntegrationTest
  include Devise::Test::IntegrationHelpers

  setup do
    @category = Category.create!(heading: 'Synthetic E2E Category', display: true)
    @product = Product.create!(
      name: 'Synthetic Test Flat White', category: @category,
      price: 4.50, available: true
    )
    @admin = User.create!(
      username: 'synthetic_e2e_admin', email: 'synthetic-admin@example.test',
      password: 'SyntheticPass123!', password_confirmation: 'SyntheticPass123!',
      admin: true
    )
    @customer = User.create!(
      username: 'synthetic_e2e_customer', email: 'synthetic-customer@example.test',
      password: 'SyntheticPass123!', password_confirmation: 'SyntheticPass123!',
      admin: false
    )
  end

  test 'non-admin cannot mutate catalogue or category through forged requests' do
    sign_in @customer
    assert_no_difference 'Product.count' do
      post products_path, params: { product: {
        name: 'Forbidden', category_id: @category.id, price: '0.01'
      } }
      assert_response :forbidden
    end
    assert_no_difference 'Category.count' do
      post categories_path, params: { category: { heading: 'Forbidden' } }
      assert_response :forbidden
    end
    assert_no_difference 'Product.count' do
      delete product_path(@product)
      assert_response :forbidden
    end
    assert Product.exists?(@product.id)
  end

  test 'product image parameter cannot be smuggled through admin product create' do
    sign_in @admin
    assert_difference 'Product.count', 1 do
      post products_path, params: { product: {
        name: 'Synthetic Admin Only', category_id: @category.id,
        price: '1.75', available: '0',
        image: 'forged_file.svg'
      } }
    end
    assert_response :redirect
    product = Product.find_by!(name: 'Synthetic Admin Only')
    assert_nil product[:image]
    assert_not product.available?
  end

  test 'Devise registration ignores forged avatar parameter and creates only a normal user' do
    assert_difference 'User.count', 1 do
      post user_registration_path, params: { user: {
        username: 'synthetic_registered', email: 'synthetic-registered@example.test',
        password: 'SyntheticPass123!', password_confirmation: 'SyntheticPass123!',
        avatar: '<svg><script>alert(1)</script></svg>',
        admin: true
      } }
    end
    assert_response :redirect
    account = User.find_by!(email: 'synthetic-registered@example.test')
    assert_not account.admin?
    assert_not User.column_names.include?('avatar')
  end

  test 'second guest session cannot edit or delete another sessions basket line' do
    buyer = open_session
    attacker = open_session
    buyer.post order_items_path, params: { order_item: {
      product_id: @product.id, quantity: 2
    } }
    assert_equal 302, buyer.response.status
    line = OrderItem.find_by!(product: @product)

    assert_raises ActiveRecord::RecordNotFound do
      attacker.patch order_item_path(line),
                     params: { order_item: { quantity: 19 } }
    end
    assert_equal 2, line.reload.quantity
    assert_raises ActiveRecord::RecordNotFound do
      attacker.delete order_item_path(line)
    end
    assert line.reload.persisted?
  end

  test 'missing CSRF token cannot create a basket line when forgery protection is on' do
    previous = ActionController::Base.allow_forgery_protection
    begin
      ActionController::Base.allow_forgery_protection = true
      assert_no_difference 'OrderItem.count' do
        assert_raises ActionController::InvalidAuthenticityToken do
          post order_items_path, params: { order_item: {
            product_id: @product.id, quantity: 1
          } }
        end
      end
    ensure
      ActionController::Base.allow_forgery_protection = previous
    end
  end
end
