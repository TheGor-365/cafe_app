#!/usr/bin/env python3
"""P1.2 fifth-only READ-ONLY TCP/Ruby preflight diagnostic, 2026-11-07.

Run ONLY --diagnose. Uses exactly the approved schema module, PG target, role
verification and reviewed Ruby 'pre' guard. No Rails schema load, migrations,
seeds, DDL/DML, role provisioning, marker writes, DB restart or media access.
Never reveal Docker stdout/stderr, DSN, password or raw connection exceptions.
"""
from __future__ import annotations
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path.home()/"Рабочий стол/rails_projects/lite/cafe_app"
PRIVATE=Path.home()/".local/share/cafe_app"
SCHEMA=PRIVATE/"cafe_p12_fifth_schema_scoped_20261106.py"
SCHEMA_BLOB="d146f135e3ce964d20b46a5c65bfe5026e72fc34"
PG="cafe-upload-security-synthetic-pg-20261105"
DB="cafe_synthetic"
NETWORK="cafe-upload-security-synthetic-net-20261105"
MARKER=PRIVATE/"cafe_p12_fifth_schema_attempt_20261106.json"
OLD_MARKER=PRIVATE/"cafe_p12_fifth_schema_attempt_20261105.json"

GUARD_LABELS={
  "unexpected PG hostname":"guard_hostname",
  "unexpected PG port":"guard_port",
  "unexpected database name":"guard_database",
  "unexpected session login":"guard_session_login",
  "unexpected Rails environment":"guard_rails_env",
  "unexpected dependency path":"guard_bundle_path",
  "unexpected Gemfile":"guard_gemfile",
  "missing exact target pin":"guard_target_pin",
  "server IP pin format":"guard_server_pin_format",
  "wrong connected database":"guard_current_database",
  "current_user not constrained owner":"guard_current_user",
  "unexpected session_user":"guard_session_user",
  "not PostgreSQL16":"guard_pg_major",
  "unexpected PG server IP":"guard_server_ip",
  "unexpected server port":"guard_connected_port",
  "unexpected read-only mode":"guard_transaction_mode",
  "app is unexpectedly permitted CREATE":"guard_app_create",
  "app is unexpectedly permitted database DDL":"guard_app_db_create",
  "app membership differs":"guard_app_membership",
  "NONLOGIN owner missing":"guard_owner_role",
  "fifth public schema already contains tables":"guard_schema_not_empty",
  "unexpected existing public sequences":"guard_sequences_not_empty",
}
# Only the known words above may ever reach stdout; no raw error lines.
FAILURE_CLASSES=(
 ("could not translate host name","dns_resolution"),
 ("could not resolve hostname","dns_resolution"),
 ("name or service not known","dns_resolution"),
 ("temporary failure in name resolution","dns_resolution"),
 ("connection refused","tcp_refused"),
 ("no route to host","network_unreachable"),
 ("network is unreachable","network_unreachable"),
 ("password authentication failed","scram_login_rejected"),
 ("no pg_hba.conf entry","pg_hba_denied"),
 ("permission denied for relation","pg_read_privilege"),
 ("permission denied for function","pg_function_privilege"),
 ("insufficientprivilege","pg_insufficient_privilege"),
 ("undefinedfunction","pg_sql_function_missing"),
 ("syntax error at or near","pg_sql_syntax"),
 ("cannot load such file -- pg","ruby_pg_adapter_unavailable"),
 ("bundler::gemnotfound","gem_not_found"),
 ("loaderror","ruby_load_error"),
 ("could not find","dependency_missing"),
 ("read-only file system","runner_readonly_fs"),
 ("permission denied","runner_permission"),
 ("operation not permitted","runner_permission"),
 ("killed","runner_terminated"),
)

def require(ok,detail):
    if not ok:
        raise RuntimeError("P1.2 TCP DIAG STOP: "+detail)

def load_schema():
    require(os.getuid()==1000 and ROOT.is_dir() and (ROOT/".git").exists(),
            "unexpected local source or uid")
    require(SCHEMA.is_file() and not SCHEMA.is_symlink() and
            SCHEMA.stat().st_uid==os.getuid() and SCHEMA.stat().st_mode&0o022==0,
            "reviewed private schema helper missing or unsafe")
    p=subprocess.run(["git","-C",str(ROOT),"hash-object",str(SCHEMA)],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,check=False)
    require(p.returncode==0 and p.stdout.decode().strip()==SCHEMA_BLOB,
            "reviewed schema helper blob changed; STOP")
    spec=importlib.util.spec_from_file_location("p12_pinned_schema_diagnostic",SCHEMA)
    require(spec and spec.loader,"pinned schema module unavailable")
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    require(obj.PG==PG and obj.DB==DB and obj.NETWORK==NETWORK and
            obj.MARKER==MARKER and obj.OLD_SCHEMA_MARKER==OLD_MARKER and
            obj.RUBY_GUARD_BLOB=="e5dae1c3b740acf3298b5baf12747f69d4d2a721",
            "schema target identity differs")
    return obj

