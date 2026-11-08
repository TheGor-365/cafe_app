class Product < ApplicationRecord
  mount_uploader :image, ImageUploader

  belongs_to :category
  has_many :order_items
  has_many :product_variants, dependent: :restrict_with_error
  has_many :product_modifier_options, dependent: :restrict_with_error
end
