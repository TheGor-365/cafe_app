# frozen_string_literal: true
# Owner P1.4 fifth-only in-process Rack GET fault classification, NO writes.
# Prints fixed phase/status/exception codes; never prints bodies, headers, DB
# URLs, IP addresses, SQL exceptions, backtraces or secrets.
require 'uri'
require 'socket'
require 'action_dispatch/testing/integration'

class P14ProbeAssertion < StandardError; end
def probe_require(condition)
  raise P14ProbeAssertion unless condition
end
def probe_http(session, path, code, expected_status, fragment)
  $p14_phase = code
  session.get(path, headers: {'HTTP_ACCEPT' => 'text/html'})
  status = session.response.status
  unless status == expected_status
    puts 'P1.4 GET DIAG HTTP_STATUS=' + (
      [200, 301, 302, 303, 401, 403, 404, 422, 500, 503].include?(status) ?
      status.to_s : 'OTHER')
    raise P14ProbeAssertion
  end
  probe_require(session.response.body.include?(fragment)) unless fragment.nil?
end

STDOUT.sync = true
$p14_phase = 'entry'
puts 'P1.4 GET DIAG RUBY_ENTRY PASS'

begin
  $p14_phase = 'target_dns'
  dsn=URI.parse(ENV.fetch('DATABASE_URL'))
  ip=ENV.fetch('CAFE_P12_SERVER_IP')
  probe_require(dsn.scheme=='postgresql' && dsn.host=='cafe-synthetic-postgres' &&
                dsn.port==5432 && dsn.path=='/cafe_synthetic' &&
                dsn.user=='cafe_synth_app' && ENV.fetch('RAILS_ENV')=='test' &&
                ENV.fetch('CAFE_P12_TARGET')=='cafe_synthetic' &&
                ENV.fetch('BUNDLE_PATH')=='/bundle' &&
                ip.match?(/\A(?:\d{1,3}\.){3}\d{1,3}\z/))
  dns=Socket.getaddrinfo(dsn.host, dsn.port, nil, Socket::SOCK_STREAM)
            .map {|e|e[3]}.uniq
  probe_require(dns==[ip])

  $p14_phase = 'sql_identity'
  conn=ActiveRecord::Base.connection
  row=conn.select_one(%q{
    SELECT current_database() AS db,
           current_user AS active_user, session_user AS login_user,
           current_setting('server_version_num') AS version,
           current_setting('default_transaction_read_only') AS readonly
  })
  probe_require(row['db']=='cafe_synthetic' &&
                row['active_user']=='cafe_synth_app' &&
                row['login_user']=='cafe_synth_app' &&
                row['version'].to_i / 10000 == 16 &&
                row['readonly']=='on')
  $p14_phase='sql_catalog'
  counts={'categories'=>8,'products'=>20,'product_variants'=>18,
          'product_modifier_options'=>30,'users'=>0,'orders'=>0,
          'order_items'=>0,'order_item_modifiers'=>0}
  counts.each do |table,count|
    probe_require(conn.select_value("SELECT count(*) FROM public.#{table}").to_i == count)
  end
  puts 'P1.4 GET DIAG APP ROLE / POSTGRES READ-ONLY / CATALOG PASS'

  $p14_phase='rack_session'
  browser=ActionDispatch::Integration::Session.new(Rails.application)
  browser.host! 'www.example.com'
  probe_http(browser,'/','get_home',200,'No live café')
  probe_http(browser,'/menu','get_menu',200,'Espresso')
  probe_http(browser,'/menu?search=Espresso','get_search',200,'Espresso')
  probe_http(browser,'/cart','get_cart',200,'Your cart is empty')
  probe_http(browser,'/info','get_info',200,'No physical café address')
  probe_http(browser,'/catering','get_catering',200,'No booking form')
  $p14_phase='product_lookup'
  product=Product.find_by!(name:'Cappuccino')
  probe_require(product.available? && product.product_variants.count==3)
  probe_http(browser,"/products/#{product.id}",'get_product',200,'Cappuccino')
  probe_http(browser,'/users/sign_in','get_signin',200,'Sign in')
  probe_http(browser,'/users/sign_up','get_signup',200,'Create an account')
  probe_http(browser,'/users/password/new','get_password',200,'Forgot your password?')
  ['/account','/products','/categories'].zip(%w[get_account get_admin_products get_admin_categories]).each do |path,code|
    $p14_phase=code
    browser.get(path,headers: {'HTTP_ACCEPT'=>'text/html'})
    status=browser.response.status
    unless status==302
      puts 'P1.4 GET DIAG HTTP_STATUS=' + (
        [200,301,302,303,401,403,404,422,500,503].include?(status) ?
        status.to_s : 'OTHER')
      raise P14ProbeAssertion
    end
    probe_require(browser.response.headers.fetch('Location','').include?('/users/sign_in'))
  end
  $p14_phase='post_counts'
  counts.each do |table,count|
    probe_require(conn.select_value("SELECT count(*) FROM public.#{table}").to_i==count)
  end
  puts 'P1.4 GET DIAG ALL HTTP ROUTES / COUNT ASSERTIONS PASS'
