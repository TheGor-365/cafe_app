class ProductsController < ApplicationController

  before_action :authenticate_user!, except: %i[show]
  before_action :require_admin!, except: %i[show]

  before_action :set_product, only: %i[ show edit update destroy ]

  def index
    @page = 'admin'
    @products = Product.includes(:category).order(:name)
  end

  def new
    @product = Product.new
  end
  
  def show
    # Keep the exact menu configuration form and server-side cart logic as
    # the single source of truth for the product detail page.
    @page = 'menu'
    @product = Product.includes(:category, :product_variants, :product_modifier_options).find(@product.id)
    @cats = [@product.category]
    @products = @product.available? ? [@product] : []

    # Only suggest available products from the same published category.
    # No user tracking or invented recommendations; stable, bounded query.
    @related_products = Product.includes(:product_variants)
                               .where(available: true, category_id: @product.category_id)
                               .where.not(id: @product.id)
                               .order(:name).limit(3).to_a
  end
  def edit; end

  def create
    @product = Product.new(product_params)
    respond_to do |format|
      if @product.save
        format.html { redirect_to @product }
      else
        format.html { render :new }
      end
    end
  end

  def update
    respond_to do |format|
      if @product.update(product_params)
        format.html { redirect_to @product }
      else
        format.html { render :edit }
      end
    end
  end

  def destroy
    if @product.order_items.exists? || @product.product_variants.exists? || @product.product_modifier_options.exists?
      redirect_to products_url, alert: 'This product has basket references or configuration options. Keep it unavailable instead of deleting it.'
    elsif @product.destroy
      redirect_to products_url, notice: 'Demo product removed.'
    else
      redirect_to products_url, alert: 'Product could not be removed safely.'
    end
  end

  private

  def set_product
    @product = Product.find(params[:id])
  end

  def product_params
    params.require(:product).permit(
      :name,
      :description,
      :price,
      :dairy_free,
      :gluten_free,
      :kosher,
      :peanut_free,
      :vegan,
      :vegetarian,
      :available,
      :catering,
      :featured,
      # Image uploads remain disabled until persistent writable storage is configured.
      :category_id
    )
  end

end
