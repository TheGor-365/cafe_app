#!/usr/bin/env python3
"""Cut over ONLY the loopback QA proxy (port 3002) to patched CarrierWave QA.

--check  : read-only host/container/network/HTTP preflight.
--switch : create a NEW isolated QA proxy, stop old QA proxy, start new,
           smoke port 3002; automatically attempt rollback on failure.

Never changes application code, real site 3001, PostgreSQL, existing media,
existing QA Rails instances or Docker volumes. Never deletes old proxy.
CAUTION: New QA web uses a separate COPY of QA media but shares QA DB;
once new uploads are made, rolling back requires media reconciliation.
"""
import argparse
from http.client import HTTPConnection
import json
import subprocess
import sys
import time
from pathlib import Path

OLD_PROXY = "cafe-upload-qa-proxy-avatar-20261103"
NEW_PROXY = "cafe-upload-qa-proxy-patched-20261104"
OLD_WEB = "cafe-app-uploads-qa-avatar-20261103"
NEW_WEB = "cafe-app-patched-qa-candidate-20261104"
QA_PG = "cafe-upload-qa-pg-20261103"
LIVE_PG = "cafe-app-db"
LIVE_WEB = "cafe-app-local-3001-web"
QA_NET = "cafe-upload-qa-net-20261103"
ACCESS_NET = "cafe-upload-qa-access-20261103"
PATCHED_BUNDLE = Path.home() / ".local/share/cafe_app/bundle_carrierwave_227_20261104"
PATCHED_UPLOADS = Path.home() / ".local/share/cafe_app/uploads_patched_qa_20261104"
PATCHED_OVERRIDE = Path.home() / ".local/share/cafe_app/qa_patched_avatar_20261104/avatar_uploader.rb"
STAGED = Path.home() / ".local/share/cafe_app/security_bundle_build_20261104"
ORIGINAL_QA_UPLOADS = Path.home() / ".local/share/cafe_app/uploads_qa_20261103"
PUBLIC_BIND = "127.0.0.1:3002:3002"


def run(*args, capture=False, check=True):
    return subprocess.run(["docker", *args],
                          check=check, text=True,
                          stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                          stderr=subprocess.PIPE if capture else None)


def inspect(name):
    return json.loads(run("inspect", name, capture=True).stdout)[0]


def container_exists(name):
    return run("container", "inspect", name,
               capture=True, check=False).returncode == 0


def check(condition, message):
    if not condition:
        raise RuntimeError("CUTOVER BLOCKED: " + message)


def response(port, path):
    http = HTTPConnection("127.0.0.1", port, timeout=8)
    try:
        http.request("GET", path)
        reply = http.getresponse()
        status = reply.status
        body = reply.read().decode("utf-8", errors="replace")
        return status, body
    finally:
        http.close()


def db_identity(name):
    result = run("exec", "--user", "postgres", name, "psql",
                 "-X", "-At", "-U", "postgres", "-d", "cafe",
                 "-c", "SELECT system_identifier::text FROM pg_control_system();",
                 capture=True)
    return result.stdout.strip()


