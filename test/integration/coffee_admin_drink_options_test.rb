require 'test_helper'

class CoffeeAdminDrinkOptionsTest < ActionDispatch::IntegrationTest
  setup do
    @category = Category.create!(heading: 'Admin options QA', display: true)
    @product = Product.create!(category: @category, name: 'Demo configurable cup', price: 4.00)
    @other = Product.create!(category: @category, name: 'Other demo drink', price: 3.00)
  end

  def sign_in_admin
    user = User.create!(username: 'options_admin', email: 'options-admin@example.test',
                        password: 'SafePass123', password_confirmation: 'SafePass123',
                        admin: true)
    post user_session_path, params: { user: { email: user.email, password: 'SafePass123' } }
    assert_response :redirect
    user
  end

  test 'unauthenticated and non-admin cannot inspect configuration management' do
    get product_product_variants_path(@product)
    assert_redirected_to new_user_session_path
    get product_product_modifier_options_path(@product)
    assert_redirected_to new_user_session_path
    user = User.create!(username: 'options_guest', email: 'options-guest@example.test',
                        password: 'SafePass123', password_confirmation: 'SafePass123')
    post user_session_path, params: { user: { email: user.email, password: 'SafePass123' } }
    assert_response :redirect
    get product_product_variants_path(@product)
    assert_response :forbidden
    post product_product_modifier_options_path(@product), params: {
      product_modifier_option: { group_code: 'milk', code: 'oat', label: 'Oat', price_cents: 60 }
    }
    assert_response :forbidden
    assert_equal 0, @product.product_modifier_options.count
  end

  test 'admin creates, updates, lists and deletes an unreferenced size' do
    sign_in_admin
    get product_product_variants_path(@product)
    assert_response :success
    assert_select '#sizes-title', count: 1
    assert_difference('ProductVariant.count', 1) do
      post product_product_variants_path(@product), params: { product_variant: {
        code: 'M', label: 'Medium sample', price_cents: 525, available: '1',
        product_id: @other.id
      } }
    end
    assert_redirected_to product_product_variants_path(@product)
    size = @product.product_variants.first
    assert_equal @product.id, size.product_id
    patch product_product_variant_path(@product, size), params: {
      product_variant: { label: 'Medium 350 ml', price_cents: 575 }
    }
    assert_redirected_to product_product_variants_path(@product)
    assert_equal 575, size.reload.price_cents
    assert_equal 'Medium 350 ml', size.label

    assert_raises(ActiveRecord::RecordNotFound) do
      patch product_product_variant_path(@other, size), params: { product_variant: { price_cents: 1 } }
    end
    assert_equal 575, size.reload.price_cents

    assert_difference('ProductVariant.count', -1) do
      delete product_product_variant_path(@product, size)
    end
    assert_redirected_to product_product_variants_path(@product)
  end

  test 'referenced size cannot be deleted and saved cart price never changes' do
    sign_in_admin
    variant = ProductVariant.create!(product: @product, code: 'S',
                                     label: 'Small', price_cents: 425)
    order = Order.create!
    line = OrderItem.create!(order: order, product: @product, quantity: 2,
                             product_variant: variant, unit_price: BigDecimal('4.25'))

    patch product_product_variant_path(@product, variant), params: {
      product_variant: { price_cents: 999, available: '0' }
    }
    assert_redirected_to product_product_variants_path(@product)
    assert_equal 999, variant.reload.price_cents
    assert_equal false, variant.available?
    assert_equal BigDecimal('4.25'), line.reload.unit_price

    assert_no_difference('ProductVariant.count') do
      delete product_product_variant_path(@product, variant)
    end
    assert_redirected_to product_product_variants_path(@product)
    assert_equal BigDecimal('8.50'), line.reload.total
  end

  test 'admin can manage add-ons without touching another product or price snapshot' do
    sign_in_admin
    get product_product_modifier_options_path(@product)
    assert_response :success
    assert_select '#extras-title', count: 1

    assert_difference('ProductModifierOption.count', 1) do
      post product_product_modifier_options_path(@product), params: {
        product_modifier_option: {
          group_code: 'milk', code: 'oat', label: 'Oat sample milk', price_cents: 60,
          available: '1', product_id: @other.id
        }
      }
    end
    assert_redirected_to product_product_modifier_options_path(@product)
    extra = @product.product_modifier_options.first
    assert_equal @product.id, extra.product_id

    variant = ProductVariant.create!(product: @product, code: 'M',
                                     label: 'Medium', price_cents: 500)
    order = Order.create!
    line = OrderItem.create!(order: order, product: @product, quantity: 1,
                             product_variant: variant, unit_price: BigDecimal('5.60'))
    stored = line.order_item_modifiers.create!(
      product_modifier_option: extra, group_code_snapshot: 'milk',
      label_snapshot: extra.label, price_cents_snapshot: extra.price_cents
    )
    patch product_product_modifier_option_path(@product, extra), params: {
      product_modifier_option: { price_cents: 600, label: 'Updated oat' }
    }
    assert_redirected_to product_product_modifier_options_path(@product)
    assert_equal 600, extra.reload.price_cents
    assert_equal 60, stored.reload.price_cents_snapshot
    assert_equal BigDecimal('5.60'), line.reload.unit_price

    assert_no_difference('ProductModifierOption.count') do
      delete product_product_modifier_option_path(@product, extra)
    end
    assert_redirected_to product_product_modifier_options_path(@product)
    assert_raises(ActiveRecord::RecordNotFound) do
      patch product_product_modifier_option_path(@other, extra), params: {
        product_modifier_option: { price_cents: 1 }
      }
    end
  end

  test 'negative prices, duplicate codes and unsupported modifier groups are rejected' do
    sign_in_admin
    ProductVariant.create!(product: @product, code: 'S', label: 'Small', price_cents: 400)
    assert_no_difference('ProductVariant.count') do
      post product_product_variants_path(@product), params: {
        product_variant: { code: 'S', label: 'Duplicate', price_cents: -10 }
      }
    end
    assert_response :unprocessable_entity

    assert_no_difference('ProductModifierOption.count') do
      post product_product_modifier_options_path(@product), params: {
        product_modifier_option: { group_code: 'secret', code: 'x',
                                   label: 'Forbidden', price_cents: -10 }
      }
    end
    assert_response :unprocessable_entity
  end
end
