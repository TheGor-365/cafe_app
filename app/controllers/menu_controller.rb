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
    load_menu
  end

  def search
    load_menu

    respond_to do |format|
      format.js
      format.html { render :index }
    end
  end

  private

  def set_cats
    @cats = Category.where(display: true).order(:heading).to_a
  end

  def load_menu
    @page = 'menu'
    @order_item = current_order.order_items.new

    @products = Product.includes(:category).where(available: true)
                       .where(category_id: @cats.map(&:id))

    @selected_category = @cats.find { |cat| cat.id.to_s == params[:category_id].to_s } if params[:category_id].present?
    @products = @products.where(category_id: @selected_category.id) if @selected_category

    query = params[:search].to_s.strip
    if query.present?
      escaped = ActiveRecord::Base.sanitize_sql_like(query)
      @products = @products.where('products.name ILIKE ?', "%#{escaped}%")
    end

    filter = DIETARY_FILTERS[params[:filter].to_s.strip.downcase]
    @products = @products.where(filter => true) if filter
    @products = @products.order(:name).to_a
  end
end
