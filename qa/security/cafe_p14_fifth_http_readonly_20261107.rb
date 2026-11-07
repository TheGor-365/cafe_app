# frozen_string_literal: true
# P1.4 guest-only in-process HTTP GET probe against the exact fifth PG.
# PostgreSQL default_transaction_read_only=on, app SCRAM role only.
# No rails test, fixtures loading, POST, DDL/DML, private user data or uploads.
require 'uri'
require 'socket'
require 'action_dispatch/testing/integration'

def guard(ok)
  abort 'P1.4 READONLY HTTP STOP: guarded assertion' unless ok
end

dsn = URI.parse(ENV.fetch('DATABASE_URL'))
pin = ENV.fetch('CAFE_P12_SERVER_IP')
guard(dsn.scheme == 'postgresql' &&
      dsn.host == 'cafe-synthetic-postgres' &&
      dsn.port == 5432 &&
      dsn.path == '/cafe_synthetic' &&
      dsn.user == 'cafe_synth_app' &&
      ENV.fetch('RAILS_ENV') == 'test' &&
      ENV.fetch('CAFE_P12_TARGET') == 'cafe_synthetic' &&
      ENV.fetch('BUNDLE_PATH') == '/bundle' &&
      pin.match?(/\A(?:\d{1,3}\.){3}\d{1,3}\z/))
resolved = Socket.getaddrinfo(dsn.host, dsn.port, nil, Socket::SOCK_STREAM)
                 .map { |entry| entry[3] }.uniq
guard(resolved == [pin])

connection = ActiveRecord::Base.connection
server = connection.select_one(%q{
  SELECT current_database() AS db,
         current_user AS active_user,
         session_user AS login_user,
         current_setting('server_version_num') AS version,
         current_setting('default_transaction_read_only') AS readonly
})
guard(server['db'] == 'cafe_synthetic' &&
      server['active_user'] == 'cafe_synth_app' &&
      server['login_user'] == 'cafe_synth_app' &&
      server['version'].to_i / 10_000 == 16 &&
      server['readonly'] == 'on')
guard(connection.select_value('SELECT COUNT(*) FROM public.categories').to_i == 8)
guard(connection.select_value('SELECT COUNT(*) FROM public.products').to_i == 20)
guard(connection.select_value('SELECT COUNT(*) FROM public.product_variants').to_i == 18)
guard(connection.select_value('SELECT COUNT(*) FROM public.product_modifier_options').to_i == 30)
guard(connection.select_value('SELECT COUNT(*) FROM public.users').to_i == 0)
guard(connection.select_value('SELECT COUNT(*) FROM public.orders').to_i == 0)
guard(connection.select_value('SELECT COUNT(*) FROM public.order_items').to_i == 0)
guard(connection.select_value('SELECT COUNT(*) FROM public.order_item_modifiers').to_i == 0)
puts 'P1.4 FIFTH APP SCRAM ROLE / PG16 / READ-ONLY SQL / 8-20-18-30 PASS'

# Directly exercise full Rails middleware/controllers/views, not a running
# localhost:3001/3002 service. Every request in this stage is GET only.
browser = ActionDispatch::Integration::Session.new(Rails.application)
browser.host! 'www.example.com'

def read_page(browser, path, expected, includes = nil)
  browser.get(path, headers: {'HTTP_ACCEPT' => 'text/html'})
  guard(browser.response.status == expected)
  guard(browser.response.body.include?(includes)) if includes
  true
end

read_page(browser, '/', 200, 'No live café')
read_page(browser, '/menu', 200, 'Espresso')
read_page(browser, '/menu?search=Espresso', 200, 'Espresso')
read_page(browser, '/cart', 200, 'Your cart is empty')
read_page(browser, '/info', 200, 'No physical café address')
read_page(browser, '/catering', 200, 'No booking form')
puts 'P1.4 GUEST HTTP HOME/MENU/SEARCH/CART/INFO/CATERING PASS'

cappuccino = Product.find_by!(name: 'Cappuccino')
guard(cappuccino.available? && cappuccino.product_variants.count == 3)
read_page(browser, "/products/#{cappuccino.id}", 200, 'Cappuccino')
read_page(browser, '/users/sign_in', 200, 'Sign in')
read_page(browser, '/users/sign_up', 200, 'Create an account')
read_page(browser, '/users/password/new', 200, 'Forgot your password?')
puts 'P1.4 PRODUCT DETAILS / DEVISE GUEST GET ROUTES PASS'

['/account', '/products', '/categories'].each do |path|
  browser.get(path, headers: {'HTTP_ACCEPT' => 'text/html'})
  guard(browser.response.status == 302 &&
        browser.response.headers.fetch('Location', '').include?('/users/sign_in'))
end
puts 'P1.4 GUEST ACCOUNT / ADMIN GET ACCESS CONTROL PASS'

guard(connection.select_value('SELECT COUNT(*) FROM public.users').to_i == 0)
guard(connection.select_value('SELECT COUNT(*) FROM public.orders').to_i == 0)
guard(connection.select_value('SELECT COUNT(*) FROM public.order_items').to_i == 0)
guard(connection.select_value('SELECT COUNT(*) FROM public.order_item_modifiers').to_i == 0)
guard(connection.select_value('SELECT COUNT(*) FROM public.categories').to_i == 8)
guard(connection.select_value('SELECT COUNT(*) FROM public.products').to_i == 20)
guard(connection.select_value('SELECT COUNT(*) FROM public.product_variants').to_i == 18)
guard(connection.select_value('SELECT COUNT(*) FROM public.product_modifier_options').to_i == 30)
puts 'P1.4 REAL RAILS RACK GET PROBE PASS — NO DB WRITES'
