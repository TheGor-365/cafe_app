# Consolidate only truly identical cart snapshots. No catalog price is ever
# written back to a previously added cart item. The parent order lock serializes
# two concurrent adds to the same guest session.
class CartLineConsolidator
  QuantityLimitExceeded = Class.new(StandardError)
  MAX_QUANTITY = 20

  def initialize(order)
    @order = order
  end

  # New and old cart snapshots are intentionally compared using the persisted
  # unit price and option labels/prices, not only foreign keys. This prevents
  # repriced or relabelled catalog options from retroactively changing carts.
  def self.fingerprint(line)
    extras = line.order_item_modifiers.map do |extra|
      [
        extra.group_code_snapshot,
        extra.product_modifier_option_id,
        extra.label_snapshot,
        extra.price_cents_snapshot
      ]
    end.sort_by { |value| value.map(&:to_s).join('|') }

    [line.product_id, line.product_variant_id, line.variant_label_snapshot,
     line.unit_price.to_d, extras]
  end

  def mergeable?
    return false unless @order.persisted?

    lines = @order.order_items.includes(:order_item_modifiers).to_a
    lines.group_by { |line| self.class.fingerprint(line) }.values.any? do |group|
      group.size > 1 && group.sum(&:quantity) <= MAX_QUANTITY
    end
  end

  def add!(candidate)
    raise ActiveRecord::RecordInvalid, candidate unless candidate.valid?

    @order.transaction do
      if @order.new_record?
        @order.save!
        candidate.order = @order
        candidate.save!
        refresh_subtotal!
        candidate
      else
        @order.with_lock do
          existing = @order.order_items
                           .includes(:order_item_modifiers)
                           .where(product_id: candidate.product_id,
                                  product_variant_id: candidate.product_variant_id,
                                  unit_price: candidate.unit_price,
                                  variant_label_snapshot: candidate.variant_label_snapshot)
                           .order(:id).to_a
                           .select { |line| self.class.fingerprint(line) == self.class.fingerprint(candidate) }

          desired_quantity = existing.sum(&:quantity) + candidate.quantity
          raise QuantityLimitExceeded if desired_quantity > MAX_QUANTITY

          result = if existing.any?
                     keeper = existing.shift
                     keeper.update!(quantity: desired_quantity)
                     existing.each(&:destroy!)
                     keeper
                   else
                     candidate.order = @order
                     candidate.save!
                     candidate
                   end
          refresh_subtotal!
          result
        end
      end
    end
  end

  # Explicit POST action for legacy duplicate rows already in the cart.
  # Groups above the 20-per-line limit remain separate to preserve quantities.
  def consolidate!
    return 0 unless @order.persisted?

    @order.with_lock do
      removed = 0
      groups = @order.order_items.includes(:order_item_modifiers)
                     .order(:id).to_a.group_by { |line| self.class.fingerprint(line) }

      groups.each_value do |group|
        next if group.size < 2
        next if group.sum(&:quantity) > MAX_QUANTITY

        keeper = group.shift
        keeper.update!(quantity: keeper.quantity + group.sum(&:quantity))
        group.each do |extra|
          extra.destroy!
          removed += 1
        end
      end
      refresh_subtotal! if removed.positive?
      removed
    end
  end

  private

  def refresh_subtotal!
    @order.order_items.reset
    @order.save!
  end
end
