class ApplicationController < ActionController::Base

  include ApplicationHelper

  before_action :configure_permitted_parameters, if: :devise_controller?

  protected

  # Must be evaluated after authenticate_user! on protected actions.
  def require_admin!
    head :forbidden unless current_user&.admin?
  end

  def configure_permitted_parameters
    # The current local Docker app is mounted read-only, so CarrierWave cannot
    # cache/store user uploads. Reject forged avatar parameters as well as
    # disabling the upload fields; existing uploaded files are not modified.
    # Re-enable only after a verified writable, persistent private uploads mount.
    devise_parameter_sanitizer.permit(:sign_up, keys: [:username])
    devise_parameter_sanitizer.permit(:account_update, keys: [:username])
  end

end
