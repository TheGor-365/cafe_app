class AccountController < ApplicationController
  before_action :authenticate_user!

  def show
    @page = 'account'
    # Orders in this legacy app are session-scoped, NOT related to users.
    # Never claim this page contains persistent order history or purchases.
    @demo_cart_count = current_order.order_items.sum(:quantity).to_i
    @demo_orders = Order.where(user_id: current_user.id).where.not(status: 'cart')
                        .order(placed_at: :desc).limit(10)
  end
end
