class CartController < ApplicationController
  def show
    @page = 'cart'
    @order_items = current_order.order_items.includes(:product, :order_item_modifiers).to_a
  end
end
