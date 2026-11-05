#!/usr/bin/env python3
"""Recover MISSING isolated Cafe QA PostgreSQL from verified owner backup.

--check           READ ONLY: exact production/QA isolation, backup SHA, free names.
--create          Creates ONLY new persistent QA volume + missing QA PG container.
--verify-created  READ ONLY: scrutinize stopped QA PG Docker configuration.
--restore         ONE SHOT: start NEW QA PG and pg_restore private QA archive.
--verify-running  READ ONLY: verify QA catalogue/users and production separation.

No original containers, images, production volumes, source files, backups,
user accounts, or published ports are modified. No deletion or retry on failure.
Never invoke Docker Compose or attach QA PG to a production network.
"""
import argparse
import hashlib
import hmac
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

HOME=Path.home()
BACKUP=HOME/"Backups/cafe_app/private_runtime/qa_security_snapshot_20261104_sqwulocr"
MANIFEST=BACKUP/"manifest.json"
ARCHIVE=BACKUP/"qa_cafe.dump"
PRIVATE=HOME/".local/share/cafe_app"
MARKER=PRIVATE/"cafe_qa_persistent_restore_once_20261106.json"
VOLUME="cafe-qa-pgdata-persistent-20261106"
PG="cafe-upload-qa-pg-20261103"
QA_NET="cafe-upload-qa-net-20261103"
QA_ALIAS="cafe-app-db"
QA_WEB="cafe-app-patched-qa-candidate-20261104"
QA_PROXY="cafe-upload-qa-proxy-patched-20261104"
LIVE_PG="cafe-app-db"
LIVE_WEB="cafe-app-local-3001-web"
LIVE_NET="cafe-app-private"
IMAGE="postgres:16"
DB="cafe"

def need(test,message):
    if not test: raise RuntimeError("CAFE QA RECOVERY STOP: "+message)

def run(args,timeout=30,stdin=None):
    try:
        return subprocess.run(args,stdin=stdin,stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,timeout=timeout,check=False)
    except (OSError,subprocess.TimeoutExpired):
        raise RuntimeError("CAFE QA RECOVERY STOP: Docker command unavailable/timeout")

def docker(*args):
    return run(["docker",*args])

def inspect(kind,name):
    cmd=(["docker","network","inspect",name] if kind=="network"
         else ["docker","volume","inspect",name] if kind=="volume"
         else ["docker","inspect","--type=container",name])
    r=run(cmd)
    need(r.returncode==0,"required Docker resource unavailable")
    value=json.loads(r.stdout)
    need(isinstance(value,list) and len(value)==1,"unexpected Docker inspect response")
    return value[0]

def exists(kind,name):
    cmd=(["docker","network","inspect",name] if kind=="network"
         else ["docker","volume","inspect",name] if kind=="volume"
         else ["docker","container","inspect",name])
    return run(cmd).returncode==0

def sql(name,statement):
    need(statement.lstrip().upper().startswith(("SELECT ","SHOW ")),
         "mutating SQL inspection forbidden")
    r=docker("exec","--user","postgres",name,"psql","-X","-At",
             "-v","ON_ERROR_STOP=1","-U","postgres","-d",DB,"-c",statement)
    need(r.returncode==0,"read-only SQL inspection failed")
    result=r.stdout.decode(errors="replace").strip()
    need(len(result)<5000,"unexpected SQL inspection length")
    return result

def http_root():
    client=HTTPConnection("127.0.0.1",3001,timeout=10)
    try:
        client.request("GET","/")
        response=client.getresponse()
        response.read(4096)
        return response.status
    except (OSError,TimeoutError):
        return 0
    finally:
        client.close()

