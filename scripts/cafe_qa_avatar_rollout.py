#!/usr/bin/env python3
"""Guarded, QA-only Docker avatar overlay rollout for Gor's Coffee.

Usage:
  python3 scripts/cafe_qa_avatar_rollout.py --check
  python3 scripts/cafe_qa_avatar_rollout.py --apply

Never touches the live Rails container, live PostgreSQL, master branch, or
original uploads. The only port switch is the existing QA port 3002, with
automatic proxy rollback if its HTTP smoke fails.
"""
import argparse
import http.client
import json
import subprocess
import sys
import time
from pathlib import Path

LIVE = "cafe-app-local-3001-web"
LIVE_DB = "cafe-app-db"
SOURCE = "cafe-app-uploads-qa-db-20261103"
NEW = "cafe-app-uploads-qa-avatar-20261103"
QA_DB = "cafe-upload-qa-pg-20261103"
OLD_PROXY = "cafe-upload-qa-proxy-db-20261103"
NEW_PROXY = "cafe-upload-qa-proxy-avatar-20261103"
QA_NET = "cafe-upload-qa-net-20261103"
ACCESS_NET = "cafe-upload-qa-access-20261103"
QA_URL = "postgresql://postgres@cafe-app-db:5432/cafe"

PROJECT = Path.home() / "Рабочий стол/rails_projects/lite/cafe_app"
OVERRIDES = Path.home() / ".local/share/cafe_app/qa_avatar_overrides_20261103"
QA_UPLOADS = Path.home() / ".local/share/cafe_app/uploads_qa_20261103"
EXPECTED_ORIGINAL_BLOBS = {
    "app/controllers/application_controller.rb": "f4fc969b74d080bbaa3653c135ef165de8fdc5b2",
    "app/views/devise/registrations/new.html.erb": "32eeffb4942bb20f12e0de7f9235c150be97ef48",
    "app/views/devise/registrations/edit.html.erb": "3ee2a70a427b79a1bedd4b479c504d7642b3e4c6",
}


def docker(*args, capture=False, check=True):
    return subprocess.run(["docker", *args], check=check, text=True,
                          stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                          stderr=subprocess.PIPE if capture else None)


def inspect(name):
    return json.loads(docker("inspect", name, capture=True).stdout)[0]


def exists(name):
    return docker("container", "inspect", name, capture=True, check=False).returncode == 0


def http_get(port, path):
    client = http.client.HTTPConnection("127.0.0.1", port, timeout=7)
    try:
        client.request("GET", path)
        response = client.getresponse()
        body = response.read().decode("utf-8", errors="replace")
        return response.status, body
    finally:
        client.close()


def hash_blob(path):
    return subprocess.check_output(["git", "-C", str(PROJECT),
                                    "hash-object", str(path)], text=True).strip()


