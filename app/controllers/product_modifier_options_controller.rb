class ProductModifierOptionsController < ApplicationController
  before_action :authenticate_user!
  before_action :require_admin!
  before_action :set_product
  before_action :set_option, only: %i[edit update destroy]

  def index
    @page = 'admin'
    @options = @product.product_modifier_options.order(:group_code, :code)
  end

  def new
    @page = 'admin'
    @option = @product.product_modifier_options.build
  end

  def create
    @page = 'admin'
    @option = @product.product_modifier_options.build(option_params)
    if @option.save
      redirect_to product_product_modifier_options_path(@product), notice: 'Add-on created.'
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
    @page = 'admin'
  end

  def update
    @page = 'admin'
    if @option.update(option_params)
      redirect_to product_product_modifier_options_path(@product), notice: 'Add-on updated.'
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    if @option.order_item_modifiers.exists?
      redirect_to product_product_modifier_options_path(@product),
                  alert: 'Add-on referenced by a saved basket: set Unavailable instead of deleting.'
    elsif @option.destroy
      redirect_to product_product_modifier_options_path(@product), notice: 'Unused add-on deleted.'
    else
      redirect_to product_product_modifier_options_path(@product), alert: 'Add-on could not be deleted.'
    end
  end

  private

  def set_product
    @product = Product.find(params[:product_id])
  end

  def set_option
    @option = @product.product_modifier_options.find(params[:id])
  end

  def option_params
    params.require(:product_modifier_option).permit(:group_code, :code, :label, :price_cents, :available)
  end
end
