#!/usr/bin/env python3
"""Read-only fifth PostgreSQL TCP cluster identity proof, 2026-11-07.

--verify-cluster: compare system_identifier observed through the isolated
reviewed Ruby TCP connection against system_identifier from the exact fifth
Docker container. Only fixed MATCH/MISMATCH and socket categories are printed.

The Ruby session temporarily uses SET ROLE NONE (session superuser postgres)
ONLY to SELECT pg_control_system(), then reselects cafe_synth_owner and checks
that it is restored; there is no role DDL, database DDL/DML, fixtures, marker,
Docker service, volume, user Git source or original upload modification.
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

HOME=Path.home()
REPO=HOME/"Рабочий стол/rails_projects/lite/cafe_app"
PRIVATE=HOME/".local/share/cafe_app"
PINNED_IP_PROBE=PRIVATE/"cafe_p12_fifth_ip_consistency_probe_20261107.py"
IP_PROBE_BLOB="a46a0a1fa985a3f80140e30ac433423e794eb2d3"
SCHEMA_BLOB="d146f135e3ce964d20b46a5c65bfe5026e72fc34"
PG="cafe-upload-security-synthetic-pg-20261105"
DB="cafe_synthetic"
NET="cafe-upload-security-synthetic-net-20261105"

RUBY_CLUSTER_PROBE=r"""# frozen_string_literal: true
# Fifth-only cluster identity, no persistent writes.
require 'pg'
require 'uri'
require 'ipaddr'
require 'socket'
def assert(condition)
  exit 3 unless condition
end

uri=URI.parse(ENV.fetch('DATABASE_URL'))
target=ENV.fetch('CAFE_P12_SERVER_IP')
cluster=ENV.fetch('CAFE_P12_EXPECTED_CLUSTER_ID')
assert(uri.host=='cafe-synthetic-postgres' && uri.port==5432 &&
       uri.path=='/cafe_synthetic' && uri.user=='postgres' &&
       ENV.fetch('CAFE_P12_TARGET')=='cafe_synthetic' &&
       ENV.fetch('RAILS_ENV')=='test' && ENV.fetch('BUNDLE_PATH')=='/bundle')
assert(/\A[0-9]{13,22}\z/.match?(cluster))
assert(IPAddr.new(target).ipv4?)
client=PG.connect(ENV.fetch('DATABASE_URL'))
begin
  first=client.exec(%q{
    SELECT current_database() AS dbname, current_user AS active_user,
           session_user AS login_user,
           current_setting('server_version_num') AS server_ver,
           inet_server_addr()::text AS socket_addr,
           inet_server_port() AS socket_port
  }).first
  assert(first['dbname']=='cafe_synthetic' &&
         first['active_user']=='cafe_synth_owner' &&
         first['login_user']=='postgres' &&
         first['server_ver'].to_i/10000==16 &&
         first['socket_port'].to_i==5432)

  # SET ROLE changes only this disposable session. PostgreSQL's own
  # documentation confirms NONE returns to session_user. No persistent DDL.
  client.exec('SET ROLE NONE')
  assert(client.exec('SELECT current_user').getvalue(0,0)=='postgres')
  seen=client.exec('SELECT system_identifier::text FROM pg_control_system()')
             .getvalue(0,0)
  assert(/\A[0-9]{13,22}\z/.match?(seen))
  client.exec('SET ROLE cafe_synth_owner')
  assert(client.exec('SELECT current_user').getvalue(0,0)=='cafe_synth_owner')

  observed=first['socket_addr']
  kind=if observed.nil? || observed.empty?
    'NULL'
  elsif observed==target
    'EXACT'
  elsif IPAddr.new(observed).ipv4?
    'DIFFERENT_IPV4'
  elsif IPAddr.new(observed).ipv4_mapped?
    'IPV4_MAPPED_IPV6'
  else
    'OTHER_IPV6'
  end
  dns=Socket.getaddrinfo(uri.host,5432,nil,Socket::SOCK_STREAM)
            .map{|item|item[3]}.uniq
  dns_kind=if dns==[target]
    'EXPECTED_ONLY'
  elsif dns.include?(target)
    'EXPECTED_PLUS_OTHER'
  else
    'OTHER'
  end
  puts 'P1.2 CLUSTER PROBE ROLE RESTORED / PG16 / FIFTH DB PASS'
  puts 'P1.2 CLUSTER PROBE TCP_CLUSTER='+(seen==cluster ? 'MATCH' : 'MISMATCH')
  puts 'P1.2 CLUSTER PROBE SOCKET_KIND='+kind
  puts 'P1.2 CLUSTER PROBE DNS_KIND='+dns_kind
  puts 'P1.2 CLUSTER PROBE READ_ONLY SESSION COMPLETE'
ensure
  client.close unless client.finished?
