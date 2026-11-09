# Rack entrypoint. Visitors use standard Devise sign-in/sign-up; admin access
# remains protected by per-controller authorization and the User#admin? role.
require_relative 'config/environment'
run Rails.application