def preflight():
    if not PROJECT.is_dir() or not QA_UPLOADS.is_dir():
        raise RuntimeError("Missing project or isolated QA uploads directory")
    if exists(NEW) or exists(NEW_PROXY):
        raise RuntimeError("New QA container/proxy already exists; abort to avoid overwrite")

    for rel, sha in EXPECTED_ORIGINAL_BLOBS.items():
        base = PROJECT / rel
        override = OVERRIDES / rel
        if not base.is_file() or not override.is_file() or override.is_symlink():
            raise RuntimeError("Missing or unsafe QA override: " + rel)
        if hash_blob(base) != sha:
            raise RuntimeError("Protected original modified: " + rel)
        text = override.read_text(encoding="utf-8")
        if rel.endswith("application_controller.rb"):
            if ":username, :avatar, :avatar_cache" not in text:
                raise RuntimeError("Avatar strong params not enabled in QA override")
        else:
            if "f.file_field :avatar" not in text or "multipart: true" not in text:
                raise RuntimeError("Expected multipart field missing from QA view")

    source, db, prod, live_db, old_proxy = (
        inspect(SOURCE), inspect(QA_DB), inspect(LIVE),
        inspect(LIVE_DB), inspect(OLD_PROXY)
    )
    for name, item in [(SOURCE, source), (QA_DB, db),
                       (LIVE, prod), (LIVE_DB, live_db),
                       (OLD_PROXY, old_proxy)]:
        if item["State"]["Status"] != "running":
            raise RuntimeError(name + " is not running")

    network = json.loads(docker("network", "inspect", QA_NET, capture=True).stdout)[0]
    if not network["Internal"]:
        raise RuntimeError("QA database network is not internal")

    def nets(item):
        return set(item["NetworkSettings"]["Networks"])
    if nets(source) != {QA_NET} or nets(db) != {QA_NET}:
        raise RuntimeError("QA web/DB have unexpected networks")
    if QA_NET in nets(prod) or QA_NET in nets(live_db):
        raise RuntimeError("Production is connected to QA DB network")
    if nets(old_proxy) != {QA_NET, ACCESS_NET}:
        raise RuntimeError("Unexpected old QA proxy network topology")
    if QA_NET not in db["NetworkSettings"]["Networks"]:
        raise RuntimeError("QA DB network missing")
    if "cafe-app-db" not in db["NetworkSettings"]["Networks"][QA_NET]["Aliases"]:
        raise RuntimeError("QA DB alias is missing")

    env = dict(x.split("=", 1) for x in source["Config"]["Env"])
    if env.get("DATABASE_URL") != QA_URL:
        raise RuntimeError("QA server URL differs from verified isolated DB")

    mounts = {m["Destination"]: m for m in source["Mounts"]}
    if (not source["HostConfig"]["ReadonlyRootfs"]
        or mounts["/app"]["RW"]
        or not mounts["/app/public/uploads"]["RW"]
        or mounts["/app/public/uploads"]["Source"] != str(QA_UPLOADS)):
        raise RuntimeError("Expected protected QA mount layout is not present")

    if http_get(3001, "/info")[0] != 200 or http_get(3002, "/menu")[0] != 200:
        raise RuntimeError("Existing production / QA web smoke failed")

    print("PREFLIGHT PASS — live site, original source, QA DB and uploads isolated", flush=True)
    return source


def common_args(source):
    cfg, host = source["Config"], source["HostConfig"]
    args = ["docker", "create", "--name", NEW, "--network", QA_NET,
            "--read-only", "--user", cfg["User"],
            "--workdir", cfg.get("WorkingDir") or "/app",
            "--restart", "no"]

    for entry in cfg.get("Env") or []:
        args += ["--env", entry]
    for opt in host.get("SecurityOpt") or []:
        args += ["--security-opt", opt]
    for cap in host.get("CapDrop") or []:
        args += ["--cap-drop", cap]
    for path, options in (host.get("Tmpfs") or {}).items():
        args += ["--tmpfs", path + (":" + options if options else "")]

    for dest, mount in {m["Destination"]: m for m in source["Mounts"]}.items():
        if mount["Type"] == "volume":
            spec = "type=volume,source={},target={}".format(mount["Name"], dest)
        elif mount["Type"] == "bind":
            spec = "type=bind,source={},target={}".format(mount["Source"], dest)
        else:
            raise RuntimeError("Unsupported Docker mount type: " + mount["Type"])
        if not mount["RW"]:
            spec += ",readonly"
        args += ["--mount", spec]

    for rel in EXPECTED_ORIGINAL_BLOBS:
        args += ["--mount", "type=bind,source={},target=/app/{},readonly"
                 .format(OVERRIDES / rel, rel)]

    return args + [cfg["Image"]] + (cfg.get("Cmd") or [])


