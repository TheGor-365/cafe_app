class ProductsController < ApplicationController

  before_action :set_product, only: %i[ show edit update destroy ]

  def index
    @products = Product.all
  end

  def show; end

  def new
    @product = Product.new
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
      :category_id
    )
  end

end
