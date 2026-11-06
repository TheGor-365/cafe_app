#!/usr/bin/env python3
"""Fifth-only, no-write IP consistency probe for the stopped P1.2 schema gate.

--probe-ip checks the reviewed fifth PostgreSQL identity, then compares
Docker's container endpoint to the PostgreSQL TCP server socket and DNS alias.
Emits ONLY fixed categories. Never prints internal IPs, DSN, secrets, SQL
stderr, or Docker inspect JSON. No schema/role/volume/marker writes.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

REPO=Path.home()/"Рабочий стол/rails_projects/lite/cafe_app"
PRIVATE=Path.home()/".local/share/cafe_app"
SCHEMA=PRIVATE/"cafe_p12_fifth_schema_scoped_20261106.py"
SCHEMA_BLOB="d146f135e3ce964d20b46a5c65bfe5026e72fc34"
PG="cafe-upload-security-synthetic-pg-20261105"
NETWORK="cafe-upload-security-synthetic-net-20261105"
DB="cafe_synthetic"
SOURCE="090b9d37419fcd9f393d8b686ac0f4563ef7b613"
RUBY_GUARD_BLOB="e5dae1c3b740acf3298b5baf12747f69d4d2a721"

RUBY_PROBE=r"""# frozen_string_literal: true
# ONLY immutable identity SELECT; all output tokens are from fixed enumerations.
require 'pg'
require 'uri'
require 'ipaddr'
require 'socket'

def gate(condition)
  exit 3 unless condition
end

uri = URI.parse(ENV.fetch('DATABASE_URL'))
expected_text = ENV.fetch('CAFE_P12_SERVER_IP')
gate(uri.host == 'cafe-synthetic-postgres' &&
     uri.port == 5432 &&
     uri.path == '/cafe_synthetic' &&
     uri.user == 'postgres' &&
     ENV.fetch('CAFE_P12_TARGET') == 'cafe_synthetic' &&
     ENV.fetch('RAILS_ENV') == 'test')
expected = IPAddr.new(expected_text)
gate(expected.ipv4? && expected_text.match?(/\A(?:\d{1,3}\.){3}\d{1,3}\z/))
db = PG.connect(ENV.fetch('DATABASE_URL'))
begin
  row = db.exec(%q{
    SELECT current_database() AS dbname, current_user AS username,
           session_user AS sessionname,
           current_setting('server_version_num') AS serverver,
           inet_server_addr()::text AS socket_ip,
           inet_server_port() AS socket_port
  }).first
  gate(row['dbname'] == 'cafe_synthetic' &&
       row['username'] == 'cafe_synth_owner' &&
       row['sessionname'] == 'postgres' &&
       row['serverver'].to_i / 10000 == 16 &&
       row['socket_port'].to_i == 5432)
  observed_text = row['socket_ip']
  if observed_text.nil? || observed_text.empty?
    kind = 'NULL_OR_LOCAL_SOCKET'
  elsif observed_text == expected_text
    kind = 'EXACT_MATCH'
  else
    observed = IPAddr.new(observed_text)
    if observed.ipv4?
      kind = 'DIFFERENT_IPV4'
    elsif observed.ipv4_mapped?
      kind = 'IPV4_MAPPED_IPV6'
    else
      kind = 'OTHER_IPV6'
    end
  end

  resolved = Socket.getaddrinfo(uri.host, uri.port, nil, Socket::SOCK_STREAM)
                   .map { |entry| entry[3] }.uniq
  dns = if resolved.empty?
    'EMPTY'
  elsif resolved.include?(expected_text)
    resolved.length == 1 ? 'EXPECTED_ONLY' : 'EXPECTED_PLUS_OTHER'
  else
    'OTHER_ONLY'
  end
  observed_in_dns = resolved.include?(observed_text) ? 'YES' : 'NO'

  puts 'P1.2 IP PROBE PG16/FIFTH DB/SCOPED ROLE/TCP PASS'
  puts 'P1.2 IP PROBE SOCKET_KIND=' + kind
  puts 'P1.2 IP PROBE DNS_KIND=' + dns
  puts 'P1.2 IP PROBE SOCKET_IN_DNS=' + observed_in_dns
  puts 'P1.2 IP PROBE RESULT=READ_ONLY'
ensure
  db.close unless db.finished?
