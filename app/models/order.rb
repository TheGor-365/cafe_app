class Order < ApplicationRecord
  STATUS_VALUES = %w[cart pending accepted preparing ready completed cancelled].freeze
  PICKUP_SLOTS = %w[asap fifteen_minutes thirty_minutes].freeze
  ALLOWED_TRANSITIONS = {
    'pending' => %w[accepted cancelled],
    'accepted' => %w[preparing cancelled],
    'preparing' => %w[ready cancelled],
    'ready' => %w[completed cancelled],
    'completed' => [],
    'cancelled' => []
  }.freeze

  belongs_to :user, optional: true
  has_many :order_items

  validates :status, inclusion: { in: STATUS_VALUES }
  validates :pickup_name, presence: true, length: { in: 2..60 }, if: :placed?
  validates :pickup_slot, inclusion: { in: PICKUP_SLOTS }, if: :placed?
  validates :pickup_note, length: { maximum: 200 }, allow_blank: true
  validates :total, numericality: { greater_than: 0 }, if: :placed?

  before_save :set_subtotal

  def placed?
    status != 'cart'
  end

  def allowed_next_statuses
    ALLOWED_TRANSITIONS.fetch(status, [])
  end

  def line_total
    order_items.to_a.inject(BigDecimal('0')) do |sum, item|
      sum + item.unit_price * item.quantity.to_i
    end
  end

  def subtotal
    order_items.collect { |order_item| order_item.valid? ? order_item.unit_price * order_item.quantity : 0 }.sum
  end

  private

  def set_subtotal
    self[:subtotal] = subtotal
  end
end
