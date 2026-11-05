# frozen_string_literal: true
# GitHub Actions ONLY: verify the synthetic SCRAM PostgreSQL schema + fixtures.
# No owner-local Docker, PostgreSQL, source media, or production databases.
require 'pg'
require 'uri'

EXPECTED_TABLES = %w[
  categories products product_variants product_modifier_options
  orders order_items order_item_modifiers users
].freeze
META_TABLES = %w[schema_migrations ar_internal_metadata].freeze

def stop_unless_ci!
  abort 'STOP: GitHub Actions CI-only proof' unless ENV['GITHUB_ACTIONS'] == 'true'
  abort 'STOP: RAILS_ENV must be test' unless ENV['RAILS_ENV'] == 'test'
  [ENV.fetch('DATABASE_URL'), ENV.fetch('APP_DATABASE_URL')].each do |url|
    parsed = URI.parse(url)
    abort 'STOP: wrong host/database for disposable CI' unless
      parsed.host == 'postgres' && parsed.port == 5432 &&
      parsed.path == '/cafe_synthetic'
  end
end

def connect(url)
  connection = PG.connect(url)
  raise 'Wrong PostgreSQL target' unless connection.exec('SELECT current_database()').getvalue(0, 0) == 'cafe_synthetic'
  raise 'Unexpected PostgreSQL server' unless connection.exec('SHOW server_version_num').getvalue(0, 0).to_i / 10000 == 16
  if block_given?
    begin
      yield connection
    ensure
      connection.close unless connection.finished?
    end
  else
    connection
  end
end

def scalar(connection, sql)
  connection.exec(sql).getvalue(0, 0)
end

def equal!(connection, sql, expected, label)
  got = scalar(connection, sql)
  raise "#{label}: expected #{expected.inspect}, got #{got.inspect}" unless got == expected.to_s
  puts "#{label} PASS"
end

def admin(&block)
  connect(ENV.fetch('DATABASE_URL'), &block)
end

def app(&block)
  connect(ENV.fetch('APP_DATABASE_URL'), &block)
end

def table_names(connection)
  connection.exec("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").column_values(0)
end

def assert_roles!(connection)
  equal!(connection, "SELECT count(*) FROM pg_roles WHERE rolname='cafe_synth_owner' AND NOT rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolbypassrls", 1, 'NONLOGIN OWNER')
  equal!(connection, "SELECT count(*) FROM pg_roles WHERE rolname='cafe_synth_app' AND rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolbypassrls", 1, 'NONADMIN APPLICATION')
  equal!(connection, "SELECT count(*) FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname='cafe_synth_app')", 0, 'NO INHERITED MEMBERSHIPS')
  equal!(connection, "SELECT count(*) FROM pg_authid WHERE rolname='cafe_synth_app' AND rolpassword LIKE 'SCRAM-SHA-256$%'", 1, 'SCRAM PASSWORD HASH')
  equal!(connection, "SELECT has_schema_privilege('cafe_synth_app','public','CREATE')", 'f', 'APP SCHEMA DDL DENIED')
  equal!(connection, "SELECT has_database_privilege('cafe_synth_app','cafe_synthetic','CREATE')", 'f', 'APP DATABASE DDL DENIED')
  equal!(connection, "SELECT has_database_privilege('cafe_synth_app','postgres','CONNECT')", 'f', 'CROSS DATABASE CONNECT DENIED')
end

def rejected!(label)
  begin
    yield
  rescue PG::Error => error
    auth_refusal = error.is_a?(PG::ConnectionBad) &&
      error.message.match?(/password authentication failed|permission denied for database/i)
    raise "#{label}: unexpected error #{error.class}" unless
      error.is_a?(PG::InsufficientPrivilege) || auth_refusal
    puts "#{label} PASS"
    return
  end
  raise "#{label}: unexpectedly succeeded"
end

def verify_auth!
  app { |connection| equal!(connection, 'SELECT 1', 1, 'GOOD SCRAM LOGIN') }
  parsed = URI.parse(ENV.fetch('APP_DATABASE_URL'))
  rejected!('WRONG SCRAM PASSWORD DENIED') do
    PG.connect(host: 'postgres', port: 5432, dbname: 'cafe_synthetic',
               user: parsed.user, password: 'DefinitelyInvalidSyntheticPassword').close
  end
  rejected!('APP OTHER DATABASE DENIED') do
    PG.connect(host: 'postgres', port: 5432, dbname: 'postgres',
               user: parsed.user, password: parsed.password).close
  end
