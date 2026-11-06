# frozen_string_literal: true
# Owner-local ONLY: target audit around a separately guarded fifth PG schema load.
# No SQL DDL/DML in this file. Real writes are delegated to Rails schema:load
# only after this program's 'pre' verification within a disposable runner.
require 'pg'
require 'uri'
require 'socket'
require 'ipaddr'

EXPECTED_APP_TABLES = %w[
  categories products product_variants product_modifier_options
  orders order_items order_item_modifiers users
].freeze
EXPECTED_META_TABLES = %w[schema_migrations ar_internal_metadata].freeze
TARGET_HOST = 'cafe-synthetic-postgres'.freeze
TARGET_DB = 'cafe_synthetic'.freeze
OWNER = 'cafe_synth_owner'.freeze
APP = 'cafe_synth_app'.freeze

def blocked(message)
  abort 'P1.2 FIFTH SCHEMA TARGET STOP: ' + message
end

def assert_equal(actual, expected, label)
  blocked(label) unless actual == expected
end

def scalar(db, sql)
  db.exec(sql).getvalue(0, 0)
end

def target_guard(db)
  uri = URI.parse(ENV.fetch('DATABASE_URL'))
  assert_equal(uri.host, TARGET_HOST, 'unexpected PG hostname')
  assert_equal(uri.port, 5432, 'unexpected PG port')
  assert_equal(uri.path, '/' + TARGET_DB, 'unexpected database name')
  assert_equal(uri.user, 'postgres', 'unexpected session login')
  assert_equal(ENV.fetch('RAILS_ENV'), 'test', 'unexpected Rails environment')
  assert_equal(ENV.fetch('BUNDLE_PATH'), '/bundle', 'unexpected dependency path')
  assert_equal(ENV.fetch('BUNDLE_GEMFILE'), '/app/Gemfile', 'unexpected Gemfile')
  assert_equal(ENV.fetch('CAFE_P12_TARGET'), TARGET_DB, 'missing exact target pin')
  expected_ip = ENV.fetch('CAFE_P12_SERVER_IP')
  expected_cluster = ENV.fetch('CAFE_P12_EXPECTED_CLUSTER_ID')
  blocked('server IP pin format') unless /\A(?:\d{1,3}\.){3}\d{1,3}\z/.match?(expected_ip)
  blocked('cluster ID pin format') unless /\A[0-9]{13,22}\z/.match?(expected_cluster)
  blocked('IPv4 pin invalid') unless IPAddr.new(expected_ip).ipv4?
  resolved = Socket.getaddrinfo(TARGET_HOST, 5432, nil, Socket::SOCK_STREAM)
                   .map { |item| item[3] }.uniq
  blocked('fifth DNS alias differs') unless resolved == [expected_ip]
  actual = db.exec(%q{
    SELECT current_database(), current_user, session_user,
           current_setting('server_version_num') AS pg_version,
           inet_server_addr()::text AS server_ip,
           inet_server_port() AS server_port,
           current_setting('default_transaction_read_only') AS read_only
  }).first
  assert_equal(actual['current_database'], TARGET_DB, 'wrong connected database')
  assert_equal(actual['current_user'], OWNER, 'current_user not constrained owner')
  assert_equal(actual['session_user'], 'postgres', 'unexpected session_user')
  blocked('not PostgreSQL16') unless actual['pg_version'].to_i / 10_000 == 16
  # Docker can report a different local socket IPv4 via network translation.
  # Never accept that discrepancy by itself: validate the SAME PG16 cluster,
  # authenticated postgres session, exact fifth DNS alias, and scoped role.
  # SET ROLE NONE is limited to this disposable SQL session. Restore owner
  # before checking application ACL or allowing schema:load to start.
  blocked('non-IPv4 TCP server') unless actual['server_ip'] &&
      IPAddr.new(actual['server_ip']).ipv4?
  begin
    db.exec('SET ROLE NONE')
    assert_equal(scalar(db, 'SELECT current_user'), 'postgres',
                 'temporary cluster identity session not postgres')
    actual_cluster = scalar(db, 'SELECT system_identifier::text FROM pg_control_system()')
  ensure
    db.exec('SET ROLE cafe_synth_owner')
  end
  assert_equal(scalar(db, 'SELECT current_user'), OWNER,
               'scoped owner not restored after cluster check')
  assert_equal(actual_cluster, expected_cluster, 'TCP cluster identity differs')
  assert_equal(actual['server_port'].to_i, 5432, 'unexpected server port')
  assert_equal(actual['read_only'], 'off', 'unexpected read-only mode')
  assert_equal(scalar(db, "SELECT has_schema_privilege('cafe_synth_app', 'public', 'CREATE')"),
               'f', 'app is unexpectedly permitted CREATE')
  assert_equal(scalar(db, "SELECT has_database_privilege('cafe_synth_app', 'cafe_synthetic', 'CREATE')"),
               'f', 'app is unexpectedly permitted database DDL')
  assert_equal(scalar(db, "SELECT count(*) FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname='cafe_synth_app')"),
               '0', 'app membership differs')
  assert_equal(scalar(db, "SELECT count(*) FROM pg_roles WHERE rolname='cafe_synth_owner' AND NOT rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole"),
               '1', 'NONLOGIN owner missing')
  puts 'P1.2 EXACT FIFTH DB/TCP IP/OWNER/APP ROLE CHECK PASS'
