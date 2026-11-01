require 'test_helper'

class CoffeeStorefrontTest < ActionDispatch::IntegrationTest
  setup do
    @coffee = Category.create!(heading: "QA Coffee", display: true)
    @bakery = Category.create!(heading: "QA Bakery", display: true)
    @latte = Product.create!(
      name: "QA Coffee Latte", description: "A warm test latte",
      category: @coffee, price: 4.75, available: true, featured: true
    )
    @croissant = Product.create!(
      name: "QA Flaky Croissant", description: "Pastry for testing",
      category: @bakery, price: 3.95, available: true
    )
  end

  test "public menu renders accessible forms and category navigation" do
    get menu_path
    assert_response :success
    assert_select 'h1#coffee-menu-title'
    assert_select 'nav[aria-label="Menu categories"]'
    assert_select "article.coffee-product-card", minimum: 2
    assert_select "form[action='#{order_items_path}'][method='post']", minimum: 2
    assert_select "input[name='order_item[product_id]'][value='#{@latte.id}']", count: 1
  end

  test "category navigation shows only selected category" do
    get menu_path(category_id: @coffee.id)
    assert_response :success
    assert_includes response.body, @latte.name
    assert_not_includes response.body, @croissant.name
  end

  test "unknown category falls back to all available products" do
    get menu_path(category_id: 'not-a-valid-id')
    assert_response :success
    assert_includes response.body, @latte.name
    assert_includes response.body, @croissant.name
  end

  test "text search works without JavaScript" do
    get menu_path(search: 'coffee latte')
    assert_response :success
    assert_includes response.body, @latte.name
    assert_not_includes response.body, @croissant.name
  end

  test "unavailable products never appear in public menu" do
    @latte.update!(available: false)
    get menu_path
    assert_response :success
    assert_not_includes response.body, @latte.name
    assert_includes response.body, @croissant.name
  end

  test "empty results show a reset action" do
    get menu_path(search: 'unfindable-qa-demo-coffee')
    assert_response :success
    assert_select '.coffee-menu__empty'
    assert_select "a[href='#{menu_path}']", text: 'View the full menu'
  end
end
