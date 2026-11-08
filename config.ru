# Run the browser session bridge before Rails; user authentication remains Devise.
require_relative 'config/environment'
require_relative 'lib/cafe_preview_access_gate'

use CafePreviewAccessGate,
    secret: Rails.application.secret_key_base

run Rails.application
