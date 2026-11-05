#!/usr/bin/env python3
"""P1.2 Cafe-only reboot inventory. READ ONLY. No Docker starts/creates/changes.

Inventory original 3001 + restored QA 3002, the three tmpfs-only historical
test PGs (#3 sandbox, #4 fourth E2E, #5 synthetic SCRAM), private networks,
preexisting test Rails candidates, P1.2 original SHA-pinned schema helper
and private verified QA archive. No source/branch change, secrets, SQL writes.
"""
import argparse
import hashlib
import hmac
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HOME=Path.home()
PRIVATE=HOME/".local/share/cafe_app"
QA_BACKUP=HOME/"Backups/cafe_app/private_runtime/qa_security_snapshot_20261104_sqwulocr"
SCHEMA_SCRIPT=PRIVATE/"cafe_p12_schema_loader_v2_20261105.py"
SCHEMA_BLOB="204070f6bdb5a4fb16ed1c04036ba42d84a593c8"
SCHEMA_MARKER=PRIVATE/"cafe_p12_fifth_schema_attempt_20261105.json"
QA_RESUME=PRIVATE/"cafe_qa_persistent_resume_v1_20261106.py"
QA_RESUME_BLOB="f87419e7119b0c360db70ebb3684c857424922f1"
QA_BOOT=PRIVATE/"cafe_qa_http_boot_v1_20261106.py"
QA_BOOT_BLOB="c6da12b502de6db902f57fe44ff0acc50414c009"

LIVE_PG="cafe-app-db"
QA_PG="cafe-upload-qa-pg-20261103"
TMPFS_TARGETS=(
 ("sandbox","cafe-upload-security-sandbox-pg-20261104","cafe-upload-security-sandbox-20261104"),
 ("fourth","cafe-upload-security-e2e-pg-20261105","cafe-upload-security-e2e-net-20261105"),
 ("fifth","cafe-upload-security-synthetic-pg-20261105","cafe-upload-security-synthetic-net-20261105"),
)
WEB_TARGETS=(
 ("sandbox-rails","cafe-upload-security-sandbox-rails-20261104"),
 ("sandbox-precache","cafe-upload-security-sandbox-precache-20261104"),
 ("headers","cafe-upload-security-headers-mountfix-20261104"),
 ("fourth-rails","cafe-upload-security-e2e-web-readonly-20261105"),
)

def require(x,reason):
    if not x: raise RuntimeError("CAFE P1.2 REBOOT INVENTORY STOP: "+reason)

def call(*args,timeout=20):
    try:
        return subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              timeout=timeout,check=False)
    except (OSError,subprocess.TimeoutExpired):
        raise RuntimeError("CAFE P1.2 REBOOT INVENTORY STOP: local Docker/SQL timeout")

def inspect(kind,name):
    cmd=["docker"]
    if kind=="container":
        cmd+=["inspect","--type","container",name]
    elif kind=="network":
        cmd+=["network","inspect",name]
    else:
        raise ValueError("unsupported Docker kind")
    r=call(*cmd)
    require(r.returncode==0,"expected Cafe-only Docker resource not found")
    response=json.loads(r.stdout)
    require(len(response)==1,"invalid Docker inspect result")
    return response[0]

def git_blob(path):
    require(path.is_file() and not path.is_symlink(),
            "SHA-verified owner helper missing or symlink")
    st=path.stat()
    require(st.st_uid==os.getuid() and not(st.st_mode & 0o022),
            "owner helper permissions changed")
    r=call("git","hash-object",str(path))
    require(r.returncode==0,"local Git hash unavailable")
    return r.stdout.decode().strip()

def http(path,port):
    conn=HTTPConnection("127.0.0.1",port,timeout=8)
    try:
        conn.request("GET",path)
        response=conn.getresponse()
        response.read(4096)
        return response.status
    except (OSError,TimeoutError):
        return 0
    finally:
        conn.close()

def sql_id(pg,dbname):
    r=call("docker","exec","--user","postgres",pg,"psql","-X","-At",
           "-v","ON_ERROR_STOP=1","-U","postgres","-d",dbname,
           "-c","SELECT system_identifier::text FROM pg_control_system();",
           timeout=20)
    require(r.returncode==0,"protected original/QA PG inspection unavailable")
    result=r.stdout.decode().strip()
    require(result.isdigit() and len(result)>12,"PG ID inspection malformed")
    return result

def qa_backup_audit():
    manifest=QA_BACKUP/"manifest.json"
    archive=QA_BACKUP/"qa_cafe.dump"
    require(QA_BACKUP.is_dir() and not QA_BACKUP.is_symlink(),
            "verified private QA backup missing")
    require(manifest.is_file() and archive.is_file() and
            not manifest.is_symlink() and not archive.is_symlink(),
            "QA backup files unavailable")
    meta=json.loads(manifest.read_text(encoding="utf-8"))
    record=meta.get("database") or {}
    expected=record.get("sha256","")
    require(meta.get("verified") is True and
            meta.get("qa_product_count")==20 and
            meta.get("deleted_test_product_21") is True and
            record.get("archive")=="qa_cafe.dump" and
            isinstance(expected,str) and re.fullmatch("[0-9a-f]{64}",expected),
            "private snapshot manifest invalid")
    digest=hashlib.sha256()
    with archive.open("rb") as src:
        for block in iter(lambda:src.read(131072),b""):
            digest.update(block)
    require(hmac.compare_digest(digest.hexdigest(),expected),
            "private snapshot SHA mismatch")
    print("P1.2 VERIFIED PRIVATE QA BACKUP SHA256 PASS")

