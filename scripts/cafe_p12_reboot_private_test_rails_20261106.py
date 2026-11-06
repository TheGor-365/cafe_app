#!/usr/bin/env python3
"""Resume ONLY previously created Cafe isolated private Rails QA services.

Prerequisite: original 3001/3002 + sandbox/fourth test PostgreSQL verified.
--check:  READ ONLY check 4 existing stopped candidates, no production exposure.
--start:  ONE SHOT: exclusive private marker, docker start exactly these 4
          previously created private candidates in dependency order, verify.
--verify: READ ONLY: re-run original pinned fourth read-only Rails contract
          and old protected four-database source baseline.

NEVER create/remove Docker resources, switch Git branch, change a database,
run a migration/seed, export private media, enable a host port or touch
production Rails or primary QA Rails. All modes print sanitized summaries only.
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

PRIVATE=Path.home()/".local/share/cafe_app"
PREV=PRIVATE/"cafe_p12_tmpfs_restore_v1_20261106.py"
PREV_BLOB="403609bc7710b88b109959caed49a850c7f068c8"
WEB_HELPER=PRIVATE/"cafe_private_e2e_web_recovery_v2_20261105.py"
WEB_BLOB="62e52015dfe7dd5ca15b1c3eabe380a38e7eca0a"
MARKER=PRIVATE/"cafe_p12_test_rails_boot_once_20261106.json"
SANDBOX_NET="cafe-upload-security-sandbox-20261104"
FOURTH_NET="cafe-upload-security-e2e-net-20261105"
IMAGE="cafe-legacy-full:node14"
CANDIDATES=(
  ("sandbox-original","cafe-upload-security-sandbox-rails-20261104",
   SANDBOX_NET,"postgresql://postgres@cafe-app-db:5432/cafe",False),
  ("sandbox-precache","cafe-upload-security-sandbox-precache-20261104",
   SANDBOX_NET,"postgresql://postgres@cafe-app-db:5432/cafe",False),
  ("headers-reportonly","cafe-upload-security-headers-mountfix-20261104",
   SANDBOX_NET,"postgresql://postgres@cafe-app-db:5432/cafe",True),
  ("fourth-readonly","cafe-upload-security-e2e-web-readonly-20261105",
   FOURTH_NET,"postgresql://postgres@cafe-e2e-postgres:5432/cafe",True),
)

def require(value,reason):
    if not value:
        raise RuntimeError("P1.2 TEST RAILS BOOT STOP: "+reason)

def git_blob(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(path,blob,name):
    require(os.getuid()==1000,"unexpected owner UID for private Cafe QA")
    require(path.is_file() and not path.is_symlink(),
            name+" pinned helper missing or symlink")
    stat=path.stat()
    require(stat.st_uid==os.getuid() and not (stat.st_mode&0o022),
            name+" pinned helper owner/mode changed")
    require(git_blob(path)==blob,
            name+" reviewed helper Git SHA does not match")
    spec=importlib.util.spec_from_file_location(name,path)
    require(spec is not None and spec.loader is not None,
            "cannot load reviewed owner helper")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def docker_start(name):
    try:
        result=subprocess.run(["docker","start",name],stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,check=False,timeout=50)
    except (OSError,subprocess.TimeoutExpired):
        raise RuntimeError("P1.2 TEST RAILS BOOT STOP: Docker start timeout")
    require(result.returncode==0,
            name+" failed start; preserve attempt marker/containers")

def inspect_web(inv,label,name,network,url,readonly):
    obj=inv.inspect("container",name)
    conf=obj["Config"];host=obj["HostConfig"]
    status=obj["State"]["Status"]
    require(obj["Name"].lstrip("/")==name and
            status in ("exited","running") and
            conf["Image"]==IMAGE and
            conf["User"]=="1000:1000" and
            host["ReadonlyRootfs"] is True and
            host["RestartPolicy"]["Name"]=="no" and
            not host.get("PortBindings") and
            set(obj["NetworkSettings"]["Networks"])=={network},
            label+" preexisting private QA runtime differs")
    original_mounts=obj["Mounts"]
    mounts={m["Destination"]:m for m in original_mounts}
    require(len(mounts)==len(original_mounts),
            label+" duplicate Docker mount destinations")
    private_media={
        "sandbox-original": PRIVATE/"uploads_security_sandbox_20261104",
        "sandbox-precache": PRIVATE/"uploads_security_sandbox_20261104",
        "headers-reportonly": PRIVATE/"headers_private_web_mountfix_20261104/uploads",
        "fourth-readonly": PRIVATE/"e2e_web_readonly_20261105/uploads",
    }
    require(label in private_media and
            mounts.get("/app/public/uploads",{}).get("Source")==str(private_media[label]) and
            mounts.get("/bundle",{}).get("Type")=="bind" and
            mounts["/bundle"]["Source"]==str(PRIVATE/"bundle_carrierwave_227_20261104") and
            mounts["/bundle"]["RW"] is False,
            label+" original private media / frozen Ruby bundle differs")
    # Existing reviewed sandbox sources expressly inherit read-only named
    # volumes (e.g. the legacy Ruby dependencies), not just host binds.
    # Reject only unrecognized/writable mounts; do not mutate Docker.
    require(mounts.get("/app",{}).get("Type")=="bind" and
            mounts["/app"]["RW"] is False and
            mounts.get("/app/public/uploads",{}).get("Type")=="bind" and
            mounts["/app/public/uploads"]["RW"] is True and
            all((dest=="/app/public/uploads" or m["RW"] is False) and
                m["Type"] in ("bind","volume") and
                (m["Type"]!="volume" or
                 (isinstance(m.get("Name"),str) and bool(m["Name"])))
                for dest,m in mounts.items()) and
            "/run/secrets/cafe_pg_password" not in mounts,
            label+" source/media mount scope changed")
    envlist=conf["Env"]
    env=dict(x.split("=",1) for x in envlist)
    require(len(env)==len(envlist) and
            env.get("DATABASE_URL")==url and
            env.get("BUNDLE_GEMFILE")=="/app/Gemfile" and
            env.get("RAILS_ENV")=="development",
            label+" private test DB / Rails environment differs")
    if readonly:
        require(env.get("PGOPTIONS")=="-c default_transaction_read_only=on",
                label+" read-only SQL session missing")
    require(not any(
            word in key.upper() for key in env
            for word in ("TOKEN","SECRET","PASSWORD","CREDENTIAL","API_KEY")),
            label+" unexpected secret-like environment variable")
    return status

def verify_networks(inv):
    expected=(
       (SANDBOX_NET,{"cafe-upload-security-sandbox-pg-20261104",
        "cafe-upload-security-sandbox-rails-20261104",
        "cafe-upload-security-sandbox-precache-20261104",
        "cafe-upload-security-headers-mountfix-20261104"}),
       (FOURTH_NET,{"cafe-upload-security-e2e-pg-20261105",
        "cafe-upload-security-e2e-web-readonly-20261105"}),
    )
    for name,allowed in expected:
        net=inv.inspect("network",name)
        require(net["Internal"] is True,"test Rails network not internal")
        members={x.get("Name") for x in
                 (net.get("Containers") or {}).values()}
        require(members.issubset(allowed),
                "unrecognized container in isolated test Rails network")
        require("cafe-app-db" not in members and
                "cafe-upload-qa-pg-20261103" not in members,
                "protected production or QA DB connected to test net")

def checked_sources():
    inv=load(PREV,PREV_BLOB,"cafe_owner_verified_two_pg")
    inv.verify()  # independent snapshot SHA, PG3+PG4 + original 3001/3002
    states={}
    for label,name,net,url,readonly in CANDIDATES:
        states[name]=inspect_web(inv.inventory(),label,name,net,url,readonly)
    verify_networks(inv.inventory())
    fifth=inv.inventory().inspect("container",inv.FIFTH)
    require(fifth["State"]["Status"]=="exited",
            "fifth synthetic DB was unexpectedly started")
    require(not inv.inventory().SCHEMA_MARKER.exists() and
            not inv.inventory().SCHEMA_MARKER.is_symlink(),
            "previous fifth DDL marker exists; cannot bootstrap")
    print("P1.2 ORIGINAL 3001/3002 + RESTORED SANDBOX/FOURTH DB PASS",flush=True)
    print("P1.2 4 EXISTING ISOLATED TEST RAILS / PRIVATE BIND / NETWORK PASS",flush=True)
    print("P1.2 FIFTH SYNTHETIC DATABASE STILL STOPPED PASS",flush=True)
    return states

def check():
    require(not MARKER.exists() and not MARKER.is_symlink(),
            "test Rails boot already attempted; inspect instead of retry")
    states=checked_sources()
    for label,name,_,_,_ in CANDIDATES:
        print("P1.2 "+label.upper()+" RAILS: "+states[name].upper(),flush=True)
    print("P1.2 PRIVATE TEST RAILS BOOT READY — NO WRITES",flush=True)

def verify():
    require(MARKER.is_file() and not MARKER.is_symlink(),
            "test Rails boot attempt marker missing")
    stat=MARKER.stat()
    require(stat.st_uid==os.getuid() and not(stat.st_mode&0o077) and
            stat.st_size<2048,
            "test Rails boot marker owner/mode differs")
    record=json.loads(MARKER.read_text(encoding="utf-8"))
    require(record.get("operation")=="boot_four_existing_private_rails_once" and
            record.get("names")==[p[1] for p in CANDIDATES],
            "test Rails boot marker targets changed")
    states=checked_sources()
    require(all(states[x[1]]=="running" for x in CANDIDATES),
            "not all historical private QA Rails are running")
    web=load(WEB_HELPER,WEB_BLOB,"cafe_reviewed_fourth_readonly_e2e")
    fourth,headers,launcher,candidate,manifest=web.preflight()
    web.inspect_web(headers,launcher,manifest,"running")
    print("P1.2 SANDBOX/PRECACHE/HEADERS + FOURTH READONLY WEB PASS",flush=True)
    print("P1.2 PINNED ORIGINAL FOUR-CLUSTER RAILS SOURCE AUDIT PASS",flush=True)
    print("P1.2 PRIVATE TEST RAILS BOOT INDEPENDENT VERIFY PASS",flush=True)

def start():
    check()
    os.umask(0o077)
    flags=os.O_CREAT|os.O_EXCL|os.O_WRONLY
    if hasattr(os,"O_NOFOLLOW"): flags|=os.O_NOFOLLOW
    fd=os.open(str(MARKER),flags,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as dest:
        json.dump({"operation":"boot_four_existing_private_rails_once",
                  "names":[p[1] for p in CANDIDATES],
                  "started_unix":int(time.time())},dest,sort_keys=True)
        dest.write("\n")
    print("P1.2 PRIVATE FOUR-RAILS ONE-SHOT MARKER RECORDED",flush=True)
    for label,name,_,_,_ in CANDIDATES:
        state=checked_sources()[name]
        if state=="exited":
            docker_start(name)
            print("P1.2 PRIVATE "+label.upper()+" RAILS STARTED",flush=True)
        else:
            print("P1.2 PRIVATE "+label.upper()+" RAILS ALREADY RUNNING",flush=True)
        require(inspect_web(inv=load(PREV,PREV_BLOB,"cafe_owner_verified_two_pg").inventory(),
                            label=label,name=name,
                            network=next(x[2] for x in CANDIDATES if x[1]==name),
                            url=next(x[3] for x in CANDIDATES if x[1]==name),
                            readonly=next(x[4] for x in CANDIDATES if x[1]==name))=="running",
                "private Rails candidate not running after start")
    verify()
    print("P1.2 FOUR PRIVATE RAILS BOOT COMPLETE — NO FIFTH DDL",flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    for name in ("check","start","verify"):
        mode.add_argument("--"+name,action="store_true")
    args=parser.parse_args()
    try:
        if args.check:check()
        elif args.start:start()
        else:verify()
    except Exception as e:
        msg=str(e)
        if not msg.startswith("P1.2 TEST RAILS BOOT STOP:"):
            msg="P1.2 TEST RAILS BOOT STOP: internal safety/compatibility audit failure"
        print(msg,file=sys.stderr,flush=True)
        print("Preserve boot marker, test Rails and PG containers; never blindly retry.",
              file=sys.stderr,flush=True)
        sys.exit(1)

if __name__=="__main__":main()