def backup_audit():
    need(BACKUP.is_dir() and not BACKUP.is_symlink(),"backup directory invalid")
    for name in (MANIFEST,ARCHIVE):
        need(name.is_file() and not name.is_symlink(),"backup file invalid")
    meta=json.loads(MANIFEST.read_text(encoding="utf-8"))
    record=meta.get("database") or {}
    need(meta.get("verified") is True and
         meta.get("qa_product_count")==20 and
         meta.get("deleted_test_product_21") is True,
         "verified QA catalogue manifest differs")
    need(record.get("archive")=="qa_cafe.dump","backup archive identity differs")
    expected=record.get("sha256","")
    need(isinstance(expected,str) and
         re.fullmatch(r"[0-9a-f]{64}",expected) is not None,
         "backup SHA metadata invalid")
    need(0<ARCHIVE.stat().st_size<=268435456,"backup dump size invalid")
    digest=hashlib.sha256()
    with ARCHIVE.open("rb") as source:
        for block in iter(lambda:source.read(131072),b""):
            digest.update(block)
    need(hmac.compare_digest(digest.hexdigest(),expected),
         "backup SHA256 mismatch")
    print("QA VERIFIED PRIVATE SNAPSHOT SHA256 PASS",flush=True)

def original_audit():
    prod=inspect("container",LIVE_PG)
    need(prod["Name"].lstrip("/")==LIVE_PG and
         prod["Config"]["Image"]=="postgres:16" and
         prod["State"]["Status"]=="running" and
         set(prod["NetworkSettings"]["Networks"])=={LIVE_NET},
         "protected original PostgreSQL identity/network changed")
    pdata=[m for m in prod["Mounts"] if
           m["Destination"]=="/var/lib/postgresql/data"]
    need(len(pdata)==1 and pdata[0]["Type"]=="volume" and
         pdata[0]["RW"] is True,
         "protected PostgreSQL persistent data volume changed")
    web=inspect("container",LIVE_WEB)
    need(web["State"]["Status"]=="running","original cafe web stopped")
    need(set(web["NetworkSettings"]["Networks"]).isdisjoint({QA_NET}),
         "original Rails attached to QA network")
    bind=web["HostConfig"].get("PortBindings") or {}
    need(any(item.get("HostIp")=="127.0.0.1" and
             item.get("HostPort")=="3001"
             for items in bind.values() for item in items),
         "original cafe 3001 localhost port unavailable")
    need(http_root()==200,"original cafe homepage HTTP not 200")
    baseline=sql(LIVE_PG,"SELECT system_identifier::text FROM pg_control_system();")
    need(baseline.isdigit(),"original PG system identifier unavailable")
    return baseline

def qa_preflight():
    network=inspect("network",QA_NET)
    need(network["Name"]==QA_NET and network["Internal"] is True,
         "QA network not internal-only")
    members={entry.get("Name") for entry in
             (network.get("Containers") or {}).values()}
    need(members.issubset({PG,QA_WEB,QA_PROXY,
                         "cafe-app-uploads-qa-avatar-20261103",
                         "cafe-app-uploads-qa-db-20261103",
                         "cafe-app-uploads-qa-20261103"}),
         "unrecognized QA network members")
    need(LIVE_PG not in members and LIVE_WEB not in members,
         "live production attached to QA network")
    web=inspect("container",QA_WEB)
    need(web["Config"]["Image"]=="cafe-legacy-full:node14" and
         set(web["NetworkSettings"]["Networks"])=={QA_NET} and
         not web["HostConfig"].get("PortBindings"),
         "QA patched web identity/network/ports differs")
    env=dict(item.split("=",1) for item in web["Config"]["Env"])
    need(env.get("DATABASE_URL")==
         "postgresql://postgres@cafe-app-db:5432/cafe",
         "existing QA Rails DATABASE_URL changed; restore blocked")
    proxy=inspect("container",QA_PROXY)
    need(QA_NET in proxy["NetworkSettings"]["Networks"] and
         not any(n==LIVE_NET for n in proxy["NetworkSettings"]["Networks"]),
         "QA proxy networks changed")
    binding=(proxy["HostConfig"].get("PortBindings") or {}).get("3002/tcp",[])
    need(len(binding)==1 and binding[0].get("HostIp")=="127.0.0.1" and
         binding[0].get("HostPort")=="3002",
         "QA proxy localhost 3002 mapping differs")

def volume_audit():
    volume=inspect("volume",VOLUME)
    need(volume["Name"]==VOLUME and volume["Driver"]=="local",
         "QA persistent volume driver/name differs")
    label=volume.get("Labels") or {}
    need(label.get("cafe.scope")=="qa-only" and
         label.get("cafe.created")=="2026-11-06",
         "QA persistent volume labels differ")

