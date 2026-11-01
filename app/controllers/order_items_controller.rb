class OrderItemsController < ApplicationController
  before_action :set_order

  def create
    payload = params.require(:order_item)
    @order_item = @order.order_items.new(payload.permit(:product_id, :quantity))

    if @order_item.product&.available? &&
       apply_drink_configuration(@order_item, payload) &&
       @order_item.valid? && @order.save
      session[:order_id] = @order.id
      respond_to do |format|
        format.html { redirect_to cart_path, notice: 'Added to your demo cart.' }
        format.js
      end
    else
      respond_to do |format|
        format.html { redirect_to menu_path, alert: 'Invalid size, add-ons, quantity or unavailable product.' }
        format.js { head :unprocessable_entity }
      end
    end
  end

  def update
    @order_item = @order.order_items.find(params[:id])
    if @order_item.update(update_params)
      @order_items = @order.order_items
      respond_to do |format|
        format.html { redirect_to cart_path, notice: 'Cart quantity updated.' }
        format.js
      end
    else
      respond_to do |format|
        format.html { redirect_to cart_path, alert: 'Enter a valid quantity.' }
        format.js { head :unprocessable_entity }
      end
    end
  end

  def destroy
    @order_item = @order.order_items.find(params[:id])
    @order_item.destroy!
    @order_items = @order.order_items

    respond_to do |format|
      format.html { redirect_to cart_path, notice: 'Item removed from cart.' }
      format.js
    end
  end

  private

  def apply_drink_configuration(item, payload)
    product = item.product
    selected_variant_id = payload[:product_variant_id].to_s.strip
    variants = product.product_variants.where(available: true)

    variant = if variants.exists?
                variants.find_by(id: selected_variant_id)
              end
    return false if variants.exists? && variant.nil?
    return false if !variants.exists? && selected_variant_id.present?

    raw_ids = payload[:modifier_option_ids]
    return false unless raw_ids.nil? || raw_ids.is_a?(Array)

    ids = Array(raw_ids).reject(&:blank?).map do |value|
      # Integer conversion must reject strings like "1abc" and all negatives.
      string = value.to_s
      return false unless string.match?(/\A[1-9]\d*\z/)

      string.to_i
    end
    return false if ids.length > 3 || ids.uniq.length != ids.length

    options = product.product_modifier_options.where(id: ids, available: true).to_a
    return false unless options.length == ids.length
    return false unless options.map(&:group_code).uniq.length == options.length

    unit_cents = variant ? variant.price_cents : (product.price * 100).round.to_i
    unit_cents += options.sum(&:price_cents)

    item.product_variant = variant
    item.variant_label_snapshot = variant&.label
    item[:unit_price] = BigDecimal(unit_cents.to_s) / 100

    options.each do |option|
      item.order_item_modifiers.build(
        product_modifier_option: option,
        group_code_snapshot: option.group_code,
        label_snapshot: option.label,
        price_cents_snapshot: option.price_cents
      )
    end

    true
  end

  def update_params
    params.require(:order_item).permit(:quantity)
  end

  def set_order
    @order = current_order
  end
end