def safe_category(output):
    content=output.decode("utf-8",errors="replace")[:20000]
    for label,code in GUARD_LABELS.items():
        if label in content:
            return code
    lowered=content.lower()
    for needle,code in FAILURE_CLASSES:
        if needle in lowered:
            return code
    return "unclassified_runner_or_guard_failure"

def command(schema,source,mounts,ip):
    argv=schema.docker_writer(source,mounts,ip)
    # Remove ALL DDL/postflight from the shell, leaving ONLY the reviewed
    # Ruby SELECT-only preaudit. Refuse if any separator/shape differs.
    marker="; bundle exec rails db:schema:load;"
    require(argv[-1].count(marker)==1 and
            argv[-1].endswith("bundle exec ruby qa/security/cafe_fifth_schema_target_guard.rb post"),
            "schema writer shell signature differs; no runner will start")
    prefix=argv[-1].split(marker,1)[0]
    expected_end="bundle exec ruby qa/security/cafe_fifth_schema_target_guard.rb pre"
    require(prefix.endswith(expected_end),"read-only Ruby target guard differs")
    # Stable progress markers; stderr/stdout from subprocess NEVER emitted raw.
    shell=prefix.replace("set -eu; ","set -eu; printf '%s\\n' P12_DIAG_ENTERED; ",1)
    require(shell.count("P12_DIAG_ENTERED")==1,"diagnostic shell anchor differs")
    shell=shell.replace("; "+expected_end,
                       "; printf '%s\\n' P12_DIAG_BEFORE_GUARD; "+expected_end,1)
    require(shell.count("P12_DIAG_BEFORE_GUARD")==1,"guard invocation marker differs")
    require("db:schema:load" not in shell and "db:seed" not in shell and
            "db:prepare" not in shell and "db:migrate" not in shell and
            "db:drop" not in shell,"writing Rails task rejected")
    require("--read-only" in argv and "--rm" in argv and
            "--network="+NETWORK in argv and "--cap-drop=ALL" in argv and
            "--user=1000:1000" in argv,
            "ephemeral runner security flags differ")
    argv[-1]=shell
    return argv

def diagnose():
    require(not MARKER.exists() and not MARKER.is_symlink() and
            not OLD_MARKER.exists() and not OLD_MARKER.is_symlink(),
            "fifth schema attempt marker exists; do not diagnose as empty")
    schema=load_schema()
    schema.role_recovery_verified()  # verified read-only role/marker/PG/media
    probe,mounts=schema.runtime()
    schema.secret_audit()           # reads private file but never prints it
    ip,identifier=schema.target()
    require(identifier not in schema.protected_four(),
            "fifth PG overlaps protected four")
    require(schema.sql("SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';")=="0" and
            schema.sql("SELECT COUNT(*) FROM pg_sequences WHERE schemaname='public';")=="0",
            "fifth public schema is no longer empty")
    require(schema.git("cat-file","-t",schema.RUBY_GUARD_BLOB)=="blob",
            "reviewed Ruby guard not present")
    print("P1.2 TCP DIAG ORIGINAL FOUR / FIFTH ROLE / SCHEMA EMPTY PASS",flush=True)
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="cafe-p12-tcp-readonly-diag-") as stage:
        source=schema.build_source(probe,stage)
        argv=command(schema,source,mounts,ip)
        try:
            p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                             check=False,timeout=150)
        except (OSError,subprocess.TimeoutExpired):
            raise RuntimeError("P1.2 TCP DIAG STOP: transient runner unavailable_or_timeout")
        out=p.stdout[:20000]
        phase=("ruby_guard" if b"P12_DIAG_BEFORE_GUARD" in out else
               "shell_setup" if b"P12_DIAG_ENTERED" in out else
               "container_start")
        if p.returncode!=0:
            detail=safe_category(p.stderr)
            print("P1.2 TCP DIAG PHASE="+phase,flush=True)
            print("P1.2 TCP DIAG CATEGORY="+detail,flush=True)
            print("P1.2 TCP DIAG RESULT=BLOCKED; NO WRITES",flush=True)
            return
        ok=(b"P1.2 EXACT FIFTH DB/TCP IP/OWNER/APP ROLE CHECK PASS" in out and
            b"P1.2 FIFTH SCHEMA EMPTY PRE-WRITE PASS" in out)
        print("P1.2 TCP DIAG PHASE="+phase,flush=True)
        print("P1.2 TCP DIAG CATEGORY="+("ruby_select_preflight_pass" if ok else "missing_preflight_markers"),flush=True)
        print("P1.2 TCP DIAG RESULT="+("PASS" if ok else "BLOCKED")+"; NO WRITES",flush=True)
    require(schema.target()==(ip,identifier) and
            schema.sql("SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';")=="0",
            "fifth identity or schema changed after read-only diagnosis")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnose",action="store_true",required=True)
    args=parser.parse_args()
    try:
        if args.diagnose:
            diagnose()
    except Exception as exc:
        msg=str(exc)
        if not msg.startswith("P1.2 TCP DIAG STOP:"):
            msg="P1.2 TCP DIAG STOP: internal read-only safety check failed"
        print(msg,file=sys.stderr,flush=True)
        print("Preserve fifth database, source, markers and private credentials.",file=sys.stderr)
        raise SystemExit(1)

if __name__=="__main__":main()