def pg_audit(expected_status):
    volume_audit()
    pg=inspect("container",PG)
    need(pg["Name"].lstrip("/")==PG and
         pg["Config"]["Image"]==IMAGE and
         pg["State"]["Status"]==expected_status,
         "QA PG name/image/status differs")
    host=pg["HostConfig"]
    need(host["ReadonlyRootfs"] is True and
         host["RestartPolicy"]["Name"]=="no" and
         host["Memory"]==768*1024*1024 and
         host["PidsLimit"]==256 and
         not host.get("PortBindings") and
         not host.get("Binds") and
         not host.get("Privileged"),
         "QA PG mount/privilege/resources/port scope changed")
    need(set((host.get("Tmpfs") or {}))==
         {"/var/run/postgresql","/tmp"},
         "QA PG runtime tmpfs configuration differs")
    mounts=pg.get("Mounts") or []
    need(len(mounts)==1 and
         mounts[0]["Destination"]=="/var/lib/postgresql/data" and
         mounts[0]["Type"]=="volume" and
         mounts[0]["Name"]==VOLUME and mounts[0]["RW"] is True,
         "QA PG uses unexpected mount or protected volume")
    need(set(pg["NetworkSettings"]["Networks"])=={QA_NET},
         "QA PG joined another Docker network")
    aliases=pg["NetworkSettings"]["Networks"][QA_NET].get("Aliases") or []
    need(QA_ALIAS in aliases,
         "QA PG required private cafe-app-db network alias missing")
    env=pg["Config"]["Env"]
    need("POSTGRES_DB=cafe" in env and
         "POSTGRES_HOST_AUTH_METHOD=trust" in env,
         "QA PG test-only database/bootstrap auth policy differs")
    need(not any(s.startswith("POSTGRES_PASSWORD=") for s in env),
         "QA PG unexpectedly exposes password in Docker inspect")
    return pg

def preflight():
    need(os.getuid()==1000,"expected owner UID1000")
    backup_audit()
    original_audit()
    qa_preflight()
    need(not exists("container",PG),"QA PG target already exists; never overwrite")
    need(not exists("volume",VOLUME),"persistent QA volume already exists")
    need(not MARKER.exists() and not MARKER.is_symlink(),
         "previous restore attempt marker exists")
    need(shutil.disk_usage(str(PRIVATE)).free>=400*1024*1024,
         "insufficient free disk for new QA persistent volume")
    print("QA PROTECTED LIVE DB / HTTP 3001 / PRIVATE NETWORK PASS",flush=True)
    print("QA MISSING PG NAME + NEW PERSISTENT VOLUME AVAILABLE",flush=True)
    print("QA PERSISTENT RESTORE PRECHECK PASS — NO WRITES",flush=True)

def create():
    preflight()
    result=docker("volume","create",
                  "--label","cafe.scope=qa-only",
                  "--label","cafe.created=2026-11-06",VOLUME)
    need(result.returncode==0,
         "QA volume creation failed; inspect before any retry")
    volume_audit()
    result=docker(
        "create","--name",PG,
        "--network",QA_NET,"--network-alias",QA_ALIAS,
        "--restart","no","--read-only",
        "--memory","768m","--pids-limit","256",
        "--tmpfs","/var/run/postgresql:rw,size=16m,mode=3775",
        "--tmpfs","/tmp:rw,size=64m,mode=1777",
        "--mount","type=volume,source={},target=/var/lib/postgresql/data".format(VOLUME),
        "--env","POSTGRES_DB=cafe",
        "--env","POSTGRES_HOST_AUTH_METHOD=trust",
        IMAGE)
    need(result.returncode==0,
         "QA PG Docker create failed; preserve volume/container")
    pg_audit("created")
    print("QA PERSISTENT POSTGRES CREATED — NOT STARTED",flush=True)
    print("NEW QA-ONLY VOLUME / NO HOST PORT / PRODUCTION UNCHANGED",flush=True)

def verify_created():
    backup_audit()
    original_audit()
    qa_preflight()
    need(not MARKER.exists() and not MARKER.is_symlink(),
         "restore attempt already recorded")
    pg_audit("created")
    print("QA PERSISTENT POSTGRES CREATED-ONLY AUDIT PASS",flush=True)
    print("NO RESTORE / NO PRODUCTION CHANGES",flush=True)

