#!/usr/bin/env python3
"""Recover ONLY the proven empty, already-running QA PostgreSQL after a one-shot
restore was interrupted BEFORE pg_restore by transient SQL readiness failure.

--check-resume : READ ONLY: pinned previous script, original restore marker,
  backup SHA, protected production, QA network/volume, distinct EMPTY QA DB.
--resume-empty : independently authorized ONCE: fresh scoped preflight, new
  exclusive marker BEFORE any pg_restore writes, exact prior QA dump import.
--verify       : READ ONLY: independently verify completed QA snapshot.

NEVER retry original --restore or this --resume-empty after an ambiguous failure.
Never delete/recreate Docker objects, alter other databases or restart Rails.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

BASE=Path.home()/".local/share/cafe_app"
ORIGINAL=BASE/"cafe_qa_persistent_recovery_v1_20261106.py"
ORIGINAL_BLOB="37ba432479f4243a725d682fa88faabf8477efb1"
RESUME_MARKER=BASE/"cafe_qa_persistent_restore_resume_once_20261106.json"

def require(condition,message):
    if not condition:
        raise RuntimeError("CAFE QA RESUME STOP: "+message)

def sha1_git_blob(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()

def load_original():
    require(ORIGINAL.is_file() and not ORIGINAL.is_symlink(),
            "original SHA-pinned owner script missing")
    st=ORIGINAL.stat()
    require(st.st_uid==os.getuid() and not(st.st_mode&0o022),
            "original script ownership/mode differs")
    require(sha1_git_blob(ORIGINAL)==ORIGINAL_BLOB,
            "original owner helper Git blob not SHA-verified")
    spec=importlib.util.spec_from_file_location("cafe_qa_persistent_v1",ORIGINAL)
    require(spec is not None and spec.loader is not None,"cannot load owner helper")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def validate_marker(module):
    marker=module.MARKER
    require(marker.is_file() and not marker.is_symlink(),
            "original one-shot restore marker missing")
    st=marker.stat()
    require(st.st_uid==os.getuid() and
            st.st_mode&0o077==0 and st.st_size<=1024,
            "original restore marker owner/mode/size differs")
    value=json.loads(marker.read_text(encoding="utf-8"))
    expected=json.loads(module.MANIFEST.read_text(encoding="utf-8"))["database"]["sha256"]
    require(value.get("operation")=="restore_private_qa_archive_once" and
            value.get("target")==module.PG and
            value.get("volume")==module.VOLUME and
            value.get("backup_sha256")==expected and
            type(value.get("started_unix")) is int and
            value["started_unix"]>0,
            "original partial restore marker inconsistent")
    return expected

def empty_db_audit(module):
    # This inspects the exact isolated QA cluster WITHOUT touching it.
    liveid=module.sql(module.LIVE_PG,
                      "SELECT system_identifier::text FROM pg_control_system();")
    qaid=module.sql(module.PG,
                    "SELECT system_identifier::text FROM pg_control_system();")
    require(liveid.isdigit() and qaid.isdigit() and qaid!=liveid,
            "QA PostgreSQL cluster not independent from protected production")
    require(module.sql(module.PG,
        "SELECT current_database();")==module.DB,
        "QA database not initialized")
    # A failed early init can leave an empty public schema. Reject ANY
    # preexisting user-schema objects, not merely missing products.
    queries=(
        "SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace;",
        "SELECT count(*) FROM pg_proc WHERE pronamespace='public'::regnamespace;",
        "SELECT count(*) FROM pg_type WHERE typnamespace='public'::regnamespace;",
        "SELECT count(*) FROM pg_extension WHERE extnamespace='public'::regnamespace;",
        "SELECT count(*) FROM pg_namespace "
        "WHERE nspname NOT IN ('public','information_schema') "
        "AND nspname NOT LIKE 'pg_%';",
        "SELECT count(*) FROM pg_tables WHERE schemaname='public';",
        "SELECT count(*) FROM pg_roles "
        "WHERE rolcanlogin AND rolname <> 'postgres';",
    )
    for statement in queries:
        require(module.sql(module.PG,statement)=="0",
                "QA DB not strictly empty or contains unexpected roles; stop")

def audit(allow_existing_resume_marker=False):
    require(os.getuid()==1000,"expected original QA operator UID1000")
    original=load_original()
    original.backup_audit()
    original.original_audit()
    original.qa_preflight()
    original.pg_audit("running")
    expected=validate_marker(original)
    if allow_existing_resume_marker:
        require(RESUME_MARKER.is_file() and not RESUME_MARKER.is_symlink(),
                "QA resume marker missing after restore")
    else:
        require(not RESUME_MARKER.exists() and not RESUME_MARKER.is_symlink(),
                "QA resume already attempted; do not run it again")
    empty_db_audit(original)
    print("QA PARTIAL ONE-SHOT MARKER / BACKUP SHA PASS",flush=True)
    print("QA NEW PERSISTENT PG / DEDICATED NETWORK / DISTINCT CLUSTER PASS",flush=True)
    print("QA STRICT EMPTY-SCHEMA AND LOGIN-ROLE CHECK PASS",flush=True)
    print("QA RESUME-EMPTY PREFLIGHT PASS — NO WRITES",flush=True)
    return original,expected

def resume_empty():
    original,expected=audit()
    # Reserve the ONE and ONLY follow-up attempt before DB writes. On failure
    # preserve this marker and all Docker/DB contents; no repeat permitted.
    os.umask(0o077)
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"): flags|=os.O_NOFOLLOW
    fd=os.open(str(RESUME_MARKER),flags,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as dest:
        json.dump({"operation":"resume_verified_empty_qa_pg_once",
                   "target":original.PG,"volume":original.VOLUME,
                   "backup_sha256":expected,"started_unix":int(time.time())},
                  dest,sort_keys=True)
        dest.write("\n")
    print("QA RESUME ONCE MARKER WRITTEN — BEGIN ONLY QA ARCHIVE IMPORT",flush=True)
    with original.ARCHIVE.open("rb") as source:
        try:
            process=subprocess.run(
                ["docker","exec","-i","--user","postgres",original.PG,
                 "pg_restore","--username=postgres","--dbname="+original.DB,
                 "--no-owner","--no-acl","--exit-on-error",
                 "--single-transaction"],
                stdin=source,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                check=False,timeout=240)
        except (OSError,subprocess.TimeoutExpired):
            raise RuntimeError(
                "CAFE QA RESUME STOP: pg_restore unavailable or timed out")
    require(process.returncode==0,
            "QA one-shot import failed; preserve marker and data, DO NOT RETRY")
    original.verify_running()
    print("QA VERIFIED BACKUP RESTORED TO PERSISTENT PG PASS",flush=True)
    print("QA ORIGINAL LIVE DB / HTTP 3001 UNCHANGED PASS",flush=True)
    print("QA RAILS / PROXY 3002 NOT STARTED",flush=True)

def verify():
    original=load_original()
    validate_marker(original)
    require(RESUME_MARKER.is_file() and not RESUME_MARKER.is_symlink(),
            "QA resume marker missing")
    record=json.loads(RESUME_MARKER.read_text(encoding="utf-8"))
    require(record.get("operation")=="resume_verified_empty_qa_pg_once" and
            record.get("target")==original.PG and
            record.get("volume")==original.VOLUME,
            "QA resume record inconsistent")
    original.verify_running()
    print("QA POST-RESUME INDEPENDENT VERIFY PASS",flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-resume",action="store_true")
    mode.add_argument("--resume-empty",action="store_true")
    mode.add_argument("--verify",action="store_true")
    args=parser.parse_args()
    try:
        if args.check_resume: audit()
        elif args.resume_empty: resume_empty()
        else: verify()
    except Exception as err:
        msg=str(err)
        if not msg.startswith("CAFE QA RESUME STOP:"):
            msg="CAFE QA RESUME STOP: internal safety/readiness audit failure"
        print(msg,file=sys.stderr,flush=True)
        print("Preserve previous marker, QA DB/volume and any new resume marker. "
              "Never blindly retry.",
              file=sys.stderr,flush=True)
        sys.exit(1)

if __name__=="__main__":
    main()
