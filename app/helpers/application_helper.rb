module ApplicationHelper

  # Render flash as escaped, non-executable HTML. The legacy version inserted
  # untrusted messages directly into JavaScript and marked them html_safe.
  def toastr_flash(messages = flash)
    alerts = messages.map do |kind, message|
      next if message.blank?

      level = case kind.to_s
              when 'notice', 'success' then 'success'
              when 'alert', 'error' then 'danger'
              else 'info'
              end

      # String.new intentionally removes a possible html_safe flag.
      text = String.new(message.to_s)
      content_tag(:div, text, class: "alert alert-#{level}", role: 'alert')
    end

    safe_join(alerts.compact)
  end

  def current_order
    if Order.find_by_id(session[:order_id]).nil?
      Order.new
    else
      Order.find_by_id(session[:order_id])
    end
  end

end
