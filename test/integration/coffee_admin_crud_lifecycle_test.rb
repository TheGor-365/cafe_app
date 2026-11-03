require 'test_helper'

# Runs only in the isolated Rails test database in GitHub Actions.
# The owner's QA browser experiment uses the same CRUD contract, but this
# test never connects to the owner's local Docker or PostgreSQL instance.
class CoffeeAdminCrudLifecycleTest < ActionDispatch::IntegrationTest
  include Devise::Test::IntegrationHelpers

  setup do
    @category = Category.create!(heading: 'Lifecycle Test Coffee', display: true)
    @admin = User.create!(username: 'lifecycle_admin', email: 'lifecycle-admin@example.test',
                          password: 'TestPassword123!', admin: true)
    @regular = User.create!(username: 'lifecycle_customer', email: 'lifecycle-customer@example.test',
                            password: 'TestPassword123!', admin: false)
  end

  test 'admin can create, edit, and delete an isolated unavailable catalogue item' do
    sign_in @admin

    assert_difference 'Product.count', 1 do
      post products_path, params: { product: {
        name: 'QA Temporary Espresso Lifecycle',
        description: 'Temporary CRUD fixture, not for sale.',
        price: '4.50',
        category_id: @category.id,
        available: '0',
        featured: '0',
        catering: '0'
      } }
    end

    item = Product.find_by!(name: 'QA Temporary Espresso Lifecycle')
    assert_redirected_to product_path(item)
    assert_equal BigDecimal('4.50'), item.price
    assert_not item.available?
    assert_equal @category.id, item.category_id

    get product_path(item)
    assert_response :success
    assert_includes response.body, 'Temporarily unavailable'

    patch product_path(item), params: { product: {
      name: 'QA Updated Espresso Lifecycle',
      description: 'Updated during admin CRUD lifecycle test.',
      price: '5.25',
      category_id: @category.id,
      available: '0'
    } }
    assert_redirected_to product_path(item)
    item.reload
    assert_equal 'QA Updated Espresso Lifecycle', item.name
    assert_equal BigDecimal('5.25'), item.price
    assert_not item.available?

    assert_difference 'Product.count', -1 do
      delete product_path(item)
    end
    assert_redirected_to products_path
    assert_not Product.exists?(item.id)
    assert_equal 0, @category.products.reload.count
  end

  test 'non-admin cannot write products or categories, even with forged params' do
    sample = Product.create!(name: 'QA Protected Product', description: 'Test only',
                             price: 3.75, category: @category, available: false)
    sign_in @regular

    assert_no_difference 'Product.count' do
      post products_path, params: { product: {
        name: 'Illicit product', category_id: @category.id, price: '1.00'
      } }
      assert_response :forbidden

      delete product_path(sample)
      assert_response :forbidden
    end

    patch product_path(sample), params: { product: { price: '0.01' } }
    assert_response :forbidden
    assert_equal BigDecimal('3.75'), sample.reload.price

    assert_no_difference 'Category.count' do
      post categories_path, params: { category: {
        heading: 'Illicit category', display: true
      } }
      assert_response :forbidden

      delete category_path(@category)
      assert_response :forbidden
    end
    assert Category.exists?(@category.id)
  end
end
