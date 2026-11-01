require 'test_helper'

class AdminAccessTest < ActionDispatch::IntegrationTest
  include Devise::Test::IntegrationHelpers

  setup do
    @category = categories(:one)
    @product = products(:one)
    @regular = User.create!(
      username: "regular_access_test",
      email: "regular_access_test@example.test",
      password: SecureRandom.hex(24),
      admin: false
    )
  end

  test "guests cannot manage products" do
    get new_product_path
    assert_redirected_to new_user_session_path

    get edit_product_path(@product)
    assert_redirected_to new_user_session_path

    assert_no_difference "Product.count" do
      post products_path, params: { product: product_attributes }
    end
    assert_redirected_to new_user_session_path

    original_name = @product.name
    patch product_path(@product), params: { product: { name: "Unauthorized" } }
    assert_redirected_to new_user_session_path
    assert_equal original_name, @product.reload.name

    assert_no_difference "Product.count" do
      delete product_path(@product)
    end
    assert_redirected_to new_user_session_path
  end

  test "regular users cannot manage products" do
    sign_in @regular

    get new_product_path
    assert_response :forbidden

    get edit_product_path(@product)
    assert_response :forbidden

    assert_no_difference "Product.count" do
      post products_path, params: { product: product_attributes }
    end
    assert_response :forbidden

    original_name = @product.name
    patch product_path(@product), params: { product: { name: "Unauthorized" } }
    assert_response :forbidden
    assert_equal original_name, @product.reload.name

    assert_no_difference "Product.count" do
      delete product_path(@product)
    end
    assert_response :forbidden
  end

  test "guests cannot manage categories" do
    get new_category_path
    assert_redirected_to new_user_session_path

    get edit_category_path(@category)
    assert_redirected_to new_user_session_path

    assert_no_difference "Category.count" do
      post categories_path, params: { category: { heading: "Unauthorized" } }
    end
    assert_redirected_to new_user_session_path

    original_heading = @category.heading
    patch category_path(@category), params: { category: { heading: "Unauthorized" } }
    assert_redirected_to new_user_session_path
    assert_equal original_heading, @category.reload.heading

    assert_no_difference "Category.count" do
      delete category_path(@category)
    end
    assert_redirected_to new_user_session_path
  end

  test "regular users cannot manage categories" do
    sign_in @regular

    get new_category_path
    assert_response :forbidden

    get edit_category_path(@category)
    assert_response :forbidden

    assert_no_difference "Category.count" do
      post categories_path, params: { category: { heading: "Unauthorized" } }
    end
    assert_response :forbidden

    original_heading = @category.heading
    patch category_path(@category), params: { category: { heading: "Unauthorized" } }
    assert_response :forbidden
    assert_equal original_heading, @category.reload.heading

    assert_no_difference "Category.count" do
      delete category_path(@category)
    end
    assert_response :forbidden
  end

  private

  def product_attributes
    { name: "Access test", price: 10, category_id: @category.id }
  end
end
