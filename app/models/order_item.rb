class OrderItem < ApplicationRecord

  belongs_to :product
  belongs_to :order

  validates :quantity, numericality: { only_integer: true, greater_than: 0 }

  before_save :set_unit_price
  before_save :set_total

  def unit_price

    if persisted?
      self[:unit_price]
    else
      product&.price
    end
  end

  def total
    return nil unless unit_price && quantity

    unit_price * quantity
  end

  private

  def set_unit_price
    self[:unit_price] = unit_price
  end

  def set_total
    self[:total] = total
  end

end