def verify_running():
    backup_audit()
    before=original_audit()
    qa_preflight()
    pg_audit("running")
    restored=sql(PG,"SELECT system_identifier::text FROM pg_control_system();")
    need(restored.isdigit() and restored!=before,
         "QA and production PG cluster identities overlap")
    need(sql(PG,"SELECT count(*) FROM public.products;")=="20",
         "QA restored catalogue product count differs")
    need(sql(PG,"SELECT count(*) FROM public.products WHERE id=21;")=="0",
         "QA restored deleted test product reappeared")
    need(sql(PG,"SELECT count(*) FROM public.users;")=="2",
         "QA restored test account count differs")
    tables=sql(PG,"SELECT count(*) FROM pg_tables WHERE schemaname='public';")
    need(tables.isdigit() and int(tables)>=10,
         "QA restored schema incomplete")
    need(original_audit()==before,"production PostgreSQL changed during QA audit")
    print("QA PERSISTENT SCHEMA / 20 PRODUCTS / 2 TEST USERS PASS",flush=True)
    print("QA DELETED ID21 ABSENT / DISTINCT PG / ORIGINAL 3001 PASS",flush=True)
    print("QA RESTORED DATABASE VERIFIED — NO LIVE DATA MODIFIED",flush=True)

def restore():
    verify_created()
    os.umask(0o077)
    before=original_audit()
    PRIVATE.mkdir(parents=True,exist_ok=True)
    with MARKER.open("x",encoding="utf-8") as dest:
        json.dump({"target":PG,"volume":VOLUME,"backup_sha256":
                   json.loads(MANIFEST.read_text())["database"]["sha256"],
                   "started_unix":int(time.time()),
                   "operation":"restore_private_qa_archive_once"},
                  dest,sort_keys=True)
        dest.write("\n")
    MARKER.chmod(0o600)
    print("QA RESTORE ONE-SHOT ATTEMPT RECORDED",flush=True)
    result=docker("start",PG)
    need(result.returncode==0,"QA PG start failed; preserve attempt/volume")
    ready=False
    for _ in range(40):
        probe=docker("exec","--user","postgres",PG,"pg_isready",
                     "-q","-U","postgres","-d",DB)
        if probe.returncode==0:
            ready=True
            break
        time.sleep(1)
    need(ready,"QA PG not ready; preserve attempt/volume")
    # Reconfirm only the newly created QA container can receive writes.
    pg_audit("running")
    need(sql(PG,"SELECT count(*) FROM pg_tables WHERE schemaname='public';")=="0",
         "QA PG not empty before archive import")
    with ARCHIVE.open("rb") as source:
        try:
            result=subprocess.run(
                ["docker","exec","-i","--user","postgres",PG,
                 "pg_restore","--username=postgres","--dbname=cafe",
                 "--no-owner","--no-acl","--exit-on-error","--single-transaction"],
                stdin=source,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                check=False,timeout=240)
        except (OSError,subprocess.TimeoutExpired):
            raise RuntimeError("CAFE QA RECOVERY STOP: one-shot pg_restore timed out")
    need(result.returncode==0,
         "one-shot QA pg_restore failed; preserve attempt, NEVER blindly retry")
    verify_running()
    need(original_audit()==before,
         "production PostgreSQL changed during QA restore")
    print("QA VERIFIED BACKUP RESTORED TO PERSISTENT VOLUME PASS",flush=True)
    print("QA RAILS/PROXY NOT STARTED BY RESTORE SCRIPT",flush=True)

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    mode=cli.add_mutually_exclusive_group(required=True)
    for name in ("check","create","verify-created","restore","verify-running"):
        mode.add_argument("--"+name,action="store_true")
    args=cli.parse_args()
    try:
        if args.check: preflight()
        elif args.create: create()
        elif args.verify_created: verify_created()
        elif args.restore: restore()
        else: verify_running()
    except Exception as err:
        msg=str(err)
        if not msg.startswith("CAFE QA RECOVERY STOP:"):
            msg="CAFE QA RECOVERY STOP: internal safety/recovery audit failure"
        print(msg,file=sys.stderr,flush=True)
        print("Do not delete or retry partial QA volume, marker or PG container.",
              file=sys.stderr,flush=True)
        sys.exit(1)

if __name__=="__main__":
    main()