end
"""

TOKENS={
    "SOCKET_KIND":{"NULL_OR_LOCAL_SOCKET","EXACT_MATCH","DIFFERENT_IPV4",
                   "IPV4_MAPPED_IPV6","OTHER_IPV6"},
    "DNS_KIND":{"EMPTY","EXPECTED_ONLY","EXPECTED_PLUS_OTHER","OTHER_ONLY"},
    "SOCKET_IN_DNS":{"YES","NO"},
}

def require(condition,label):
    if not condition:
        raise RuntimeError("P1.2 IP PROBE STOP: "+label)

def load_schema():
    require(os.getuid()==1000 and REPO.is_dir() and
            (REPO/".git").is_dir(),"unrecognized owner or Git repository")
    require(SCHEMA.is_file() and not SCHEMA.is_symlink() and
            SCHEMA.stat().st_uid==os.getuid() and
            SCHEMA.stat().st_mode&0o022==0,
            "reviewed owner-only schema helper absent or unsafe")
    p=subprocess.run(["git","-C",str(REPO),"hash-object",str(SCHEMA)],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     check=False,timeout=20)
    require(p.returncode==0 and p.stdout.decode("ascii").strip()==SCHEMA_BLOB,
            "reviewed 06.11 helper SHA differs")
    spec=importlib.util.spec_from_file_location("p12_original_schema_inspection",SCHEMA)
    require(spec is not None and spec.loader is not None,"private schema import unavailable")
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    require(obj.PG==PG and obj.DB==DB and obj.NETWORK==NETWORK and
            obj.SOURCE==SOURCE and obj.RUBY_GUARD_BLOB==RUBY_GUARD_BLOB,
            "fifth target or reviewed guard changed")
    require(not obj.MARKER.exists() and not obj.MARKER.is_symlink() and
            not obj.OLD_SCHEMA_MARKER.exists() and
            not obj.OLD_SCHEMA_MARKER.is_symlink(),
            "one-shot schema marker exists; do not proceed")
    return obj

def readonly_command(schema,source,mounts,ip):
    argv=schema.docker_writer(source,mounts,ip)
    original=argv[-1]
    marker="; bundle exec rails db:schema:load;"
    require(original.count(marker)==1 and original.endswith(
        "bundle exec ruby qa/security/cafe_fifth_schema_target_guard.rb post"),
        "original fifth-only writer signature differs")
    prefix=original.split("; bundle exec ruby qa/security/cafe_fifth_schema_target_guard.rb pre;",1)
    require(len(prefix)==2 and prefix[1].startswith(" bundle exec rails db:schema:load;"),
            "original read-only guard boundary not found")
    shell=prefix[0]+"; bundle exec ruby qa/security/cafe_fifth_ip_consistency_probe_20261107.rb"
    require(shell.startswith('set -eu; password="$(cat /tmp/cafe_p12_secret)"; ') and
            shell.count("DATABASE_URL=")==1 and
            shell.count("cafe_fifth_ip_consistency_probe_20261107.rb")==1,
            "diagnostic shell prefix differs")
    require(not any(x in shell for x in ("db:schema:load","db:seed","db:prepare",
                                       "db:migrate","db:drop","cafe_fifth_schema_target_guard.rb")),
            "writing/postflight command not fully removed")
    require("--rm" in argv and "--read-only" in argv and
            "--network="+NETWORK in argv and "--cap-drop=ALL" in argv and
            "--security-opt=no-new-privileges" in argv and
            "--user=1000:1000" in argv and
            not any(x=="--network=host" for x in argv),
            "disposable Docker security contract changed")
    argv[-1]=shell
    return argv

def safe_output(stdout):
    lines=stdout.decode("utf-8",errors="replace").strip().splitlines()
    prefix="P1.2 IP PROBE "
    require(len(lines)==5 and
            lines[0]=="P1.2 IP PROBE PG16/FIFTH DB/SCOPED ROLE/TCP PASS" and
            lines[-1]=="P1.2 IP PROBE RESULT=READ_ONLY",
            "Ruby probe missing fixed identity markers")
    for i,(key,choices) in enumerate(TOKENS.items(),start=1):
        require(lines[i].startswith(prefix+key+"=") and
                lines[i].split("=",1)[-1] in choices,
                "Ruby probe returned unrecognized output category")
    return lines

def probe():
    schema=load_schema()
    ip,ident=schema.target()
    require(ident not in schema.protected_four(),
            "fifth PG overlaps original protected databases")
    require(schema.sql("SELECT count(*) FROM pg_tables WHERE schemaname='public';")=="0" and
            schema.sql("SELECT count(*) FROM pg_sequences WHERE schemaname='public';")=="0",
            "fifth target not empty")
    require(schema.sql("SELECT count(*) FROM pg_roles WHERE rolname='cafe_synth_owner' AND NOT rolcanlogin;")=="1" and
            schema.sql("SELECT count(*) FROM pg_roles WHERE rolname='cafe_synth_app' AND rolcanlogin;")=="1",
            "scoped roles differ from recovered state")
    schema.secret_audit()
    runtime,mounts=schema.runtime()
    print("P1.2 IP PROBE FIFTH/FOUR PG/EMPTY SCHEMA/ROLES PASS",flush=True)
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="cafe-p12-fifth-ip-check-") as stage:
        source=schema.build_source(runtime,stage)
        path=source/"qa/security/cafe_fifth_ip_consistency_probe_20261107.rb"
        require(not path.exists() and not path.is_symlink(),
                "probe path already exists in reviewed source")
        with path.open("x",encoding="utf-8") as out:
            out.write(RUBY_PROBE)
        argv=readonly_command(schema,source,mounts,ip)
        try:
            completed=subprocess.run(argv,stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,check=False,timeout=150)
        except (OSError,subprocess.TimeoutExpired):
            raise RuntimeError("P1.2 IP PROBE STOP: isolated runner unavailable_or_timeout")
        require(completed.returncode==0,
                "isolated Ruby socket identity query failed; raw logs suppressed")
        for line in safe_output(completed.stdout):
            print(line,flush=True)
    require(schema.target()==(ip,ident) and
            schema.sql("SELECT count(*) FROM pg_tables WHERE schemaname='public';")=="0",
            "fifth target changed after diagnostic")

def main():
    arg=argparse.ArgumentParser(description=__doc__)
    arg.add_argument("--probe-ip",action="store_true",required=True)
    options=arg.parse_args()
    try:
        if options.probe_ip:
            probe()
    except Exception as error:
        msg=str(error)
        if not msg.startswith("P1.2 IP PROBE STOP:"):
            msg="P1.2 IP PROBE STOP: internal read-only verification failure"
        print(msg,file=sys.stderr,flush=True)
        print("Preserve protected databases, fifth-only marker and secrets; do not run DDL.",
              file=sys.stderr,flush=True)
        raise SystemExit(1)

if __name__=="__main__":
    main()
