# Rack entrypoint; production access is restricted to private portfolio reviewers.
require_relative 'config/environment'

if Rails.env.production?
  require_relative 'lib/cafe_preview_access_gate'
  use CafePreviewAccessGate,
      username: ENV.fetch('CAFE_PREVIEW_HTTP_BASIC_USER', 'portfolio'),
      password: ENV.fetch('CAFE_PREVIEW_HTTP_BASIC_PASSWORD'),
      secret: Rails.application.secret_key_base
end

run Rails.application
