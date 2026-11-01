class ApplicationController < ActionController::Base

  include ApplicationHelper

  before_action :configure_permitted_parameters, if: :devise_controller?

  protected

  # Must be evaluated after authenticate_user! on protected actions.
  def require_admin!
    head :forbidden unless current_user&.admin?
  end

  def configure_permitted_parameters
    devise_parameter_sanitizer.permit(:sign_up, keys: [:username, :avatar, :avatar_cache])
    devise_parameter_sanitizer.permit(:account_update, keys: [:username, :avatar, :avatar_cache])
  end

end
