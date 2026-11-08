require 'test_helper'

class CoffeeAdminConsoleTest < ActionDispatch::IntegrationTest
  include Devise::Test::IntegrationHelpers

  setup do
    @category = Category.create!(heading: 'Admin Console QA', display: true)
    @product = Product.create!(name: 'QA Catalog Product', category: @category,
                               price: 3.50, description: 'QA sample', available: true)
    @admin = User.create!(username: 'catalog_admin_qa', email: 'catalog-admin@example.test',
                          password: 'SecureTestPass123', admin: true)
    @regular = User.create!(username: 'catalog_regular_qa', email: 'catalog-regular@example.test',
                            password: 'SecureTestPass123', admin: false)
  end

  test 'guest cannot view either private management index' do
    get products_path
    assert_redirected_to new_user_session_path

    get categories_path
    assert_redirected_to new_user_session_path

    get product_path(@product)
    assert_response :success
    get menu_path
    assert_response :success
  end

  test 'regular user cannot view catalogue admin indexes' do
    sign_in @regular
    get products_path
    assert_response :forbidden
    get categories_path
    assert_response :forbidden
    get category_path(@category)
    assert_response :forbidden

    get product_path(@product)
    assert_response :success
  end

  test 'admin can review responsive product and category management tables' do
    sign_in @admin
    get products_path
    assert_response :success
    assert_select 'main.cafe-admin h1', text: 'Manage products'
    assert_select 'table.cafe-admin__table' do
      assert_select 'th', text: /QA Catalog Product/
      assert_select "a[href='#{edit_product_path(@product)}']", count: 1
    end

    get categories_path
    assert_response :success
    assert_select 'main.cafe-admin h1', text: 'Manage categories'
    assert_select 'table.cafe-admin__table' do
      assert_select 'th', text: /Admin Console QA/
      assert_select 'td', text: '1', minimum: 1
      assert_select 'span.cafe-admin__disabled', text: 'In use', minimum: 1
    end
  end

  test 'admin forms are styled and do not offer broken image uploads' do
    sign_in @admin
    get new_product_path
    assert_response :success
    assert_select 'main.cafe-admin form.cafe-admin__form' do
      assert_select 'input[name="product[image]"]', count: 0
      assert_select 'input[name="product[image_cache]"]', count: 0
      assert_select 'select[name="product[category_id]"]', count: 1
    end

    get edit_product_path(@product)
    assert_response :success
    assert_select 'main.cafe-admin form.cafe-admin__form' do
      assert_select 'input[name="product[image]"]', count: 0
    end

    get new_category_path
    assert_response :success
    assert_select 'main.cafe-admin form.cafe-admin__form' do
      assert_select 'input[name="category[heading]"]', count: 1
    end
  end

  test 'admin can update catalogue data without changing existing uploads' do
    sign_in @admin
    patch product_path(@product), params: {
      product: { name: 'Updated QA Coffee', category_id: @category.id,
                 price: '4.25', available: true }
    }
    assert_redirected_to product_path(@product)
    assert_equal 'Updated QA Coffee', @product.reload.name
    assert_equal BigDecimal('4.25'), @product.price

    patch category_path(@category), params: { category: { heading: 'Updated QA Category', display: true } }
    assert_redirected_to category_path(@category)
    assert_equal 'Updated QA Category', @category.reload.heading
  end

  test 'admin cannot delete categories containing products' do
    sign_in @admin
    assert_no_difference 'Category.count' do
      delete category_path(@category)
    end
    assert_redirected_to categories_path
    assert_equal @category.id, @product.reload.category_id
  end

  test 'admin cannot delete product referenced by options' do
    ProductVariant.create!(product: @product, label: 'Medium', code: 'M',
                           price_cents: 450, available: true)
    sign_in @admin
    assert_no_difference 'Product.count' do
      delete product_path(@product)
    end
    assert_redirected_to products_path
    assert Product.exists?(@product.id)
  end

  test 'admin stylesheet compiles for mobile with SassC' do
    css = SassC::Engine.new(Rails.root.join('app/assets/stylesheets/zzz_cafe_admin.scss').read,
                             syntax: :scss).render
    assert_includes css, 'overflow-x: auto'
    assert_includes css, '@media (max-width: 760px)'
    assert_includes css, '.cafe-admin__form'
    assert_includes css, '.cafe-admin__actions'
  end
end