def check_new_backend():
    qa = inspect(NEW)
    if qa["State"]["Status"] != "running":
        raise RuntimeError("New QA web did not start")
    if set(qa["NetworkSettings"]["Networks"]) != {QA_NET}:
        raise RuntimeError("New QA web has unsafe network exposure")

    mounts = {m["Destination"]: m for m in qa["Mounts"]}
    for rel in EXPECTED_ORIGINAL_BLOBS:
        dest = "/app/" + rel
        if mounts[dest]["Source"] != str(OVERRIDES / rel) or mounts[dest]["RW"]:
            raise RuntimeError("Missing scoped readonly override: " + rel)

    # Only internal QA HTTP, no public port. Verify actual rendered upload field.
    ruby = (
        "require 'net/http'; "
        "db = ActiveRecord::Base.connection.select_value('SELECT current_database()'); "
        "raise 'wrong QA database' unless db == 'cafe'; "
        "h = Net::HTTP.new('127.0.0.1', 3001, nil); "
        "h.open_timeout = 3; h.read_timeout = 8; "
        "r = h.get('/users/sign_up'); "
        "raise 'registration HTTP not 200' unless r.code == '200'; "
        "raise 'missing avatar field' unless r.body.include?('name=\\\"user[avatar]\\\"'); "
        "raise 'missing multipart form' unless r.body.include?('multipart/form-data'); "
        "puts 'QA AVATAR REGISTRATION HTML PASS'"
    )
    # Use rails runner to guarantee that SQL and HTTP are both tested.
    result = docker("exec", NEW, "bundle", "exec", "rails", "runner",
                    ruby, capture=True)
    print(result.stdout.strip(), flush=True)


def create_proxy():
    node = (
        "const net=require('net');"
        "net.createServer(client=>{"
        "const upstream=net.connect(3001,'"+NEW+"');"
        "client.pipe(upstream);upstream.pipe(client);"
        "client.on('error',()=>upstream.destroy());"
        "upstream.on('error',()=>client.destroy());"
        "client.on('close',()=>upstream.destroy());"
        "upstream.on('close',()=>client.destroy());"
        "}).listen(3002,'0.0.0.0');"
    )
    docker("create", "--name", NEW_PROXY, "--network", ACCESS_NET,
           "--publish", "127.0.0.1:3002:3002",
           "--read-only", "--user", "1000:1000", "--memory", "128m",
           "--pids-limit", "64", "--cap-drop", "ALL",
           "--security-opt", "no-new-privileges",
           "--restart", "no", "--entrypoint", "node",
           "cafe-legacy-full:node14", "-e", node)
    docker("network", "connect", QA_NET, NEW_PROXY)
    proxy = inspect(NEW_PROXY)
    if (set(proxy["NetworkSettings"]["Networks"]) != {ACCESS_NET, QA_NET}
        or proxy["State"]["Status"] != "created"):
        raise RuntimeError("Proxy networks differ from QA-only topology")
    print("REPLACEMENT QA PROXY CREATED — NOT STARTED", flush=True)


def switch_proxy():
    stopped = False
    try:
        docker("stop", "--time", "2", OLD_PROXY)
        stopped = True
        docker("start", NEW_PROXY)
        passed = False
        for _ in range(15):
            try:
                code, body = http_get(3002, "/users/sign_up")
                if (code == 200 and 'name="user[avatar]"' in body
                    and "multipart/form-data" in body):
                    passed = True
                    break
            except (OSError, TimeoutError):
                pass
            time.sleep(1)
        if not passed or http_get(3001, "/info")[0] != 200:
            raise RuntimeError("QA/prod smoke failed after proxy switch")
        if inspect(LIVE)["State"]["Status"] != "running":
            raise RuntimeError("Original live container state changed")
        print("QA PORT 3002 AVATAR FORM PASS", flush=True)
        print("PRODUCTION PORT 3001 HTTP 200", flush=True)
        print("PREVIOUS QA PROXY PRESERVED (stopped)", flush=True)
        print("QA AVATAR WEB READY", flush=True)
    except Exception:
        if stopped:
            docker("stop", "--time", "2", NEW_PROXY, check=False)
            docker("start", OLD_PROXY, check=False)
            print("ROLLBACK: attempted to restore previous QA proxy", flush=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="read-only preflight")
    mode.add_argument("--apply", action="store_true", help="stage QA web + switch QA proxy with rollback")
    args = parser.parse_args()

    source = preflight()
    if args.check:
        print("SAFE TO APPLY — no changes made", flush=True)
        return
    try:
        subprocess.run(common_args(source), check=True, stdout=subprocess.DEVNULL)
        print("QA AVATAR CONTAINER CREATED — NO PUBLIC PORT", flush=True)
        docker("start", NEW)
        check_new_backend()
        create_proxy()
        switch_proxy()
    except Exception as exc:
        print("FAILED:", type(exc).__name__, str(exc)[:180], file=sys.stderr)
        print("Live site was never stopped. Inspect new QA containers before retry.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
