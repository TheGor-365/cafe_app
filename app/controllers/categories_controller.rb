class CategoriesController < ApplicationController

  before_action :authenticate_user!
  before_action :require_admin!

  before_action :set_category, only: %i[ show edit update destroy ]

  def index
    @page = 'admin'
    @categories = Category.includes(:products).order(:heading)
  end

  def show; end
  def edit; end

  def new
    @category = Category.new
  end

  def create
    @category = Category.new(category_params)

    respond_to do |format|
      if @category.save
        format.html { redirect_to @category }
      else
        format.html { render :new }
      end
    end
  end

  def update
    respond_to do |format|
      if @category.update(category_params)
        format.html { redirect_to @category }
      else
        format.html { render :edit }
      end
    end
  end

  def destroy
    if @category.products.exists?
      redirect_to categories_url, alert: 'This category contains products. Reassign them before deleting it.'
    elsif @category.destroy
      redirect_to categories_url, notice: 'Category removed.'
    else
      redirect_to categories_url, alert: 'Category could not be removed.'
    end
  end

  private

  def set_category
    @category = Category.find(params[:id])
  end

  def category_params
    params.require(:category).permit(:heading, :body, :display)
  end

end
