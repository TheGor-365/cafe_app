require 'test_helper'

class CoffeeLayoutReflowTest < ActionDispatch::IntegrationTest
  test 'cart renders navigation, main, account and normal escaped flash markup' do
    get cart_path
    assert_response :success
    assert_select 'div.page-container.row', count: 1
    assert_select 'div.page-container > nav.cafe-sidebar', count: 1
    assert_select 'div.page-container > div.col-8', count: 1
    assert_select 'div.page-container > div.col-1.p-2', count: 1
    assert_select 'h1#cafe-cart-title', count: 1

    post order_items_path, params: { order_item: { product_id: -1, quantity: 1 } }
    assert_redirected_to menu_path
    follow_redirect!
    assert_select 'div.page-container > div.alert.alert-danger[role=alert]', count: 1
  end

  test 'layout polish stylesheet compiles under legacy SassC and avoids 100vw shell' do
    stylesheet = Rails.root.join('app/assets/stylesheets/zz_cafe_layout_reflow.scss')
    output = SassC::Engine.new(File.read(stylesheet), syntax: :scss).render

    assert_includes output, 'grid-template-areas'
    assert_includes output, 'grid-area: main'
    assert_includes output, 'position: fixed'
    assert_includes output, 'overflow-x: hidden'
    assert_includes output, 'min-width: 0'
    assert_includes output, 'max-width: 760px'
  end
end
