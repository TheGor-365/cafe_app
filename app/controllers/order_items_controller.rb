class OrderItemsController < ApplicationController
  before_action :set_order

  def create
    @order_item = @order.order_items.new(create_params)

    if @order_item.product&.available? && @order_item.valid? && @order.save
      session[:order_id] = @order.id
      respond_to do |format|
        format.html { redirect_to cart_path, notice: 'Added to your demo cart.' }
        format.js
      end
    else
      respond_to do |format|
        format.html { redirect_to menu_path, alert: 'Could not add this item. Check availability and quantity.' }
        format.js { head :unprocessable_entity }
      end
    end
  end

  def update
    @order_item = @order.order_items.find(params[:id])
    if @order_item.update(update_params)
      @order_items = @order.order_items
      respond_to do |format|
        format.html { redirect_to cart_path, notice: 'Cart quantity updated.' }
        format.js
      end
    else
      respond_to do |format|
        format.html { redirect_to cart_path, alert: 'Enter a valid quantity.' }
        format.js { head :unprocessable_entity }
      end
    end
  end

  def destroy
    @order_item = @order.order_items.find(params[:id])
    @order_item.destroy!
    @order_items = @order.order_items

    respond_to do |format|
      format.html { redirect_to cart_path, notice: 'Item removed from cart.' }
      format.js
    end
  end

  private

  def create_params
    params.require(:order_item).permit(:product_id, :quantity)
  end

  def update_params
    # The client may only change quantity, never the product or its price.
    params.require(:order_item).permit(:quantity)
  end

  def set_order
    @order = current_order
  end
end
