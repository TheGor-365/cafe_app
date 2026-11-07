#!/usr/bin/env python3
"""P1.4 fifth-only GET failure classification. --diagnose ONLY, no DB writes.

Use the unchanged SHA-verified original P1.4 owner Python/Ruby scripts to
obtain exact SCRAM app identity / runtime / readonly PGOPTIONS. Substitute
an independently SHA-reviewed, staged diagnostic Ruby Rack GET program in
the same isolated disposable runner. Classify stage and error without logging
SQL exceptions, HTTP bodies, tracebacks, URLs, private IPs or credentials.
The independent P1.3 fixture verify runs before AND after the diagnosis.
"""
from __future__ import annotations
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HOME=Path.home()
ROOT=HOME/"Рабочий стол/rails_projects/lite/cafe_app"
PRIV=HOME/".local/share/cafe_app"
P14=PRIV/"cafe_p14_fifth_http_readonly_20261107.py"
P14_BLOB="426414d64584231df380c9588c9e0b80e32589c7"
ORIG_RUBY=PRIV/"cafe_p14_fifth_http_readonly_20261107.rb"
ORIG_RUBY_BLOB="299de6d74f55fe04c222875ca424b6c2c7443b5f"
DIAG_RUBY=PRIV/"cafe_p14_fifth_http_fault_diagnostic_20261107.rb"
DIAG_RUBY_BLOB="e7738e20f8d8656a685d0084f31f19a5e04bed64"
DB="cafe_synthetic"
NETWORK="cafe-upload-security-synthetic-net-20261105"

STAGES=set("""entry target_dns sql_identity sql_catalog rack_session get_home get_menu
get_search get_cart get_info get_catering product_lookup get_product
get_signin get_signup get_password get_account get_admin_products
get_admin_categories post_counts UNKNOWN BOOT""".split())
ERROR_KINDS=set("""ASSERTION PG_CONNECTION SQL_WRITE_BLOCKED PG_PRIVILEGE SQL_ERROR
RECORD_NOT_FOUND VIEW_ERROR ROUTING_ERROR FORMAT_ERROR RUBY_LOAD_ERROR
RUBY_NAME_ERROR RUBY_NO_METHOD READONLY_FILESYSTEM FS_ACCESS_DENIED
GUARD_EXIT ARGUMENT_ERROR RUNTIME_ERROR SESSION_ERROR
OTHER_RUBY_ERROR RUBY_DID_NOT_START BOOT_DEPENDENCY BOOT_FILESYSTEM
BOOT_UNCLASSIFIED""".split())
STATUS=set("200 301 302 303 401 403 404 422 500 503 OTHER".split())

def require(ok,reason):
    if not ok:
        raise RuntimeError("P1.4 GET DIAG STOP: "+reason)

def checked_file(path,sha):
    require(path.is_file() and not path.is_symlink() and
            path.stat().st_uid==os.getuid() and
            path.stat().st_mode&0o077==0,
            "private reviewed helper missing/unsafe")
    result=subprocess.run(["git","-C",str(ROOT),"hash-object",str(path)],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          timeout=20,check=False)
    require(result.returncode==0 and
            result.stdout.decode("ascii").strip()==sha,
            "private reviewed helper Git blob differs")

def module():
    require(os.getuid()==1000 and ROOT.is_dir() and (ROOT/".git").is_dir(),
            "unexpected owner or repository")
    checked_file(P14,P14_BLOB)
    checked_file(ORIG_RUBY,ORIG_RUBY_BLOB)
    checked_file(DIAG_RUBY,DIAG_RUBY_BLOB)
    spec=importlib.util.spec_from_file_location("p14_original_http_probe",P14)
    require(spec is not None and spec.loader is not None,
            "reviewed P1.4 module import unavailable")
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    require(m.DB==DB and m.NET==NETWORK and
            m.RUBY_BLOB==ORIG_RUBY_BLOB and
            m.P13_BLOB=="8dbf42b86a4c617fb69c986e9103fce631d3a49e",
            "reviewed P1.4 source/target pins differ")
    return m

def command(p14,schema,src,mounts,ip,cluster,secret):
    argv=p14.runner_command(schema,src,mounts,ip,cluster,secret)
    old="bundle exec rails runner qa/security/cafe_p14_fifth_http_readonly_20261107.rb"
    new="bundle exec rails runner qa/security/cafe_p14_fifth_http_fault_diagnostic_20261107.rb"
    require(argv[-1].count(old)==1 and argv[-1].endswith(old),
            "original read-only Rack runner differs")
    argv[-1]=argv[-1].replace(old,new)
    for required in ("--rm","--read-only","--cap-drop=ALL",
                     "--security-opt=no-new-privileges",
                     "--network="+NETWORK,
                     "--user=1000:1000",
                     "--env=RAILS_ENV=test",
                     "--env=PGOPTIONS=-c default_transaction_read_only=on -c search_path=public",
                     "--env=CAFE_P12_EXPECTED_CLUSTER_ID="+cluster):
        require(required in argv,"fifth-only readonly Docker contract differs")
    require(not any(bad in argv[-1] for bad in (
        "db:schema:load","db:seed","db:drop","db:migrate","db:prepare",
        "rails test","cafe_fifth_schema_cluster_guard_20261107.rb")),
        "unexpected schema/seed/fixture database command")
    require(not any(arg.startswith(("--publish","-p=","--privileged","--network=host"))
                    for arg in argv),
            "unexpected Docker publishing/privileges")
    return argv