rescue Exception => error
  # Never print messages, Ruby/SQL backtrace or raw untrusted class name.
  kinds={
    'P14ProbeAssertion'=>'ASSERTION',
    'PG::ConnectionBad'=>'PG_CONNECTION',
    'PG::ReadOnlySqlTransaction'=>'SQL_WRITE_BLOCKED',
    'PG::InsufficientPrivilege'=>'PG_PRIVILEGE',
    'ActiveRecord::StatementInvalid'=>'SQL_ERROR',
    'ActiveRecord::ReadOnlyError'=>'SQL_WRITE_BLOCKED',
    'ActiveRecord::RecordNotFound'=>'RECORD_NOT_FOUND',
    'ActionView::Template::Error'=>'VIEW_ERROR',
    'ActionController::RoutingError'=>'ROUTING_ERROR',
    'ActionController::UnknownFormat'=>'FORMAT_ERROR',
    'LoadError'=>'RUBY_LOAD_ERROR',
    'NameError'=>'RUBY_NAME_ERROR',
    'NoMethodError'=>'RUBY_NO_METHOD',
    'Errno::EROFS'=>'READONLY_FILESYSTEM',
    'Errno::EACCES'=>'FS_ACCESS_DENIED',
    'SystemExit'=>'GUARD_EXIT',
    'ArgumentError'=>'ARGUMENT_ERROR',
    'RuntimeError'=>'RUNTIME_ERROR',
    'ActiveSupport::MessageVerifier::InvalidSignature'=>'SESSION_ERROR'
  }
  stages=%w[entry target_dns sql_identity sql_catalog rack_session
            get_home get_menu get_search get_cart get_info get_catering
            product_lookup get_product get_signin get_signup get_password
            get_account get_admin_products get_admin_categories post_counts]
  puts 'P1.4 GET DIAG FAILED_STAGE=' + (stages.include?($p14_phase) ? $p14_phase : 'UNKNOWN')
  puts 'P1.4 GET DIAG ERROR_KIND=' + kinds.fetch(error.class.name,'OTHER_RUBY_ERROR')

  causes = []
  inspected = error
  0.upto(5) do
    break unless inspected
    causes << inspected
    inspected = inspected.cause
    break if inspected && causes.include?(inspected)
  end
  cause_names = causes.map { |entry| entry.class.name.to_s }
  # Inspect messages locally ONLY to select redacted fixed category tokens.
  # NEVER write exceptions, paths, URLs, secrets or messages to stdout/stderr.
  cause_text = causes.map { |entry| entry.message.to_s }.join("\n").downcase
  detail = if cause_names.any? { |name| name.include?('MissingEntryError') }
    'WEBPACKER_MANIFEST_ENTRY'
  elsif cause_names.any? { |name| name.include?('Webpacker') && name.include?('Compilation') }
    'WEBPACKER_COMPILE'
  elsif cause_names.any? { |name| name.include?('AssetNotFound') || name.include?('Sprockets::FileNotFound') }
    'SPROCKETS_ASSET_NOT_FOUND'
  elsif cause_names.any? { |name| name.include?('SassC::SyntaxError') }
    'SASS_COMPILATION'
  elsif cause_names.any? { |name| name == 'Errno::EROFS' }
    'FILESYSTEM_READONLY'
  elsif cause_names.any? { |name| name == 'Errno::EACCES' }
    'FILESYSTEM_PERMISSION'
  elsif cause_names.any? { |name| name.include?('ActionView::MissingTemplate') }
    'MISSING_TEMPLATE'
  elsif cause_names.any? { |name| name == 'NameError' }
    'NAME_ERROR'
  elsif cause_names.any? { |name| name == 'NoMethodError' }
    'NO_METHOD'
  elsif cause_text.include?('webpacker') && cause_text.include?('manifest')
    'WEBPACKER_MANIFEST_OR_COMPILE'
  elsif cause_text.include?('webpack') && (cause_text.include?('compile') || cause_text.include?('node_modules'))
    'WEBPACKER_DEPENDENCY'
  elsif cause_text.include?('assets are not present') || cause_text.include?('asset not found')
    'SPROCKETS_ASSET_NOT_FOUND'
  elsif cause_text.include?('read-only file system')
    'FILESYSTEM_READONLY'
  elsif cause_text.include?('permission denied')
    'FILESYSTEM_PERMISSION'
  elsif cause_text.include?('sassc') || cause_text.include?('scss syntax')
    'SASS_COMPILATION'
  else
    'OTHER_VIEW_ERROR'
  end
  asset_dir = Rails.root.join('public', 'packs-test')
  asset_manifest = asset_dir.join('manifest.json')
  puts 'P1.4 VIEW DIAG ROOT_CAUSE=' + detail
  puts 'P1.4 VIEW DIAG PACK_MANIFEST=' + (asset_manifest.file? ? 'PRESENT' : 'MISSING')
  puts 'P1.4 VIEW DIAG PUBLIC_PACKS=' + (asset_dir.directory? ? 'PRESENT' : 'MISSING')
  puts 'P1.4 VIEW DIAG NODE_MODULES=' +
       (Rails.root.join('node_modules').directory? ? 'PRESENT' : 'MISSING')

  puts 'P1.4 GET DIAG RESULT=BLOCKED; NO INTENDED DB WRITES'
  exit 6
end
