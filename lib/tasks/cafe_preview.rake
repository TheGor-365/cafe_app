# ONLY the separately provisioned Railway Cafe preview may load fictional catalog.
# Never run this on owner-local, production, inherited, or shared databases.
namespace :cafe do
  desc 'Seed an empty, isolated Railway preview database once'
  task bootstrap_preview: :environment do
    expected_project = 'a6c48a67-c6f4-4f12-a5df-6d1de0f45d69'
    expected_environment = 'e47229ba-6dd7-47ec-9155-a329bb2a963c'
    permitted = Rails.env.production? &&
      ENV['RAILWAY_PROJECT_ID'] == expected_project &&
      ENV['RAILWAY_ENVIRONMENT_ID'] == expected_environment &&
      ENV['CAFE_PREVIEW_SEED_ALLOWED'] == 'YES'

    abort 'Cafe preview seed gate denied' unless permitted
    require 'uri'
    database = URI.parse(ENV.fetch('DATABASE_URL'))
    abort 'Cafe preview requires private Railway PostgreSQL' unless database.host.to_s.end_with?('.railway.internal')

    if Product.where(name: 'Espresso').exists? && Product.count >= 20
      puts 'Cafe preview catalog already initialized; no seed changes applied'
      next
    end

    ActiveRecord::Base.transaction do
      Rails.application.load_seed
    end
    puts 'Cafe preview fictional catalog bootstrapped'
  end
end