def output_classification(raw,returncode,stderr):
    # Only exact predefined tokens are accepted. ALL other stdout is ignored,
    # including application logs/stack traces, and NEVER returned to user.
    lines=raw.decode("utf-8",errors="replace")[:40000].splitlines()
    entry="P1.4 GET DIAG RUBY_ENTRY PASS" in lines
    scope="P1.4 GET DIAG APP ROLE / POSTGRES READ-ONLY / CATALOG PASS" in lines
    finished="P1.4 GET DIAG ALL HTTP ROUTES / COUNT ASSERTIONS PASS" in lines
    def one(prefix,choices):
        selected=[l[len(prefix):] for l in lines if l.startswith(prefix)
                  and l[len(prefix):] in choices]
        return selected[0] if len(selected)==1 else None
    stage=one("P1.4 GET DIAG FAILED_STAGE=",STAGES)
    kind=one("P1.4 GET DIAG ERROR_KIND=",ERROR_KINDS)
    status=one("P1.4 GET DIAG HTTP_STATUS=",STATUS)
    if returncode==0 and finished and entry and scope:
        return ("PASSED","ALL_GETS_PASS","NONE",None)
    if entry and stage is not None and kind is not None:
        return ("BLOCKED",stage,kind,status)
    # Boot diagnostics are fixed categories only; error lines remain private.
    low=stderr.decode("utf-8",errors="replace")[:5000].lower()
    if "could not find" in low or "cannot load such file" in low:
        category="BOOT_DEPENDENCY"
    elif "read-only file system" in low or "permission denied" in low:
        category="BOOT_FILESYSTEM"
    elif not entry:
        category="RUBY_DID_NOT_START"
    else:
        category="BOOT_UNCLASSIFIED"
    return ("BLOCKED","BOOT",category,None)

def diagnose():
    p14=module()
    p13=p14.pinned_module()
    p13.verify()
    schema=p13.load_schema()
    ip,cluster=schema.target()
    require(cluster not in schema.protected_four(),
            "fifth PG overlaps four originals")
    app_file=p14.app_secret(schema,cluster)
    runtime,mounts=schema.runtime()
    print("P1.4 GET DIAG FIFTH/APP SCRAM/FOUR ORIGINAL PG PASS",flush=True)
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="cafe-p14-http-fault-readonly-") as stage:
        source=schema.build_source(runtime,stage)
        for file,sha in ((ORIG_RUBY,ORIG_RUBY_BLOB),
                         (DIAG_RUBY,DIAG_RUBY_BLOB)):
            dest=source/"qa/security"/file.name
            require(not dest.exists() and not dest.is_symlink(),
                    "reviewed source probe path collision")
            with dest.open("xb") as f:
                f.write(file.read_bytes())
            require(schema.git("hash-object",str(dest))==sha,
                    "staged immutable Ruby proof hash differs")
        argv=command(p14,schema,source,mounts,ip,cluster,app_file)
        require(schema.target()==(ip,cluster),
                "fifth cluster changed before read-only Rack")
        try:
            process=subprocess.run(argv,stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,check=False,timeout=180)
        except (OSError,subprocess.TimeoutExpired):
            raise RuntimeError("P1.4 GET DIAG STOP: disposable read-only runner unavailable/timeout")
        # No raw logs escaped. Preserve only classified tags in memory.
        result=output_classification(process.stdout,process.returncode,process.stderr)
    # Even if Ruby GET failed, independent full fifth/other four PG verification
    # must run before returning a classified owner-visible result.
    require(schema.target()==(ip,cluster),
            "fifth cluster changed after read-only Rack")
    p13.verify()
    state,phase,kind,status=result
    print("P1.4 GET DIAG STAGE="+phase,flush=True)
    print("P1.4 GET DIAG KIND="+kind,flush=True)
    if status is not None:
        print("P1.4 GET DIAG STATUS="+status,flush=True)
    print("P1.4 GET DIAG RESULT="+state+"; NO INTENDED DB WRITES",flush=True)

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--diagnose",required=True,action="store_true")
    args=a.parse_args()
    try:
        if args.diagnose:
            diagnose()
    except Exception as exc:
        msg=str(exc)
        if not msg.startswith("P1.4 GET DIAG STOP:"):
            msg="P1.4 GET DIAG STOP: internal no-write safety/runner gate failed"
        print(msg,file=sys.stderr,flush=True)
        print("Never rerun schema/fixture one-shots, delete markers, reboot fifth PG, or inspect raw secret logs.",
              file=sys.stderr,flush=True)
        raise SystemExit(1)

if __name__=="__main__":
    main()
