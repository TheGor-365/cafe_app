#!/usr/bin/env python3
"""Cafe QA reboot recovery: safely start existing patched Rails + loopback proxy.

--check   read-only owner snapshot/DB/network/container preflight
--start   recheck, start ONLY existing QA Rails and existing QA proxy, verify
--verify  read-only original QA/live DB and localhost HTTP/browser-form checks

No Docker create/remove/restart/compose, migrations, SQL writes or upload writes.
Reads no private media, prints no source mounts, environment or credentials.
"""
import argparse
import hashlib
import importlib.util
from http.client import HTTPConnection
import os
from pathlib import Path
import subprocess
import sys
import time

BASE=Path.home()/".local/share/cafe_app"
RESUME=BASE/"cafe_qa_persistent_resume_v1_20261106.py"
RESUME_BLOB="f87419e7119b0c360db70ebb3684c857424922f1"
WEB="cafe-app-patched-qa-candidate-20261104"
PROXY="cafe-upload-qa-proxy-patched-20261104"
PG="cafe-upload-qa-pg-20261103"
QA_NET="cafe-upload-qa-net-20261103"
ACCESS_NET="cafe-upload-qa-access-20261103"
LIVE_NET="cafe-app-private"
PORT=3002

def require(condition,why):
    if not condition:
        raise RuntimeError("CAFE QA HTTP BOOT STOP: "+why)

