class OrderItem < ApplicationRecord
  belongs_to :product
  belongs_to :order
  belongs_to :product_variant, optional: true
  has_many :order_item_modifiers, inverse_of: :order_item, dependent: :destroy

  validates :quantity, numericality: {
    only_integer: true, greater_than: 0, less_than_or_equal_to: 20
  }
  validates_associated :order_item_modifiers
  validate :verify_variant_and_modifier_groups

  before_save :set_unit_price
  before_save :set_total

  # Never recalculate a persisted cart line from a changed catalog price.
  def unit_price
    self[:unit_price] || product&.price
  end

  def total
    return nil unless unit_price && quantity

    unit_price * quantity
  end

  private

  def verify_variant_and_modifier_groups
    if product
      if new_record? && product.product_variants.exists? && product_variant.nil?
        errors.add(:product_variant, 'is required for this drink')
      elsif product_variant &&
            (product_variant.product_id != product.id || (!persisted? && !product_variant.available?))
        errors.add(:product_variant, 'must belong to this product and be available when added')
      end
    end

    groups = order_item_modifiers.reject(&:marked_for_destruction?).map(&:group_code_snapshot)
    errors.add(:order_item_modifiers, 'may contain only one selection per group') if groups.uniq.length != groups.length
    errors.add(:order_item_modifiers, 'may contain at most three additions') if groups.length > 3
  end

  def set_unit_price
    self[:unit_price] = unit_price
  end

  def set_total
    self[:total] = total
  end
end
