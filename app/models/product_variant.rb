class ProductVariant < ApplicationRecord
  belongs_to :product
  has_many :order_items, dependent: :restrict_with_error

  validates :code, :label, presence: true
  validates :code, uniqueness: { scope: :product_id }
  validates :price_cents, numericality: { only_integer: true, greater_than_or_equal_to: 0 }
end