def inspect_readonly():
    names = (OLD_PROXY, OLD_WEB, NEW_WEB, QA_PG, LIVE_PG, LIVE_WEB)
    old_proxy, old_web, new_web, qa_pg, live_pg, live = [inspect(n) for n in names]

    for label, obj in zip(names, (old_proxy, old_web, new_web, qa_pg, live_pg, live)):
        check(obj["State"]["Status"] == "running", label + " must be running")

    nets = lambda obj: set(obj["NetworkSettings"]["Networks"])
    check(nets(old_proxy) == {QA_NET, ACCESS_NET}, "unexpected previous proxy networks")
    check(nets(old_web) == {QA_NET}, "previous QA Rails network changed")
    check(nets(new_web) == {QA_NET}, "patched QA Rails network changed")
    check(nets(qa_pg) == {QA_NET}, "QA PostgreSQL network changed")
    check(QA_NET not in nets(live) and QA_NET not in nets(live_pg),
          "production exposed to QA network")

    old_cmd = " ".join(old_proxy["Config"].get("Cmd") or [])
    check(OLD_WEB in old_cmd, "old proxy no longer targets previous QA web")
    check(old_proxy["Config"]["Image"] == "cafe-legacy-full:node14",
          "previous proxy image changed")
    check(old_proxy["HostConfig"]["ReadonlyRootfs"], "previous proxy root not readonly")
    check(old_proxy["Config"]["User"] == "1000:1000", "previous proxy user changed")
    bind = old_proxy["HostConfig"]["PortBindings"]["3002/tcp"]
    check(len(bind) == 1 and bind[0]["HostIp"] == "127.0.0.1"
          and bind[0]["HostPort"] == "3002", "old proxy port mapping differs")

    mounts = {m["Destination"]: m for m in new_web["Mounts"]}
    check(new_web["HostConfig"]["ReadonlyRootfs"], "patched Rails root not readonly")
    check(not new_web["HostConfig"]["PortBindings"], "new QA Rails has a public port")
    check(not mounts["/app"]["RW"], "patched Rails /app mount is writable")
    for dest, source in [
        ("/bundle", PATCHED_BUNDLE),
        ("/app/Gemfile", STAGED / "Gemfile"),
        ("/app/Gemfile.lock", STAGED / "Gemfile.lock"),
        ("/app/app/uploaders/avatar_uploader.rb", PATCHED_OVERRIDE),
    ]:
        check(mounts[dest]["Source"] == str(source) and not mounts[dest]["RW"],
              "patched read-only mount differs: " + dest)
    media = mounts["/app/public/uploads"]
    check(media["Source"] == str(PATCHED_UPLOADS) and media["RW"],
          "patched QA media mount differs")

    check(qa_pg["NetworkSettings"]["Networks"][QA_NET]["Aliases"]
          and "cafe-app-db" in qa_pg["NetworkSettings"]["Networks"][QA_NET]["Aliases"],
          "QA PostgreSQL alias missing")

    new_env = dict(item.split("=", 1) for item in new_web["Config"]["Env"])
    check(new_env["DATABASE_URL"] == "postgresql://postgres@cafe-app-db:5432/cafe",
          "QA URL differs from private alias")
    check(new_env.get("BUNDLE_GEMFILE") == "/app/Gemfile", "patched bundle Gemfile missing")

    qa_id, live_id = db_identity(QA_PG), db_identity(LIVE_PG)
    check(qa_id.isdigit() and live_id.isdigit() and qa_id != live_id,
          "QA and live PostgreSQL system identifiers not distinct")

    current_qa, _ = response(3002, "/menu")
    current_live, _ = response(3001, "/info")
    check(current_qa == 200 and current_live == 200, "existing site HTTP failed")

    # Verify patched candidate's *actual* running bundle (no changes).
    version = run("exec", NEW_WEB, "bundle", "exec", "ruby", "-e",
                  "require 'carrierwave'; print Gem.loaded_specs.fetch('carrierwave').version",
                  capture=True).stdout.strip()
    check(version == "2.2.7", "candidate runtime not CarrierWave 2.2.7")

    print("PATCHED QA PROXY PREFLIGHT PASS", flush=True)
    print("LIVE 3001 / OLD QA 3002 HTTP 200", flush=True)
    print("PATCHED RAILS / QA DATABASE ISOLATION VERIFIED", flush=True)