end

def schema_tables(db)
  db.exec("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
    .column_values(0)
end

def expect_pre(db)
  assert_equal(schema_tables(db), [], 'fifth public schema already contains tables')
  assert_equal(scalar(db, "SELECT count(*) FROM pg_sequences WHERE schemaname='public'"),
               '0', 'unexpected existing public sequences')
  puts 'P1.2 FIFTH SCHEMA EMPTY PRE-WRITE PASS'
end

def expect_post(db)
  expected = (EXPECTED_APP_TABLES + EXPECTED_META_TABLES).sort
  assert_equal(schema_tables(db), expected, 'schema table list differs')
  assert_equal(scalar(db,
    "SELECT count(*) FROM pg_constraint c JOIN pg_namespace n "     "ON n.oid=c.connamespace WHERE n.nspname='public' AND c.contype='f'"),
    '8', 'foreign key count differs')
  assert_equal(scalar(db,
    "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner='cafe_synth_owner'"),
    '10', 'table ownership differs')
  assert_equal(scalar(db,
    "SELECT count(*) FROM pg_sequences WHERE schemaname='public' AND sequenceowner='cafe_synth_owner'"),
    '8', 'sequence ownership differs')
  expected_versions = Dir['/app/db/migrate/[0-9]*_*.rb']
    .map { |f| File.basename(f).split('_', 2).first }.sort
  actual_versions = db.exec('SELECT version FROM public.schema_migrations ORDER BY version')
    .column_values(0)
  assert_equal(actual_versions, expected_versions, 'migration versions differ')
  assert_equal(scalar(db, "SELECT count(*) FROM public.schema_migrations WHERE version='20261102000100'"),
               '1', 'latest canonical migration version missing')
  EXPECTED_APP_TABLES.each do |table|
    assert_equal(scalar(db, "SELECT count(*) FROM public.#{table}"),
                 '0', 'fixture data unexpectedly present: ' + table)
    %w[SELECT INSERT UPDATE DELETE].each do |privilege|
      assert_equal(scalar(db,
        "SELECT has_table_privilege('cafe_synth_app','public.#{table}','#{privilege}')"),
        't', 'app CRUD grant differs: ' + table + ' ' + privilege)
    end
  end
  puts 'P1.2 TEN OWNER TABLES / EIGHT FK / EIGHT SEQUENCES PASS'
  puts 'P1.2 EXACT MIGRATION VERSIONS / ZERO DATA / APP CRUD ACL PASS'
end

mode = ARGV.fetch(0) { blocked('missing [pre|post] audit mode') }
blocked('unsupported audit mode') unless %w[pre post].include?(mode)
# No password, DSN or raw error message is ever printed by the host orchestrator.
db = PG.connect(ENV.fetch('DATABASE_URL'))
begin
  target_guard(db)
  mode == 'pre' ? expect_pre(db) : expect_post(db)
ensure
  db.close unless db.finished?
end