end

stop_unless_ci!
case ARGV.fetch(0)
when 'provision'
  admin do |connection|
    raise 'STOP: public schema was not empty before roles' unless table_names(connection).empty?
    connection.exec(File.read('qa/security/cafe_synthetic_roles_acl_ci.sql'))
    assert_roles!(connection)
    raise 'STOP: roles provision caused unexpected tables' unless table_names(connection).empty?
    puts 'DISPOSABLE SCOPED ROLES / EMPTY PG PASS'
  end
when 'preload'
  admin do |connection|
    assert_roles!(connection)
    raise 'STOP: public schema already populated' unless table_names(connection).empty?
    puts 'EMPTY PRE-SCHEMA GATE PASS'
  end
  verify_auth!
when 'owner'
  # PGOPTIONS must also be set on the adjacent Rails schema:load step.
  admin do |connection|
    equal!(connection, 'SELECT current_user', 'cafe_synth_owner', 'OWNER SESSION ROLE')
    equal!(connection, 'SELECT session_user', 'postgres', 'PRIVILEGED CI SESSION')
  end
when 'schema'
  admin do |connection|
    expected = (EXPECTED_TABLES + META_TABLES).sort
    got = table_names(connection)
    raise "Unexpected tables: #{got.inspect}, expected #{expected.inspect}" unless got == expected
    equal!(connection, "SELECT count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' AND c.contype='f'", 8, 'EIGHT FOREIGN KEYS')
    equal!(connection, "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner='cafe_synth_owner'", 10, 'TEN OWNER-OWNED TABLES INCLUDING META')
    equal!(connection, "SELECT count(*) FROM pg_sequences WHERE schemaname='public' AND sequenceowner='cafe_synth_owner'", 8, 'EIGHT OWNER-OWNED SEQUENCES')
    equal!(connection, "SELECT count(*) FROM schema_migrations WHERE version='20261102000100'", 1, 'LATEST CANONICAL MIGRATION VERSION')
    equal!(connection, "SELECT count(*) FROM schema_migrations", 1, 'EXACT SCHEMA MIGRATION COUNT')
    EXPECTED_TABLES.each do |table|
      %w[SELECT INSERT UPDATE DELETE].each do |privilege|
        equal!(connection, "SELECT has_table_privilege('cafe_synth_app','public.#{table}','#{privilege}')", 't', "APP #{privilege} #{table}")
      end
    end
    equal!(connection, "SELECT has_schema_privilege('cafe_synth_app','public','CREATE')", 'f', 'APP NO CREATE')
    puts 'RAILS CANONICAL SCHEMA / OWNER / ACL PASS'
  end
when 'seeds'
  app do |connection|
    {'categories'=>8, 'products'=>20, 'product_variants'=>18,
     'product_modifier_options'=>30, 'users'=>0, 'orders'=>0,
     'order_items'=>0, 'order_item_modifiers'=>0}.each do |table, count|
      equal!(connection, "SELECT count(*) FROM public.#{table}", count, "SYNTHETIC #{table.upcase}")
    end
    begin
      connection.exec('BEGIN')
      connection.exec("INSERT INTO public.categories(heading,body,display,created_at,updated_at) VALUES ('synthetic transaction test','test',false,NOW(),NOW())")
      connection.exec("UPDATE public.categories SET body='changed' WHERE heading='synthetic transaction test'")
      connection.exec("DELETE FROM public.categories WHERE heading='synthetic transaction test'")
      connection.exec('ROLLBACK')
    ensure
      connection.exec('ROLLBACK') if connection.transaction_status == PG::PQTRANS_INTRANS
    end
    equal!(connection, 'SELECT count(*) FROM public.categories', 8, 'APP DML / ROLLBACK')
    rejected!('APP CREATE TABLE DENIED') { connection.exec('CREATE TABLE public.forbidden_fixture(id integer)') }
    rejected!('APP CREATE ROLE DENIED') { connection.exec('CREATE ROLE forbidden_fixture LOGIN') }
    raise 'Forbidden table appeared' if table_names(connection).include?('forbidden_fixture')
    puts 'FICTIONAL CATALOGUE / OWNER-LESS APP / NEGATIVE ACL PASS'
  end
else
  abort 'Usage: ruby qa/security/cafe_synthetic_schema_seeds_ci.rb [provision|preload|owner|schema|seeds]'
end