end
"""

VALID={
  "TCP_CLUSTER":{"MATCH","MISMATCH"},
  "SOCKET_KIND":{"NULL","EXACT","DIFFERENT_IPV4","IPV4_MAPPED_IPV6","OTHER_IPV6"},
  "DNS_KIND":{"EXPECTED_ONLY","EXPECTED_PLUS_OTHER","OTHER"},
}

def require(condition,reason):
    if not condition:
        raise RuntimeError("P1.2 CLUSTER PROBE STOP: "+reason)

def import_ip():
    require(os.getuid()==1000 and REPO.is_dir() and (REPO/".git").is_dir(),
            "unexpected operator or repo")
    require(PINNED_IP_PROBE.is_file() and not PINNED_IP_PROBE.is_symlink() and
            PINNED_IP_PROBE.stat().st_uid==os.getuid() and
            PINNED_IP_PROBE.stat().st_mode&0o022==0,
            "original IP probe private file absent or unsafe")
    cmd=["git","-C",str(REPO),"hash-object",str(PINNED_IP_PROBE)]
    r=subprocess.run(cmd,capture_output=True,check=False,timeout=20)
    require(r.returncode==0 and r.stdout.decode("ascii").strip()==IP_PROBE_BLOB,
            "original IP probe Git blob SHA differs")
    spec=importlib.util.spec_from_file_location("p12_reviewed_ip_probe",PINNED_IP_PROBE)
    require(spec is not None and spec.loader is not None,
            "original IP probe import failed")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    require(mod.SCHEMA_BLOB==SCHEMA_BLOB and mod.PG==PG and
            mod.NETWORK==NET and mod.DB==DB,
            "original IP probe target changed")
    return mod

def build_command(ip_mod,schema,source,mounts,ip,cluster):
    require(re.fullmatch(r"[0-9]{13,22}",cluster) is not None,
            "fifth Docker cluster ID invalid")
    argv=ip_mod.readonly_command(schema,source,mounts,ip)
    exact="bundle exec ruby qa/security/cafe_fifth_ip_consistency_probe_20261107.rb"
    require(argv[-1].count(exact)==1 and argv[-1].endswith(exact),
            "read-only Ruby probe command differs")
    require("--network="+NET in argv and "--read-only" in argv and
            "--cap-drop=ALL" in argv and "--rm" in argv and
            "--user=1000:1000" in argv,
            "isolated runner security constraints differ")
    require(not any(x in argv[-1] for x in ("db:schema:load","db:migrate",
                                           "db:seed","db:drop","db:prepare")),
            "unexpected database write command in source runner")
    argv[-1]=argv[-1].replace(
        exact,"bundle exec ruby qa/security/cafe_fifth_ip_consistency_probe_20261107.rb")
    idx=argv.index("--entrypoint=sh")
    argv.insert(idx,"--env=CAFE_P12_EXPECTED_CLUSTER_ID="+cluster)
    return argv

def parse_output(raw):
    lines=raw.decode("utf-8",errors="replace").strip().splitlines()
    require(len(lines)==5 and
            lines[0]=="P1.2 CLUSTER PROBE ROLE RESTORED / PG16 / FIFTH DB PASS" and
            lines[-1]=="P1.2 CLUSTER PROBE READ_ONLY SESSION COMPLETE",
            "Ruby proof output missing exact expected markers")
    for index,(key,values) in enumerate(VALID.items(),start=1):
        head="P1.2 CLUSTER PROBE "+key+"="
        require(lines[index].startswith(head) and
                lines[index][len(head):] in values,
                "unrecognized Ruby proof output")
    return lines

def verify():
    ip_mod=import_ip()
    schema=ip_mod.load_schema()
    ip,ident=schema.target()
    require(ident not in schema.protected_four(),
            "fifth cluster overlaps four originals")
    require(schema.sql("SELECT count(*) FROM pg_tables WHERE schemaname='public';")=="0" and
            schema.sql("SELECT count(*) FROM pg_sequences WHERE schemaname='public';")=="0",
            "fifth schema is no longer empty")
    require(schema.sql("SELECT count(*) FROM pg_roles WHERE rolname='cafe_synth_owner' AND NOT rolcanlogin;")=="1" and
            schema.sql("SELECT count(*) FROM pg_roles WHERE rolname='cafe_synth_app' AND rolcanlogin;")=="1",
            "fifth scoped role attributes differ")
    schema.secret_audit()
    probe,mounts=schema.runtime()
    print("P1.2 CLUSTER PROBE FIFTH DOCKER/ROLES/FOUR PG/EMPTY SCHEMA PASS",flush=True)
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="cafe-p12-readonly-cluster-proof-") as stage:
        source=schema.build_source(probe,stage)
        staged=source/"qa/security/cafe_fifth_ip_consistency_probe_20261107.rb"
        require(not staged.exists() and not staged.is_symlink(),
                "reviewed source already contains a probe path")
        with staged.open("x",encoding="utf-8") as f:
            f.write(RUBY_CLUSTER_PROBE)
        argv=build_command(ip_mod,schema,source,mounts,ip,ident)
        try:
            done=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                check=False,timeout=150)
        except (OSError,subprocess.TimeoutExpired):
            raise RuntimeError("P1.2 CLUSTER PROBE STOP: ephemeral runner unavailable_or_timeout")
        require(done.returncode==0,
                "isolated read-only Ruby cluster proof failed; raw logs suppressed")
        lines=parse_output(done.stdout)
    require(schema.target()==(ip,ident) and
            schema.sql("SELECT count(*) FROM pg_tables WHERE schemaname='public';")=="0",
            "fifth target/empty schema changed after diagnostic")
    for line in lines:
        print(line,flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify-cluster",required=True,action="store_true")
    a=p.parse_args()
    try:
        if a.verify_cluster:
            verify()
    except Exception as e:
        msg=str(e)
        if not msg.startswith("P1.2 CLUSTER PROBE STOP:"):
            msg="P1.2 CLUSTER PROBE STOP: internal read-only safety gate failed"
        print(msg,file=sys.stderr,flush=True)
        print("Do not modify private credentials, markers or protected databases.",
              file=sys.stderr,flush=True)
        raise SystemExit(1)

if __name__=="__main__":
    main()
