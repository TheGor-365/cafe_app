require 'test_helper'

class MenuControllerTest < ActionDispatch::IntegrationTest
  setup do
    @category = Category.create!(heading: "QA Menu", display: true)
    @vegan = Product.create!(
      name: "Pineapple QA Salad",
      description: "A demo dish",
      price: 9.99,
      category: @category,
      vegan: true,
      dairy_free: true
    )
    @other = Product.create!(
      name: "Carrot QA Soup",
      description: "Another demo dish",
      price: 5.99,
      category: @category,
      vegetarian: true
    )
  end

  test "menu index route works" do
    get menu_path
    assert_response :success
  end

  test "default filter and case insensitive query produce matching items" do
    body = search_body("PiNeApPlE", "Select Filter")
    assert_includes body, @vegan.name
    assert_not_includes body, @other.name
  end

  test "nil and unsupported filters do not crash or choose arbitrary columns" do
    [nil, "Unknown Flag", "admin", "name"].each do |filter|
      body = search_body("", filter)
      assert_includes body, @vegan.name
      assert_includes body, @other.name
    end
  end

  test "all six permitted dietary filters apply exactly" do
    %w[gluten_free kosher peanut_free].each do |key|
      @other.update_column(key, true)
    end
    {
      "Dairy Free" => @vegan.name,
      "Gluten Free" => @other.name,
      "Kosher" => @other.name,
      "Peanut Free" => @other.name,
      "Vegan" => @vegan.name,
      "Vegetarian" => @other.name
    }.each do |filter, expected_name|
      body = search_body("", filter)
      assert_includes body, expected_name, filter
    end
  end

  test "no match is a successful empty result" do
    body = search_body("a-unique-menu-query-never-found", "Select Filter")
    assert_not_includes body, @vegan.name
    assert_not_includes body, @other.name
  end

  test "SQL wildcard characters are interpreted literally" do
    body = search_body("%_QQ", "Select Filter")
    assert_not_includes body, @vegan.name
    assert_not_includes body, @other.name
  end

  private

  def search_body(search, filter)
    get search_path, params: { search: search, filter: filter }, xhr: true
    assert_response :success
    response.body
  end
end
