class PagesController < ApplicationController
  def home
    @page = 'home'
    @home_categories = Category.where(display: true).order(:heading).to_a
    @category_counts = Product.where(available: true, category_id: @home_categories.map(&:id))
                              .group(:category_id).count

    featured = Product.includes(:category).where(available: true, featured: true)
                      .order(:name).limit(3).to_a
    @featured_products = featured.presence ||
                         Product.includes(:category).where(available: true).order(:name).limit(3).to_a
  end

  def catering
    @page = 'catering'
  end

  def info
    @page = 'info'
  end
end
