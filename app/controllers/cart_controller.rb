class CartController < ApplicationController
  def show
    @page = 'cart'
    @order_items = current_order.order_items.includes(:product).to_a
  end
end