def create_new_proxy():
    check(not container_exists(NEW_PROXY),
          "replacement QA proxy already exists; inspect before retry")

    code = (
        "const net=require('net');"
        "net.createServer(client=>{"
        "const upstream=net.connect(3001,'" + NEW_WEB + "');"
        "client.pipe(upstream);upstream.pipe(client);"
        "client.on('error',()=>upstream.destroy());"
        "upstream.on('error',()=>client.destroy());"
        "client.on('close',()=>upstream.destroy());"
        "upstream.on('close',()=>client.destroy());"
        "}).listen(3002,'0.0.0.0');"
    )
    run("create",
        "--name", NEW_PROXY,
        "--network", ACCESS_NET,
        "--publish", PUBLIC_BIND,
        "--read-only", "--user", "1000:1000",
        "--memory", "128m", "--pids-limit", "64",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--restart", "no",
        "--entrypoint", "node",
        "cafe-legacy-full:node14", "-e", code)

    # Only attach the NEW proxy to the existing isolated QA private network.
    run("network", "connect", QA_NET, NEW_PROXY)

    created = inspect(NEW_PROXY)
    check(created["State"]["Status"] == "created", "new proxy unexpectedly running")
    check(set(created["NetworkSettings"]["Networks"]) == {QA_NET, ACCESS_NET},
          "new proxy network isolation differs")
    check(NEW_WEB in " ".join(created["Config"].get("Cmd") or []),
          "new proxy backend target differs")
    check(created["HostConfig"]["ReadonlyRootfs"], "new proxy not readonly")
    check(created["Config"]["User"] == "1000:1000", "new proxy user differs")
    binding = created["HostConfig"]["PortBindings"]["3002/tcp"]
    check(len(binding) == 1 and binding[0]["HostIp"] == "127.0.0.1"
          and binding[0]["HostPort"] == "3002", "new proxy port differs")
    print("REPLACEMENT QA PROXY CREATED — NOT STARTED", flush=True)


def switch():
    inspect_readonly()
    check(not container_exists(NEW_PROXY),
          "new proxy already exists; do not retry over it")
    create_new_proxy()
    stopped_old = False
    try:
        run("stop", "--time", "2", OLD_PROXY)
        stopped_old = True
        run("start", NEW_PROXY)

        passed = False
        for _ in range(15):
            try:
                status_menu, _ = response(3002, "/menu")
                status_form, body = response(3002, "/users/sign_up")
                if (status_menu == 200 and status_form == 200
                    and 'name="user[avatar]"' in body
                    and "multipart/form-data" in body):
                    passed = True
                    break
            except (OSError, TimeoutError):
                pass
            time.sleep(1)

        check(passed, "new QA proxy failed menu or signup HTTP")
        check(response(3001, "/info")[0] == 200,
              "main site HTTP failed after QA switch")
        check(inspect(LIVE_WEB)["State"]["Status"] == "running",
              "production container unexpectedly stopped")
        check(inspect(OLD_WEB)["State"]["Status"] == "running",
              "old QA web unexpectedly stopped")
        check(inspect(NEW_WEB)["State"]["Status"] == "running",
              "patched QA web unexpectedly stopped")
        print("PATCHED QA PROXY HTTP 200 / SIGNUP AVATAR FORM PASS", flush=True)
        print("PRODUCTION 3001 HTTP 200", flush=True)
        print("OLD QA PROXY PRESERVED (STOPPED)", flush=True)
        print("PATCHED QA PORT 3002 SWITCH VERIFIED", flush=True)
        print("DO NOT UPLOAD UNTIL MULTIPART TEST PLAN IS READY", flush=True)
    except Exception as error:
        print("CUTOVER FAILED:", type(error).__name__, str(error)[:300],
              file=sys.stderr)
        if stopped_old:
            run("stop", "--time", "2", NEW_PROXY, check=False)
            restored = run("start", OLD_PROXY, check=False)
            if restored.returncode == 0:
                try:
                    status, _ = response(3002, "/menu")
                    print("QA PROXY ROLLBACK HTTP:", status, flush=True)
                except Exception as issue:
                    print("QA ROLLBACK HTTP CHECK FAILED:", repr(issue)[:160],
                          file=sys.stderr)
            else:
                print("QA PROXY ROLLBACK FAILED: manual inspection required",
                      file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true",
                       help="read-only verification; no Docker changes")
    modes.add_argument("--switch", action="store_true",
                       help="create new QA proxy and switch ONLY port 3002")
    options = parser.parse_args()
    try:
        if options.check:
            inspect_readonly()
            check(not container_exists(NEW_PROXY), "new QA proxy already exists")
            print("CUTOVER READY — NO CHANGES MADE", flush=True)
        else:
            switch()
    except Exception as error:
        print("QA SWITCH BLOCKED:", type(error).__name__,
              str(error)[:350], file=sys.stderr)
        print("Inspect existing resources before retry; never delete media or DB",
              file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
