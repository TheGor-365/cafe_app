class DemoOrdersController < ApplicationController
  before_action :authenticate_user!, only: %i[index update]
  before_action :require_admin!, only: %i[index update]

  class InvalidCheckout < StandardError; end
  class InvalidTransition < StandardError; end

  def new
    @page = 'cart'
    @order = current_order
    unless @order.persisted? && @order.order_items.exists?
      redirect_to cart_path, alert: 'Add something to your cart before demo checkout.'
    end
  end

  def create
    @page = 'cart'
    @order = current_order
    unless @order.persisted?
      redirect_to cart_path, alert: 'Your demo cart is empty.'
      return
    end

    values = params.require(:demo_order).permit(:pickup_name, :pickup_slot, :pickup_note)
    begin
      @order.with_lock do
        raise InvalidCheckout unless @order.status == 'cart'
        raise InvalidCheckout if @order.order_items.empty?
        raise InvalidCheckout unless @order.order_items.all? { |line| line.quantity.to_i.between?(1, 20) && line.unit_price.to_d > 0 }

        @order.assign_attributes(values)
        @order.user = current_user if user_signed_in?
        @order.status = 'pending'
        @order.placed_at = Time.current
        @order.total = @order.line_total
        @order.save!
      end
      session.delete(:order_id)
      session[:last_demo_order_id] = @order.id
      redirect_to demo_order_path(@order), notice: 'Demo order recorded — no payment or real preparation.'
    rescue ActiveRecord::RecordInvalid
      render :new, status: :unprocessable_entity
    rescue InvalidCheckout
      redirect_to cart_path, alert: 'Demo checkout could not be completed. Review the cart.'
    end
  end

  def show
    @page = 'cart'
    scope = Order.where.not(status: 'cart')
    id = params[:id].to_s
    @order = if current_user&.admin? || session[:last_demo_order_id].to_s == id
               scope.find(id)
             elsif user_signed_in?
               scope.where(user_id: current_user.id).find(id)
             else
               raise ActiveRecord::RecordNotFound
             end
    @items = @order.order_items.includes(:product, :order_item_modifiers)
  end

  def index
    @page = 'admin'
    @orders = Order.where.not(status: 'cart').includes(:order_items)
                   .order(placed_at: :desc, id: :desc).limit(100)
  end

  def update
    @page = 'admin'
    @order = Order.where.not(status: 'cart').find(params[:id])
    new_status = params.require(:demo_order).permit(:status)[:status].to_s
    begin
      @order.with_lock do
        raise InvalidTransition unless @order.allowed_next_statuses.include?(new_status)
        @order.update!(status: new_status)
      end
      redirect_to admin_demo_orders_path, notice: 'Demo order status updated.'
    rescue InvalidTransition
      redirect_to admin_demo_orders_path, alert: 'Invalid status transition.'
    end
  end
end
