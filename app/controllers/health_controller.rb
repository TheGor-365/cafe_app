# Railway readiness probe: 200 only when Rails and its isolated database respond.
# Does not require authentication and exposes no application data.
class HealthController < ActionController::Base
  def show
    ActiveRecord::Base.connection.select_value('SELECT 1')
    render plain: 'ok', status: :ok
  rescue StandardError
    render plain: 'unavailable', status: :service_unavailable
  end
end
