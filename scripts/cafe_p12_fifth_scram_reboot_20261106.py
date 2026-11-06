#!/usr/bin/env python3
"""Cafe P1.2 — one-shot start of the EXISTING fifth SCRAM-only PostgreSQL.

--check:         READ ONLY. Protected original four PG + read-only E2E,
                 owner SHA-pinned full fourth-Rails reboot verify, original
                 fifth private credential, stopped exact fifth Docker object.
--start-empty:   ONE SHOT. Exclusive private attempt marker BEFORE the sole
                 Docker start of the pre-existing fifth PG container; allow
                 Postgres16 SCRAM init on its already configured tmpfs PGDATA.
                 Verify PostgreSQL TCP ready, distinct cluster, zero tables,
                 zero non-postgres login roles and original protected state.
--verify-empty:  READ ONLY after boot, until scoped roles provisioning starts.

No Docker creation/removal/volume/network change, git checkout, production
SQL, QA snapshot import, new roles or Rails schema/seed/migration is permitted.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

PRIVATE=Path.home()/".local/share/cafe_app"
OLD=PRIVATE/"cafe_synthetic_pg_scram_v1_20261105.py"
OLD_BLOB="153ffca0535e0c42921d18ea39943bb4a92795fd"
BOOT=PRIVATE/"cafe_p12_private_test_rails_boot_v2_20261106.py"
BOOT_BLOB="c6e037a97218b084560ccdba183dab4ad0aee1b4"
MARKER=PRIVATE/"cafe_p12_fifth_reboot_empty_once_20261106.json"
SCHEMA_MARKER=PRIVATE/"cafe_p12_fifth_schema_attempt_20261105.json"
PG="cafe-upload-security-synthetic-pg-20261105"
NETWORK="cafe-upload-security-synthetic-net-20261105"
DB="cafe_synthetic"

def require(condition,message):
    if not condition:
        raise RuntimeError("P1.2 FIFTH SCRAM REBOOT STOP: "+message)

def blob(path):
    content=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(content)).encode()+b"\0"+content).hexdigest()

def owner_module(path,sha,name):
    require(os.getuid()==1000,"owner UID must be 1000")
    require(path.is_file() and not path.is_symlink(),
            name+" original helper unavailable")
    st=path.stat()
    require(st.st_uid==os.getuid() and not(st.st_mode&0o022),
            name+" unexpected host permissions")
    require(blob(path)==sha,name+" original reviewed Git blob mismatch")
    spec=importlib.util.spec_from_file_location(name,path)
    require(spec is not None and spec.loader is not None,
            name+" module loader not available")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def run(argv,timeout=30):
    try:
        return subprocess.run(argv,stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,timeout=timeout,
                              check=False)
    except (OSError,subprocess.TimeoutExpired):
        raise RuntimeError("P1.2 FIFTH SCRAM REBOOT STOP: Docker command failed or timed out")

def no_schema_marker():
    require(not SCHEMA_MARKER.exists() and not SCHEMA_MARKER.is_symlink(),
            "prior fifth schema attempt marker exists; preserve it")

def preflight():
    require(not MARKER.exists() and not MARKER.is_symlink(),
            "fifth restart attempt already marked; do not retry")
    no_schema_marker()
    boot=owner_module(BOOT,BOOT_BLOB,"p12_reviewed_four_rails_boot")
    boot.verify()  # validates original 3001/3002 + PG3/PG4 + all 4 private Rails
    old=owner_module(OLD,OLD_BLOB,"p12_reviewed_original_fifth_pg")
    old.source_baseline()
    old.secret_audit()  # old owner-only credential, never printed/exported
    old.check_new("exited")  # strict SCRAM, PGDATA tmpfs, internal net, no port
    require(old.PG==PG and old.NETWORK==NETWORK and old.PGDB==DB,
            "original fifth protected identity differs")
    print("P1.2 FOUR PROTECTED PG / PRIVATE RAILS READONLY E2E PASS",flush=True)
    print("P1.2 FIFTH EXISTING STOPPED TMPFS POSTGRES16 / SCRAM CONFIG PASS",flush=True)
    print("P1.2 FIFTH PRIVATE CREDENTIAL / NO PREVIOUS DDL MARKER PASS",flush=True)
    print("P1.2 FIFTH SCRAM REBOOT CHECK PASS — NO WRITES",flush=True)
    return old

def postflight():
    require(MARKER.is_file() and not MARKER.is_symlink(),
            "fifth restart one-shot marker missing")
    stat=MARKER.stat()
    require(stat.st_uid==os.getuid() and stat.st_mode&0o077==0 and
            stat.st_size<2048,
            "fifth marker permissions or size changed")
    record=json.loads(MARKER.read_text(encoding="utf-8"))
    require(record.get("operation")=="reboot_existing_fifth_empty_scram_once" and
            record.get("pg")==PG and record.get("network")==NETWORK and
            record.get("source_blob")==OLD_BLOB,
            "fifth restart marker identity changed")
    no_schema_marker()
    old=owner_module(OLD,OLD_BLOB,"p12_reviewed_original_fifth_pg")
    old.secret_audit()
    old.source_baseline()
    old.check_new("running")
    old.verify_running()  # 5 distinct PG IDs, SCRAM-only HBA, zero login roles/tables
    print("P1.2 FIFTH POSTGRES16 EMPTY SCRAM / FIVE DISTINCT PG PASS",flush=True)
    print("P1.2 FIFTH ZERO TABLES / ZERO EXTRA LOGIN ROLES / NO DDL PASS",flush=True)
    print("P1.2 FIFTH REBOOT INDEPENDENT POSTFLIGHT PASS",flush=True)

def wait_final_tcp():
    # The official postgres image starts a temporary init server listening
    # on Unix sockets only. TCP ready here means final SCRAM server is active.
    for _ in range(60):
        r=run(["docker","exec","--user","postgres",PG,
               "pg_isready","-h","127.0.0.1","-p","5432",
               "-U","postgres","-d",DB],timeout=9)
        if r.returncode==0:
            q=run(["docker","exec","--user","postgres",PG,
                   "psql","-X","-At","-v","ON_ERROR_STOP=1",
                   "-U","postgres","-d",DB,"-c",
                   "SELECT current_database();"],timeout=15)
            if q.returncode==0 and q.stdout.decode(errors="replace").strip()==DB:
                return
        time.sleep(1)
    raise RuntimeError("P1.2 FIFTH SCRAM REBOOT STOP: final PostgreSQL TCP/SQL not ready")

def start_empty():
    old=preflight()
    os.umask(0o077)
    flags=os.O_CREAT|os.O_EXCL|os.O_WRONLY
    if hasattr(os,"O_NOFOLLOW"):flags|=os.O_NOFOLLOW
    fd=os.open(str(MARKER),flags,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as out:
        json.dump({"operation":"reboot_existing_fifth_empty_scram_once",
                   "pg":PG,"network":NETWORK,"source_blob":OLD_BLOB,
                   "unix":int(time.time())},out,sort_keys=True)
        out.write("\n")
    print("P1.2 FIFTH EMPTY SCRAM ONE-SHOT MARKER RECORDED",flush=True)
    r=run(["docker","start",PG],timeout=50)
    require(r.returncode==0,
            "fifth original container could not start; preserve marker")
    print("P1.2 EXISTING FIFTH PG CONTAINER STARTED",flush=True)
    wait_final_tcp()
    print("P1.2 FIFTH SCRAM FINAL TCP POSTGRES READY",flush=True)
    postflight()
    print("P1.2 FIFTH EMPTY SCRAM REBOOT COMPLETE — NO ROLE/SCHEMA WRITES",flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check",action="store_true")
    mode.add_argument("--start-empty",action="store_true")
    mode.add_argument("--verify-empty",action="store_true")
    args=p.parse_args()
    try:
        if args.check:preflight()
        elif args.start_empty:start_empty()
        else:postflight()
    except Exception as e:
        message=str(e)
        if not message.startswith("P1.2 FIFTH SCRAM REBOOT STOP:"):
            message="P1.2 FIFTH SCRAM REBOOT STOP: internal safety/compatibility audit failure"
        print(message,file=sys.stderr,flush=True)
        print("Preserve fifth container, credential and one-shot marker; "
              "never blindly retry or run old --bootstrap.",file=sys.stderr,flush=True)
        raise SystemExit(1)

if __name__=="__main__":main()
