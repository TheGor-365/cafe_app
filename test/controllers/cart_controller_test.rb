require 'test_helper'

class CartControllerTest < ActionDispatch::IntegrationTest
  test 'real cart endpoint returns an empty demo cart for a new session' do
    get cart_path
    assert_response :success
    assert_select 'h1#cafe-cart-title', count: 1
    assert_select '.cafe-cart__empty', count: 1
  end
end
