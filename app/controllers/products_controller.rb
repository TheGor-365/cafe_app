class ProductsController < ApplicationController

  before_action :authenticate_user!, except: %i[index show]
  before_action :require_admin!, except: %i[index show]

  before_action :set_product, only: %i[ show edit update destroy ]

  def index
    @products = Product.all
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
    @product.category = Category.find(params[:product][:category_id])

    respond_to do |format|
      if @product.save
        format.html { redirect_to @product }
      else
        format.html { render :new }
      end
    end
  end

  def update
    @product.category = Category.find(params[:product][:category_id])

    respond_to do |format|
      if @product.update(product_params)
        format.html { redirect_to @product }
      else
        format.html { render :edit }
      end
    end
  end

  def destroy
    @product.destroy

    respond_to do |format|
      format.html { redirect_to products_url }
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
      :image,
      :image_cache,
      :category_id
    )
  end

end
