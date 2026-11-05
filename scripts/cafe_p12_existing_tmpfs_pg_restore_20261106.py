#!/usr/bin/env python3
"""Cafe P1.2 recovery of TWO preexisting stopped, tmpfs-only private test PGs.

--check          READ ONLY: pin owner inventory, backup SHA, protected Cafe,
                 test PG3/PG4 exact existing stopped containers, no restore marker.
--restore-clones ONE SHOT: repeat --check; create exclusive local attempt marker
                 BEFORE starting only PG3/PG4; wait for real SQL ready; import
                 the existing SHA-verified private QA archive into each initially
                 empty disposable database in a single transaction; verify each.
--verify-clones  READ ONLY: both target clusters distinct, 20 products, 2 test
                 users, absent test product 21, and original 3001/3002 protected.

NEVER reset/remove/recreate containers, change network, edit original code/media,
export private dump, restart protected PG, or touch fifth synthetic PostgreSQL.
No retries after an ambiguous write failure. Does NOT start any Rails process.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HOME=Path.home()
PRIVATE=HOME/".local/share/cafe_app"
OWNER_INVENTORY=PRIVATE/"cafe_p12_reboot_inventory_v1_20261106.py"
INVENTORY_BLOB="af125038530314febacd35a59d5d213a85f8f742"
MARKER=PRIVATE/"cafe_p12_temp_two_pg_restore_once_20261106.json"
PGS=(
 ("sandbox","cafe-upload-security-sandbox-pg-20261104",
  "cafe-upload-security-sandbox-20261104","cafe"),
 ("fourth","cafe-upload-security-e2e-pg-20261105",
  "cafe-upload-security-e2e-net-20261105","cafe"),
)
PROTECTED=("cafe-app-db","cafe-upload-qa-pg-20261103")
FIFTH="cafe-upload-security-synthetic-pg-20261105"
DEFAULT_PG_USERS="POSTGRES_HOST_AUTH_METHOD=trust"

def require(ok,why):
    if not ok:
        raise RuntimeError("CAFE P1.2 TEST DB RECOVERY STOP: "+why)

def run(argv,*,timeout=30,stdin=None):
    try:
        return subprocess.run(argv,stdin=stdin,stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,timeout=timeout,check=False)
    except (OSError,subprocess.TimeoutExpired):
        raise RuntimeError("CAFE P1.2 TEST DB RECOVERY STOP: local command unavailable/timeout")

def git_blob(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()

def inventory():
    require(os.getuid()==1000,"expected original operator UID 1000")
    require(OWNER_INVENTORY.is_file() and not OWNER_INVENTORY.is_symlink(),
            "pinned owner inventory missing")
    st=OWNER_INVENTORY.stat()
    require(st.st_uid==os.getuid() and st.st_mode&0o022==0,
            "owner inventory permissions/owner changed")
    require(git_blob(OWNER_INVENTORY)==INVENTORY_BLOB,
            "original owner inventory Git blob differs")
    spec=importlib.util.spec_from_file_location("cafe_verified_reboot_inventory",OWNER_INVENTORY)
    require(spec is not None and spec.loader is not None,"inventory import unavailable")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def inspect_source(inv,label,name,network,state):
    pg=inv.inspect("container",name)
    host=pg["HostConfig"]
    require(pg["Name"].lstrip("/")==name and
            pg["State"]["Status"]==state and
            pg["Config"]["Image"]=="postgres:16" and
            set(pg["NetworkSettings"]["Networks"])=={network} and
            host["RestartPolicy"]["Name"]=="no" and
            not host.get("PortBindings") and
            not host.get("Binds") and
            "POSTGRES_DB=cafe" in pg["Config"]["Env"] and
            DEFAULT_PG_USERS in pg["Config"]["Env"] and
            "/var/lib/postgresql/data" in (host.get("Tmpfs") or {}) and
            "/var/run/postgresql" in (host.get("Tmpfs") or {}) and
            not pg.get("Mounts"),
            label+" existing disposable PostgreSQL config changed")
    net=inv.inspect("network",network)
    require(net["Internal"] is True,
            label+" network not internal-only")
    members={x.get("Name") for x in
             (net.get("Containers") or {}).values()}
    allowed={
      "sandbox":{"cafe-upload-security-sandbox-pg-20261104",
                 "cafe-upload-security-sandbox-rails-20261104",
                 "cafe-upload-security-sandbox-precache-20261104",
                 "cafe-upload-security-headers-mountfix-20261104"},
      "fourth":{"cafe-upload-security-e2e-pg-20261105",
                "cafe-upload-security-e2e-web-readonly-20261105"},
    }[label]
    require(members.issubset(allowed) and
            not any(x in members for x in PROTECTED),
            label+" network includes unexpected active member")
    return pg

def require_backup(inv):
    inv.qa_backup_audit()
    return inv.QA_BACKUP/"qa_cafe.dump"

def scoped_qa(inv):
    inv.protected_pair()
    require(inv.inspect("container",FIFTH)["State"]["Status"]=="exited",
            "synthetic fifth state changed; inspect independently")
    require(not inv.SCHEMA_MARKER.exists() and
            not inv.SCHEMA_MARKER.is_symlink(),
            "fifth schema marker exists; do not proceed")
    for label,name,net,_db in PGS:
        inspect_source(inv,label,name,net,"exited")

def original_source_check(inv):
    require_backup(inv)
    scoped_qa(inv)
    require(not MARKER.exists() and not MARKER.is_symlink(),
            "private test PG restore already attempted: no retry")
    print("P1.2 PRIVATE QA ARCHIVE SHA256 / ORIGINAL 3001-3002 PASS",flush=True)
    print("P1.2 TWO EXISTING TEST PG CONTAINERS STOPPED / TMPFS ONLY PASS",flush=True)
    print("P1.2 RECREATE/DROP/RESTART/FIFTH WRITES NOT ALLOWED",flush=True)
    print("P1.2 TEST PG RECOVERY CHECK PASS — NO WRITES",flush=True)
    return inv

def query(name,db,statement):
    require(statement.lstrip().upper().startswith(("SELECT ","SHOW ")),
            "read-only PostgreSQL inspection only")
    result=run(["docker","exec","--user","postgres",name,
                "psql","-X","-At","-v","ON_ERROR_STOP=1",
                "-U","postgres","-d",db,"-c",statement],timeout=24)
    require(result.returncode==0,"PostgreSQL read-only SQL check failed")
    value=result.stdout.decode(errors="replace").strip()
    require(len(value)<1000 and "\n" not in value,
            "PostgreSQL read-only response invalid")
    return value

def ready(name,dbname):
    # pg_isready alone can be true during temporary official-image init.
    # Require successful SQL on the exact expected database twice.
    for attempt in range(65):
        first=run(["docker","exec","--user","postgres",name,"psql",
                   "-X","-At","-v","ON_ERROR_STOP=1","-U","postgres",
                   "-d",dbname,"-c","SELECT current_database();"],timeout=9)
        if first.returncode==0 and first.stdout.decode().strip()==dbname:
            time.sleep(1)
            second=run(["docker","exec","--user","postgres",name,"psql",
                        "-X","-At","-v","ON_ERROR_STOP=1","-U","postgres",
                        "-d",dbname,"-c","SELECT current_database();"],timeout=9)
            if second.returncode==0 and second.stdout.decode().strip()==dbname:
                return
        time.sleep(1)
    raise RuntimeError("CAFE P1.2 TEST DB RECOVERY STOP: new test PG SQL never became stable")

def unique_ids(inv,active):
    protected=[inv.sql_id(PROTECTED[0],"cafe"),
               inv.sql_id(PROTECTED[1],"cafe")]
    ids=list(protected)
    for _label,name,db in active:
        ids.append(query(name,db,
                         "SELECT system_identifier::text FROM pg_control_system();"))
    require(all(x.isdigit() and len(x)>12 for x in ids) and
            len(set(ids))==len(ids),
            "test PG cluster ID duplicated protected/original cluster")
    return ids

def empty(inv,label,name,network,db,active):
    inspect_source(inv,label,name,network,"running")
    ready(name,db)
    unique_ids(inv,active+[(label,name,db)])
    checks=(
      "SELECT count(*) FROM pg_tables WHERE schemaname='public';",
      "SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace;",
      "SELECT count(*) FROM pg_proc WHERE pronamespace='public'::regnamespace;",
      "SELECT count(*) FROM pg_extension WHERE extnamespace='public'::regnamespace;",
      "SELECT count(*) FROM pg_namespace WHERE nspname NOT IN ('public','information_schema') AND nspname NOT LIKE 'pg_%';",
      "SELECT count(*) FROM pg_roles WHERE rolcanlogin AND rolname <> 'postgres';",
    )
    for statement in checks:
        require(query(name,db,statement)=="0",
                label+" PG not empty after reinitialization; never import")

def verify_tables(name,dbname):
    require(query(name,dbname,
                  "SELECT count(*) FROM public.products;")=="20",
            "restored test product count differs")
    require(query(name,dbname,
                  "SELECT count(*) FROM public.products WHERE id=21;")=="0",
            "test product ID21 unexpectedly present")
    require(query(name,dbname,
                  "SELECT count(*) FROM public.users;")=="2",
            "historical private QA users count differs")
    count=query(name,dbname,
                "SELECT count(*) FROM pg_tables WHERE schemaname='public';")
    require(count.isdigit() and int(count)>=10,
            "test PostgreSQL restored public table count incomplete")

def confirm_restored():
    require(MARKER.is_file() and not MARKER.is_symlink(),
            "test database recovery marker missing")
    st=MARKER.stat()
    require(st.st_uid==os.getuid() and st.st_mode&0o077==0 and
            st.st_size<2048,
            "test database recovery marker security differs")
    value=json.loads(MARKER.read_text(encoding="utf-8"))
    require(value.get("operation")=="restore_existing_two_disposable_pg_once" and
            value.get("targets")==[p[1] for p in PGS] and
            value.get("archive_sha256")==json.loads(
                (inventory().QA_BACKUP/"manifest.json").read_text()
            )["database"]["sha256"],
            "test DB restore marker differs")

def verify():
    inv=inventory()
    confirm_restored()
    require_backup(inv)
    inv.protected_pair()
    require(not inv.SCHEMA_MARKER.exists() and
            not inv.SCHEMA_MARKER.is_symlink(),
            "fifth P1.2 schema attempt unexpectedly exists")
    active=[]
    for label,name,network,db in PGS:
        inspect_source(inv,label,name,network,"running")
        verify_tables(name,db)
        active.append((label,name,db))
    unique_ids(inv,active)
    print("P1.2 SANDBOX/FOURTH VERIFIED 20 PRODUCTS / 2 PRIVATE QA USERS PASS",flush=True)
    print("P1.2 TWO TEMP CLUSTERS DISTINCT FROM PERSISTENT 3001/3002 PASS",flush=True)
    print("P1.2 TEMP TEST PG RECOVERY VERIFIED — NO SCHEMA WRITES TO FIFTH",flush=True)

def restore():
    inv=original_source_check(inventory())
    archive=inv.QA_BACKUP/"qa_cafe.dump"
    os.umask(0o077)
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"): flags|=os.O_NOFOLLOW
    fd=os.open(str(MARKER),flags,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as dst:
        json.dump({"operation":"restore_existing_two_disposable_pg_once",
                   "targets":[p[1] for p in PGS],
                   "archive_sha256":json.loads(
                      (inv.QA_BACKUP/"manifest.json").read_text()
                   )["database"]["sha256"],
                   "started_unix":int(time.time())},
                  dst,sort_keys=True)
        dst.write("\n")
    print("P1.2 TWO-TEST-PG ONE-SHOT RESTORE MARKER WRITTEN",flush=True)
    completed=[]
    for label,name,network,db in PGS:
        # No Docker run/creation, volume change, network mutation or production start.
        ret=run(["docker","start",name],timeout=50)
        require(ret.returncode==0,
                label+" existing PostgreSQL failed to start; preserve marker")
        empty(inv,label,name,network,db,completed)
        with archive.open("rb") as source:
            result=run(["docker","exec","-i","--user","postgres",name,
                        "pg_restore","--username=postgres",
                        "--dbname="+db,"--no-owner","--no-acl",
                        "--exit-on-error","--single-transaction"],
                       timeout=240,stdin=source)
        require(result.returncode==0,
                label+" pg_restore failed; preserve marker; never retry")
        verify_tables(name,db)
        completed.append((label,name,db))
        unique_ids(inv,completed)
        inv.protected_pair()
        print("P1.2 "+label.upper()+" PRIVATE TEST PG RESTORE PASS",flush=True)
    verify()
    print("P1.2 TWO DISPOSABLE PG RESTORED; FIFTH STILL STOPPED",flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check",action="store_true")
    group.add_argument("--restore-clones",action="store_true")
    group.add_argument("--verify-clones",action="store_true")
    args=parser.parse_args()
    try:
        if args.check: original_source_check(inventory())
        elif args.restore_clones: restore()
        else: verify()
    except Exception as exc:
        message=str(exc)
        if not message.startswith("CAFE P1.2 TEST DB RECOVERY STOP:"):
            message="CAFE P1.2 TEST DB RECOVERY STOP: internal safety/compatibility audit failure"
        print(message,file=sys.stderr,flush=True)
        print("Preserve prior test Docker objects, original QA dump and marker; "
              "do not blindly retry restore.",file=sys.stderr,flush=True)
        sys.exit(1)

if __name__=="__main__":
    main()
