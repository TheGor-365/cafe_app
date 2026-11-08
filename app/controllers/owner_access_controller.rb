# Secure, one-time ownership bootstrap for the isolated Railway coffee portfolio.
# Credentials are never put in source, URLs, email or chat messages.
class OwnerAccessController < ApplicationController
  before_action :authenticate_user!
  before_action :ensure_configured!

  def new
    redirect_to products_path and return if current_user.admin?
    @owner_matches = owner_account?
    @available = !User.where(admin: true).exists?
  end

  def create
    redirect_to products_path and return if current_user.admin?

    submitted = params[:owner_access_code].to_s
    valid_secret = submitted.bytesize.between?(48, 256) &&
      ActiveSupport::SecurityUtils.secure_compare(
        Digest::SHA256.hexdigest(submitted),
        Digest::SHA256.hexdigest(ENV.fetch('CAFE_OWNER_CLAIM_TOKEN'))
      )
    unless owner_account? && valid_secret
      redirect_to new_owner_access_path, alert: 'Owner access was not verified.'
      return
    end

    claimed = false
    User.transaction do
      # Serialize simultaneous claims across every Puma worker / app instance.
      ActiveRecord::Base.connection.execute('SELECT pg_advisory_xact_lock(2026110901)')
      unless User.where(admin: true).exists?
        current_user.update!(admin: true)
        claimed = true
      end
    end

    if claimed
      redirect_to products_path, notice: 'Owner access activated.'
    else
      redirect_to account_path, alert: 'Owner access has already been activated.'
    end
  end

  private

  def owner_account?
    current_user.username.to_s.casecmp(ENV.fetch('CAFE_OWNER_USERNAME', '')).zero?
  end

  def ensure_configured!
    project_ok = Rails.env.test? || (Rails.env.production? &&
      ENV['RAILWAY_PROJECT_ID'] == 'a6c48a67-c6f4-4f12-a5df-6d1de0f45d69' &&
      ENV['RAILWAY_ENVIRONMENT_ID'] == 'e47229ba-6dd7-47ec-9155-a329bb2a963c')
    token = ENV['CAFE_OWNER_CLAIM_TOKEN'].to_s
    username = ENV['CAFE_OWNER_USERNAME'].to_s
    head :not_found unless project_ok && token.bytesize >= 48 && username.present?
  end
end
