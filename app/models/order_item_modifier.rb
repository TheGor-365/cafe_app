class OrderItemModifier < ApplicationRecord
  belongs_to :order_item, inverse_of: :order_item_modifiers
  belongs_to :product_modifier_option

  validates :group_code_snapshot, :label_snapshot, presence: true
  validates :price_cents_snapshot, numericality: { only_integer: true, greater_than_or_equal_to: 0 }

  validate :selected_option_belongs_to_product

  private

  def selected_option_belongs_to_product
    return unless order_item && product_modifier_option

    if order_item.product_id != product_modifier_option.product_id ||
       product_modifier_option.group_code != group_code_snapshot ||
       (new_record? && !product_modifier_option.available?)
      errors.add(:product_modifier_option, 'must be available for this product')
    end
  end
end
