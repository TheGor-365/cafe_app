class MenuController < ApplicationController
  DIETARY_FILTERS = {
    'dairy free' => :dairy_free,
    'gluten free' => :gluten_free,
    'kosher' => :kosher,
    'peanut free' => :peanut_free,
    'vegan' => :vegan,
    'vegetarian' => :vegetarian
  }.freeze

  before_action :set_cats

  def index
    @page = 'menu'
    @products = Product.all
    @order_item = current_order.order_items.new
  end

  def search
    @page = 'menu'
    @order_item = current_order.order_items.new
    @products = Product.all

    query = params[:search].to_s.strip
    if query.present?
      escaped = ActiveRecord::Base.sanitize_sql_like(query)
      @products = @products.where('name ILIKE ?', "%#{escaped}%")
    end

    filter = DIETARY_FILTERS[params[:filter].to_s.strip.downcase]
    @products = @products.where(filter => true) if filter
  end

  private

  def set_cats
    @cats = Category.where(display: true)
  end
end
