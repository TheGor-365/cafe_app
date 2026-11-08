class CartController < ApplicationController
  def show
    @page = 'cart'
    order = current_order
    @order_items = order.order_items.includes(:product, :order_item_modifiers).to_a
    @mergeable_lines = CartLineConsolidator.new(order).mergeable?
  end

  def consolidate
    removed = CartLineConsolidator.new(current_order).consolidate!
    message = removed.positive? ? 'Identical cart entries combined.' : 'No matching entries to combine.'
    redirect_to cart_path, notice: message
  end
end