def git_sha(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def verified_resume():
    require(os.getuid()==1000,"wrong owner operator UID")
    require(RESUME.is_file() and not RESUME.is_symlink(),
            "verified QA recovery file unavailable")
    st=RESUME.stat()
    require(st.st_uid==os.getuid() and not(st.st_mode & 0o022),
            "QA recovery file owner/mode changed")
    require(git_sha(RESUME)==RESUME_BLOB,"QA resume script not pinned")
    spec=importlib.util.spec_from_file_location("cafe_qa_verified_resume",RESUME)
    require(spec is not None and spec.loader is not None,"QA verification import failed")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def inspect(module,name):
    return module.load_original().inspect("container",name)

def state(container):
    return container["State"]["Status"]

def http(port,path):
    connection=HTTPConnection("127.0.0.1",port,timeout=8)
    try:
        connection.request("GET",path)
        response=connection.getresponse()
        body=response.read(196608)
        return response.status,body.decode(errors="replace")
    except (OSError,TimeoutError):
        return 0,""
    finally:
        connection.close()

def baseline():
    resume=verified_resume()
    resume.verify()  # protected live database, SHA snapshot, old one-shot markers
    main=resume.load_original()
    main.qa_preflight()
    main.pg_audit("running")

    web=main.inspect("container",WEB)
    proxy=main.inspect("container",PROXY)
    prodweb=main.inspect("container",main.LIVE_WEB)
    prodpg=main.inspect("container",main.LIVE_PG)

    require(state(web) in ("exited","running") and
            state(proxy) in ("exited","running"),
            "QA web/proxy unexpectedly created/paused/restarting")
    require(web["Config"]["Image"]=="cafe-legacy-full:node14" and
            proxy["Config"]["Image"]=="cafe-legacy-full:node14",
            "existing QA runtime images changed")
    require(set(web["NetworkSettings"]["Networks"])=={QA_NET},
            "patched web joined unexpected Docker network")
    require(set(proxy["NetworkSettings"]["Networks"])=={QA_NET,ACCESS_NET},
            "QA proxy joined unexpected Docker network")
    require(not ({QA_NET,ACCESS_NET} & set(prodweb["NetworkSettings"]["Networks"])) and
            not ({QA_NET,ACCESS_NET} & set(prodpg["NetworkSettings"]["Networks"])),
            "protected live container attached to QA")
    require(set(prodpg["NetworkSettings"]["Networks"])=={LIVE_NET},
            "protected live PG original network changed")
    require(web["HostConfig"]["ReadonlyRootfs"] is True and
            not web["HostConfig"].get("PortBindings"),
            "patched Rails readonly/no-public-port scope differs")
    mounts={m["Destination"]:m for m in web["Mounts"]}
    require(mounts.get("/app",{}).get("RW") is False and
            mounts.get("/app/public/uploads",{}).get("RW") is True,
            "patched QA code/media mount scope differs")
    env=dict(e.split("=",1) for e in web["Config"]["Env"])
    require(env.get("DATABASE_URL")==
            "postgresql://postgres@cafe-app-db:5432/cafe" and
            env.get("BUNDLE_GEMFILE")=="/app/Gemfile",
            "patched QA DB alias/bundle differs")
    require(proxy["HostConfig"]["ReadonlyRootfs"] is True and
            proxy["Config"]["User"]=="1000:1000" and
            WEB in " ".join(proxy["Config"].get("Cmd") or []),
            "QA proxy security/user/backend target differs")
    ports=(proxy["HostConfig"].get("PortBindings") or {}).get("3002/tcp",[])
    require(len(ports)==1 and ports[0].get("HostIp")=="127.0.0.1" and
            ports[0].get("HostPort")=="3002",
            "QA port mapping not loopback 127.0.0.1:3002")
    qapg=main.inspect("container",PG)
    aliases=qapg["NetworkSettings"]["Networks"][QA_NET].get("Aliases") or []
    require("cafe-app-db" in aliases,"QA PostgreSQL DNS alias unavailable")
    require(http(3001,"/")[0]==200,"protected Cafe 3001 HTTP not 200")
    print("CAFE QA VERIFIED BACKUP / ISOLATED PERSISTENT PG PASS",flush=True)
    print("CAFE QA PATCHED RAILS / LOOPBACK PROXY CONFIG PASS",flush=True)
    print("CAFE ORIGINAL 3001 HTTP PASS",flush=True)
    return resume,main,web,proxy

def verify():
    resume,main,web,proxy=baseline()
    require(state(web)=="running" and state(proxy)=="running",
            "QA web or proxy is not running")
    menu,body=http(PORT,"/menu")
    require(menu==200,"QA /menu HTTP not 200")
    signup,form=http(PORT,"/users/sign_up")
    require(signup==200 and
            'name="user[avatar]"' in form and "multipart/form-data" in form,
            "QA signup multipart avatar form missing")
    result=subprocess.run(["docker","exec",WEB,"bundle","exec","ruby","-e",
                           "require 'carrierwave'; print Gem.loaded_specs.fetch('carrierwave').version"],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          check=False,timeout=25)
    require(result.returncode==0 and result.stdout.decode().strip()=="2.2.7",
            "patched CarrierWave version not 2.2.7")
    resume.verify()
    print("CAFE QA 3002 MENU/SIGNUP/MULTIPART HTTP 200 PASS",flush=True)
    print("CAFE QA PATCHED CARRIERWAVE 2.2.7 PASS",flush=True)
    print("CAFE 3001/3002 PG ISOLATION / RECOVERY COMPLETE PASS",flush=True)

def start():
    resume,main,web,proxy=baseline()
    if state(web)!="running":
        ret=subprocess.run(["docker","start",WEB],
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                           check=False,timeout=35)
        require(ret.returncode==0,
                "QA patched Rails failed to start; inspect only QA logs")
        print("CAFE PATCHED QA RAILS STARTED",flush=True)
    else:
        print("CAFE PATCHED QA RAILS ALREADY RUNNING",flush=True)
    require(state(main.inspect("container",WEB))=="running",
            "QA Rails process not running after start")
    if state(proxy)!="running":
        ret=subprocess.run(["docker","start",PROXY],
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                           check=False,timeout=35)
        require(ret.returncode==0,
                "QA loopback proxy failed to start; do not restart production")
        print("CAFE QA LOOPBACK PROXY STARTED",flush=True)
    else:
        print("CAFE QA LOOPBACK PROXY ALREADY RUNNING",flush=True)
    ready=False
    for attempt in range(45):
        code,_body=http(PORT,"/menu")
        if code==200:
            ready=True
            break
        if state(main.inspect("container",WEB))!="running" or \
           state(main.inspect("container",PROXY))!="running":
            break
        time.sleep(1)
    require(ready,"QA HTTP /menu did not become ready; preserve QA containers")
    verify()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    for name in ("check","start","verify"):
        mode.add_argument("--"+name,action="store_true")
    args=parser.parse_args()
    try:
        if args.check: baseline()
        elif args.start: start()
        else: verify()
    except Exception as error:
        message=str(error)
        if not message.startswith("CAFE QA HTTP BOOT STOP:"):
            message="CAFE QA HTTP BOOT STOP: internal safety or runtime check failed"
        print(message,file=sys.stderr,flush=True)
        print("Do not remove/recreate QA Docker objects or touch original Cafe.",
              file=sys.stderr,flush=True)
        sys.exit(1)

if __name__=="__main__":
    main()
