class OrderItemsController < ApplicationController

  before_action :set_order

  def create
    @order_item = @order.order_items.new(create_params)

    if @order_item.valid? && @order.save
      session[:order_id] = @order.id
    else
      head :unprocessable_entity
    end
  end

  def update
    @order_item = @order.order_items.find(params[:id])
    if @order_item.update(update_params)
      @order_items = current_order.order_items
    else
      head :unprocessable_entity
    end
  end

  def destroy
    @order_item = @order.order_items.find(params[:id])
    @order_item.destroy
    @order_items = current_order.order_items
  end

  private

  def create_params
    params.require(:order_item).permit(:product_id, :quantity)
  end

  # Never allow an existing cart line to be swapped to a different product.
  def update_params
    params.require(:order_item).permit(:quantity)
  end

  def set_order
    @order = current_order
  end

end
