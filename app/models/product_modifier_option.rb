class ProductModifierOption < ApplicationRecord
  GROUPS = %w[milk syrup shot].freeze

  belongs_to :product
  has_many :order_item_modifiers, dependent: :restrict_with_error

  validates :group_code, inclusion: { in: GROUPS }
  validates :code, :label, presence: true
  validates :code, uniqueness: { scope: [:product_id, :group_code] }
  validates :price_cents, numericality: { only_integer: true, greater_than_or_equal_to: 0 }
end
