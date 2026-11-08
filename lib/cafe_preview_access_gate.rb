# Private staging-only gate for the educational, legacy Rails application.
# This is not a replacement for upgrading unsupported dependencies.
require 'rack/auth/basic'
require 'rack/utils'

class CafePreviewAccessGate
  HEALTH_PATH = '/__cafe_health'.freeze

  def initialize(app, username:, password:)
    unless password.to_s.bytesize >= 24
      raise ArgumentError, 'Private preview HTTP Basic password must be at least 24 bytes'
    end

    @protected_app = Rack::Auth::Basic.new(app, "Gor's Coffee private preview") do |provided_user, provided_password|
      Rack::Utils.secure_compare(provided_user.to_s, username.to_s) &&
        Rack::Utils.secure_compare(provided_password.to_s, password.to_s)
    end
  end

  def call(env)
    if env['PATH_INFO'] == HEALTH_PATH && env['REQUEST_METHOD'] == 'GET'
      return healthcheck
    end

    @protected_app.call(env)
  end

  private

  def healthcheck
    # Probe the isolated database: a responsive Puma with a broken database is not healthy.
    ActiveRecord::Base.connection.select_value('SELECT 1')
    [200, { 'Content-Type' => 'text/plain; charset=utf-8', 'Cache-Control' => 'no-store' }, ['ok']]
  rescue StandardError
    [503, { 'Content-Type' => 'text/plain; charset=utf-8', 'Cache-Control' => 'no-store' }, ['unavailable']]
  end
end
