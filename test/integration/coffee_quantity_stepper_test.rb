require 'test_helper'

class CoffeeQuantityStepperTest < ActionDispatch::IntegrationTest
  setup do
    @category = Category.create!(heading: 'Quantity Controls QA', display: true)
    @drink = Product.create!(category: @category, name: 'Quantity QA Latte',
                             description: 'Demo test drink', price: 4.50, available: true)
    @variant = ProductVariant.create!(product: @drink, code: 'M',
                                      label: 'Medium', price_cents: 500)
  end

  test 'menu keeps native quantity field with accessible progressive step buttons' do
    get menu_path(category_id: @category.id)
    assert_response :success
    assert_select 'details[data-coffee-config]', count: 1 do
      assert_select 'form[data-coffee-price-form]' do
        assert_select 'div[data-coffee-quantity-control]', count: 1 do
          assert_select 'button[type=button][data-coffee-quantity-step="-1"][aria-label=?]',
                        "Decrease quantity for #{@drink.name}", count: 1
          assert_select 'button[type=button][data-coffee-quantity-step="1"][aria-label=?]',
                        "Increase quantity for #{@drink.name}", count: 1
          assert_select 'input[data-coffee-quantity][data-coffee-quantity-input]'                         '[name="order_item[quantity]"][min="1"][max="20"][required]',
                        count: 1
        end
      end
    end
  end

  test 'cart quantity controls preserve explicit update and server-validated totals' do
    post order_items_path, params: { order_item: {
      product_id: @drink.id, product_variant_id: @variant.id, quantity: 2
    } }
    assert_redirected_to cart_path
    item = OrderItem.last
    get cart_path
    assert_response :success
    assert_select 'form.cafe-cart__update-form', count: 1 do
      assert_select 'div[data-coffee-quantity-control]', count: 1 do
        assert_select 'button[type=button][data-coffee-quantity-step="-1"]', count: 1
        assert_select 'button[type=button][data-coffee-quantity-step="1"]', count: 1
        assert_select 'input[data-coffee-quantity-input][name="order_item[quantity]"]'                       '[min="1"][max="20"]', count: 1
      end
      assert_select 'input[type=submit][value=Update]', count: 1
    end

    patch order_item_path(item), params: { order_item: { quantity: 3 } }
    assert_redirected_to cart_path
    assert_equal 3, item.reload.quantity
    assert_equal BigDecimal('15.00'), item[:total]
  end

  test 'stepper stylesheet compiles under legacy SassC and hides buttons without JS' do
    css = Rails.root.join('app/assets/stylesheets/cafe_quantity_stepper.scss')
    compiled = SassC::Engine.new(File.read(css), syntax: :scss).render
    assert_includes compiled, '.coffee-quantity__step'
    assert_includes compiled, 'display: none'
    assert_includes compiled, '.coffee-quantity--enhanced'
    assert_includes compiled, 'focus-visible'
  end
end