def protected_pair():
    require(git_blob(QA_RESUME)==QA_RESUME_BLOB,
            "owner QA restore-resume helper differs")
    require(git_blob(QA_BOOT)==QA_BOOT_BLOB,
            "owner QA HTTP boot helper differs")
    live=inspect("container",LIVE_PG)
    qa=inspect("container",QA_PG)
    require(live["State"]["Status"]=="running" and
            qa["State"]["Status"]=="running",
            "original/QA PG not both running")
    require(live["Config"]["Image"]=="postgres:16" and
            qa["Config"]["Image"]=="postgres:16",
            "original/QA PG image changed")
    require(set(live["NetworkSettings"]["Networks"])=={"cafe-app-private"} and
            set(qa["NetworkSettings"]["Networks"])==
            {"cafe-upload-qa-net-20261103"},
            "original/QA PG network isolation changed")
    def persistent(pg):
        return [m for m in pg["Mounts"] if
                m["Destination"]=="/var/lib/postgresql/data" and
                m["Type"]=="volume" and m["RW"] is True]
    require(len(persistent(live))==1 and len(persistent(qa))==1 and
            persistent(live)[0]["Name"]!=persistent(qa)[0]["Name"],
            "protected QA/live PGDATA volumes not separated")
    require(http("/",3001)==200 and http("/menu",3002)==200,
            "Cafe 3001/3002 HTTP not 200")
    require(sql_id(LIVE_PG,"cafe")!=sql_id(QA_PG,"cafe"),
            "protected production and QA PostgreSQL IDs equal")
    print("P1.2 ORIGINAL 3001 + PERSISTENT QA 3002 / DISTINCT PG PASS")

def tmpfs_audit():
    status={}
    for label,name,network in TMPFS_TARGETS:
        pg=inspect("container",name)
        net=inspect("network",network)
        host=pg["HostConfig"]
        # Check every test PG unconditionally.
        require(pg["Name"].lstrip("/")==name and
                pg["Config"]["Image"]=="postgres:16" and
                pg["State"]["Status"] in ("exited","created","running") and
                set(pg["NetworkSettings"]["Networks"])=={network} and
                net["Internal"] is True and
                not host.get("PortBindings") and
                host["RestartPolicy"]["Name"]=="no",
                "unexpected test PG image/network/status/port")
        tmp=host.get("Tmpfs") or {}
        require("/var/lib/postgresql/data" in tmp and
                "/var/run/postgresql" in tmp,
                "test PostgreSQL unexpectedly uses persistent PGDATA")
        require(not any(m["Destination"]=="/var/lib/postgresql/data"
                        for m in pg.get("Mounts",[])),
                "test PGDATA has unexpected bind/volume")
        require(not any(m["Type"]=="volume" for m in pg.get("Mounts",[])),
                "test PG uses unexpected volume")
        if label=="fifth":
            require(host["ReadonlyRootfs"] is True and
                    len(pg.get("Mounts",[]))==1 and
                    pg["Mounts"][0]["Type"]=="bind" and
                    pg["Mounts"][0]["RW"] is False and
                    pg["Mounts"][0]["Destination"]==
                    "/run/secrets/cafe_synthetic_postgres",
                    "fifth SCRAM credential isolation changed")
        else:
            require(not pg.get("Mounts"),
                    "private sandbox/fourth PG has unexpected mounts")
        members={entry["Name"] for entry in
                 (net.get("Containers") or {}).values()}
        require(LIVE_PG not in members and QA_PG not in members,
                "protected live/QA PG connected to disposable test network")
        status[label]=pg["State"]["Status"]
        print("P1.2 TEST PG "+label.upper()+": "+status[label].upper()+
              " / TMPFS PGDATA / INTERNAL NETWORK")
    return status

def web_audit():
    for label,name in WEB_TARGETS:
        web=inspect("container",name)
        require(web["State"]["Status"] in ("created","exited","running") and
                web["Config"]["Image"]=="cafe-legacy-full:node14" and
                not web["HostConfig"].get("PortBindings") and
                all(x not in web["NetworkSettings"]["Networks"]
                    for x in ("cafe-app-private","cafe-upload-qa-net-20261103")),
                "protected QA candidate isolation/status unexpectedly changed")
        print("P1.2 SOURCE WEB "+label.upper()+": "+
              web["State"]["Status"].upper()+
              " / NO HOST PORT")

def check():
    require(os.getuid()==1000,"expected owner Linux UID 1000")
    require(not SCHEMA_MARKER.exists() and not SCHEMA_MARKER.is_symlink(),
            "P1.2 schema marker already exists; do not resume writes")
    require(git_blob(SCHEMA_SCRIPT)==SCHEMA_BLOB,
            "original P1.2 reviewed schema helper not pinned")
    qa_backup_audit()
    protected_pair()
    status=tmpfs_audit()
    web_audit()
    if all(status[x]=="exited" for x in ("sandbox","fourth","fifth")):
        print("P1.2 THREE TEST PG STOPPED AFTER REBOOT — FRESH INIT REQUIRED")
    else:
        print("P1.2 TEST PG STATES VARY — REVIEW BEFORE ANY REBOOT RECOVERY")
    print("P1.2 POST-REBOOT INVENTORY PASS — NO DOCKER / SQL / FILE WRITES")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true",required=True)
    parser.parse_args()
    try: check()
    except Exception as exc:
        message=str(exc)
        if not message.startswith("CAFE P1.2 REBOOT INVENTORY STOP:"):
            message="CAFE P1.2 REBOOT INVENTORY STOP: internal safety audit failed"
        print(message,file=sys.stderr,flush=True)
        print("Preserve all existing volumes, markers, test containers and media.",
              file=sys.stderr,flush=True)
        sys.exit(1)

if __name__=="__main__":
    main()
