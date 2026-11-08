class ProductVariantsController < ApplicationController
  before_action :authenticate_user!
  before_action :require_admin!
  before_action :set_product
  before_action :set_variant, only: %i[edit update destroy]

  def index
    @page = 'admin'
    @variants = @product.product_variants.order(:code)
  end

  def new
    @page = 'admin'
    @variant = @product.product_variants.build
  end

  def create
    @page = 'admin'
    @variant = @product.product_variants.build(variant_params)
    if @variant.save
      redirect_to product_product_variants_path(@product), notice: 'Size created.'
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
    @page = 'admin'
  end

  def update
    @page = 'admin'
    if @variant.update(variant_params)
      redirect_to product_product_variants_path(@product), notice: 'Size updated.'
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    if @variant.order_items.exists?
      redirect_to product_product_variants_path(@product),
                  alert: 'Size referenced by a saved basket: set Unavailable instead of deleting.'
    elsif @variant.destroy
      redirect_to product_product_variants_path(@product), notice: 'Unused size deleted.'
    else
      redirect_to product_product_variants_path(@product), alert: 'Size could not be deleted.'
    end
  end

  private

  def set_product
    @product = Product.find(params[:product_id])
  end

  def set_variant
    @variant = @product.product_variants.find(params[:id])
  end

  def variant_params
    params.require(:product_variant).permit(:code, :label, :price_cents, :available)
  end
end
