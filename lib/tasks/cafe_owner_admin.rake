# One-shot, isolated Railway owner role promotion.
# This does not create an account and does not alter any password or another app's DB.
namespace :cafe do
  desc 'Assign admin to the existing, screenshot-verified owner Eric in the isolated Railway preview'
  task promote_existing_owner: :environment do
    next unless ENV['CAFE_OWNER_PROMOTE_ON_START'] == 'YES'

    abort 'Not the expected Railway Cafe preview' unless
      Rails.env.production? &&
      ENV['RAILWAY_PROJECT_ID'] == 'a6c48a67-c6f4-4f12-a5df-6d1de0f45d69' &&
      ENV['RAILWAY_ENVIRONMENT_ID'] == 'e47229ba-6dd7-47ec-9155-a329bb2a963c' &&
      ENV['CAFE_OWNER_USERNAME'] == 'Eric' &&
      ENV.fetch('CAFE_OWNER_CLAIM_TOKEN', '').bytesize >= 32

    require 'uri'
    database = URI.parse(ENV.fetch('DATABASE_URL'))
    abort 'Owner promotion requires the dedicated private Railway database' unless
      database.host.to_s.end_with?('.railway.internal')

    owner = User.find_by!(username: 'Eric')
    abort 'Owner account does not have an encrypted password' if owner.encrypted_password.blank?
    if owner.admin?
      puts 'Cafe owner Eric already has admin role; no changes applied'
    else
      owner.update!(admin: true)
      puts 'Cafe owner Eric promoted to admin (existing account, password unchanged)'
    end
  end
end
