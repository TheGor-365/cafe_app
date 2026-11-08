# Browser access uses standard Devise registration and sign-in.
require_relative 'config/environment'

if Rails.env.production?
  require_relative 'lib/cafe_preview_access_gate'
  use CafePreviewAccessGate, secret: Rails.application.secret_key_base
end

run Rails.application
