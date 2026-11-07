#!/usr/bin/env python3
"""Fail-closed, standalone localhost-only Cafe RC71 preview.

Four distinct modes:
  --check   read-only preflight of local setup and reserved resource names
  --stage   private GitHub clone pinned to one immutable reviewed commit
  --launch  create ONLY new preview network/PG, seed it, build JS, start port 3003
  --verify  read-only isolation/DB/HTTP checks, with no secrets printed

This NEVER changes existing Rails 3001/3002, original four PGs,
the protected fifth synthetic PG, the user's dirty checkout or uploads.
Creation is one-shot. On an error, preserve partial resources and inspect;
never blindly re-run --launch or delete an existing Docker object.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import stat
import subprocess
import sys
import time

HOME = Path.home()
PRIVATE = HOME / ".local/share/cafe_app"
WORK = PRIVATE / "rc71_preview_20261108"
SOURCE = WORK / "source"
LOCAL = HOME / "Рабочий стол/rails_projects/lite/cafe_app"
LOCAL_BRANCH = "feature/cafe-integration-local-20261101"
REPO = "https://github.com/TheGor-365/cafe_app.git"
SOURCE_BRANCH = "feature/cafe-admin-drink-options-20261107"
EXPECTED_HEAD = "83d3346418fccc158bcc72d9c30fb17603b43d30"
IMAGE = "cafe-legacy-full:node14"
DB_IMAGE = "postgres:16"
WEB_LIVE = "cafe-app-local-3001-web"
DB_LIVE = "cafe-app-db"
NET = "cafe-rc71-net-20261108"
PG_VOLUME = "cafe-rc71-pgdata-20261108"
PG = "cafe-rc71-pg-20261108"
SETUP = "cafe-rc71-setup-20261108"
WEB = "cafe-rc71-web-20261108"
PORT = 3003
ADMIN_EMAIL = "preview-admin@example.test"
ENV_RUN = WORK / "preview-web.env"
ENV_SETUP = WORK / "preview-setup.env"
ENV_PG = WORK / "preview-postgres.env"
CRED = WORK / "preview-admin-local-only.txt"


class Stop(RuntimeError):
    pass


def need(condition, reason):
    if not condition:
        raise Stop("CAFE RC71 STOP: " + reason)


def execute(*args, timeout=30, must=True):
    try:
        r = subprocess.run(list(args), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise Stop("CAFE RC71 STOP: subprocess unavailable or timed out")
    if must:
        need(r.returncode == 0, "command failed; preserve state for diagnosis")
    return r


def inspect(kind, name):
    r = execute("docker", kind, "inspect", name, timeout=15, must=False)
    if r.returncode:
        return None
    try:
        value = json.loads(r.stdout.decode())
        return value[0] if isinstance(value, list) else value
    except (ValueError, IndexError, TypeError):
        raise Stop("CAFE RC71 STOP: Docker inspection failed")


def git_head(path):
    return execute("git", "-C", str(path), "rev-parse", "HEAD").stdout.decode().strip()


def port_free():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", PORT)) != 0


def private_parent():
    need(os.getuid() == 1000, "expected owner UID 1000")
    need(PRIVATE.is_dir() and not PRIVATE.is_symlink(),
         "private base directory absent")
    p = PRIVATE.stat()
    need(p.st_uid == os.getuid() and (stat.S_IMODE(p.st_mode) & 0o077) == 0,
         "private base folder is not owner-only")


def local_baseline():
    private_parent()
    need(LOCAL.is_dir() and not LOCAL.is_symlink(), "owner checkout missing")
    branch = execute("git", "-C", str(LOCAL), "branch", "--show-current").stdout.decode().strip()
    need(branch == LOCAL_BRANCH, "owner checkout branch changed")
    live = inspect("container", WEB_LIVE)
    db = inspect("container", DB_LIVE)
    need(live is not None and db is not None, "original Cafe containers missing")
    need(live["Config"]["Image"] == IMAGE and live["State"]["Running"],
         "original web image or running status differs")
    need(db["State"]["Running"], "original PostgreSQL not running")
    mounts = {m["Destination"]: m for m in live["Mounts"]}
    for dest in ("/app", "/bundle", "/app/node_modules", "/app/public/packs"):
        need(dest in mounts and mounts[dest]["RW"] is False,
             "reviewed original readonly source/gem/asset mount differs")
    for dest in ("/bundle", "/app/node_modules"):
        need(mounts[dest]["Type"] == "volume" and mounts[dest].get("Name"),
             "reviewed dependency volume missing")
    need(inspect("image", IMAGE) is not None and
         inspect("image", DB_IMAGE) is not None,
         "local preview Docker images not present")
    return mounts["/bundle"]["Name"], mounts["/app/node_modules"]["Name"]


def objects_absent():
    for kind, obj in (("network", NET), ("volume", PG_VOLUME),
                      ("container", PG), ("container", SETUP),
                      ("container", WEB)):
        need(inspect(kind, obj) is None,
             "reserved preview Docker object already exists: " + obj)
    need(port_free(), "localhost 3003 already listening")


def check():
    local_baseline()
    need(not WORK.exists() and not WORK.is_symlink(),
         "preview private work path already exists")
    objects_absent()
    print("CAFE RC71 OWNER ORIGINALS / DEPENDENCIES / IMAGES PASS")
    print("CAFE RC71 ALL NEW RESOURCE NAMES / 3003 FREE PASS")
    print("CAFE RC71 READ-ONLY PREFLIGHT PASS — NO FILES/DB/DOCKER WRITES")


def stage():
    check()
    os.umask(0o077)
    WORK.mkdir(mode=0o700)
    result = execute("git", "clone", "--quiet", "--single-branch", "--depth", "1",
                     "--branch", SOURCE_BRANCH, REPO, str(SOURCE),
                     timeout=180, must=False)
    need(result.returncode == 0, "private pinned clone failed; preserve stage")
    need(git_head(SOURCE) == EXPECTED_HEAD,
         "GitHub head drifted; do not use clone or move branch")
    for folder in ("tmp", "tmp/pids", "log", "packs", "uploads"):
        (WORK / folder).mkdir(parents=True, exist_ok=True, mode=0o700)
    (WORK / "stage.json").write_text(json.dumps(
        {"expected_head": EXPECTED_HEAD, "source_branch": SOURCE_BRANCH}) + "\n")
    print("CAFE RC71 PRIVATE IMMUTABLE SOURCE CHECKOUT PASS")
    print("CAFE RC71 STAGING PASS — NO DOCKER OR DATABASE CHANGES")


def stage_valid():
    local_baseline()
    need(WORK.is_dir() and not WORK.is_symlink(), "private preview stage absent")
    need(WORK.stat().st_uid == os.getuid() and
         (stat.S_IMODE(WORK.stat().st_mode) & 0o077) == 0,
         "preview stage permissions unsafe")
    need(SOURCE.is_dir() and not SOURCE.is_symlink(), "private Git clone absent")
    need(git_head(SOURCE) == EXPECTED_HEAD,
         "pinned private source changed")
    try:
        marker = json.loads((WORK / "stage.json").read_text())
    except (OSError, ValueError):
        raise Stop("CAFE RC71 STOP: stage marker absent or invalid")
    need(marker.get("expected_head") == EXPECTED_HEAD, "stage marker SHA differs")


def save_secret(path, value):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(value)
    os.chmod(path, 0o600)


def mount_args(bundle, node):
    result = []
    mounts = [
        "type=bind,source=" + str(SOURCE) + ",target=/app,readonly",
        "type=volume,source=" + bundle + ",target=/bundle,readonly",
        "type=volume,source=" + node + ",target=/app/node_modules,readonly",
        "type=bind,source=" + str(WORK / "tmp") + ",target=/app/tmp",
        "type=bind,source=" + str(WORK / "log") + ",target=/app/log",
        "type=bind,source=" + str(WORK / "packs") + ",target=/app/public/packs",
        "type=bind,source=" + str(WORK / "uploads") + ",target=/app/public/uploads",
    ]
    for mount in mounts:
        result.extend(["--mount", mount])
    return result


def web_common(bundle, node):
    return [
        "--network", NET,
        "--user", "1000:1000", "--workdir", "/app",
        "--read-only", "--tmpfs", "/tmp:rw,size=128m,mode=1777",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--pids-limit", "180",
    ] + mount_args(bundle, node)


def wait_pg():
    for _ in range(50):
        r = execute("docker", "exec", PG, "pg_isready", "-U", "postgres", "-d", "cafe",
                    timeout=8, must=False)
        if r.returncode == 0:
            return
        time.sleep(1)
    raise Stop("CAFE RC71 STOP: new preview PG did not become ready")


def sql(query):
    r = execute("docker", "exec", PG, "psql", "-X", "-At", "-v",
                "ON_ERROR_STOP=1", "-U", "postgres", "-d", "cafe",
                "-c", query, timeout=20)
    return r.stdout.decode().strip()


def launch():
    stage_valid()
    bundle, node = local_baseline()
    objects_absent()
    for dest in ("tmp", "tmp/pids", "log", "packs", "uploads"):
        need((WORK / dest).is_dir() and not (WORK / dest).is_symlink(),
             "preview scratch directory changed")
    os.umask(0o077)
    password = secrets.token_hex(24)
    admin_password = secrets.token_urlsafe(24)
    db_url = "postgresql://postgres:" + password + "@rc71-pg:5432/cafe"
    save_secret(ENV_PG, "POSTGRES_USER=postgres\nPOSTGRES_DB=cafe\nPOSTGRES_PASSWORD=" +
                password + "\nPOSTGRES_HOST_AUTH_METHOD=scram-sha-256\n")
    base_env = ("RAILS_ENV=development\nNODE_ENV=development\nRUBYOPT=-rlogger\n"
                "BUNDLE_PATH=/bundle\nRAILS_MAX_THREADS=2\n"
                "DATABASE_URL=" + db_url + "\n"
                "BABEL_DISABLE_CACHE=1\n")
    save_secret(ENV_RUN, base_env)
    save_secret(ENV_SETUP, base_env + "CAFE_PREVIEW_ADMIN_PASSWORD=" +
                admin_password + "\n")
    save_secret(CRED, "PRIVATE LOCAL PREVIEW ONLY\n"
                "URL: http://127.0.0.1:3003/users/sign_in\n"
                "EMAIL: " + ADMIN_EMAIL + "\nPASSWORD: " + admin_password +
                "\nNEVER post credentials in chat or GitHub.\n")
    execute("docker", "network", "create", "--internal", "--driver", "bridge", NET)
    execute("docker", "volume", "create", PG_VOLUME)
    execute("docker", "run", "-d", "--name", PG, "--network", NET,
            "--network-alias", "rc71-pg", "--env-file", str(ENV_PG),
            "--mount", "type=volume,source=" + PG_VOLUME + ",target=/var/lib/postgresql/data",
            "--restart", "no", DB_IMAGE, timeout=35)
    wait_pg()
    need(sql("SELECT current_database()") == "cafe", "new PG database not cafe")
    print("CAFE RC71 NEW PRIVATE NETWORK / NEW PG CLUSTER PASS", flush=True)

    runner = (
        "set -eu; "
        "bundle exec rails db:schema:load; "
        "bundle exec rails db:seed; "
        "bundle exec rails runner \""
        "raise 'wrong preview target' unless Rails.env.development? && "
        "ActiveRecord::Base.connection.current_database == 'cafe' && "
        "ENV['DATABASE_URL'].to_s.include?('@rc71-pg:5432/cafe'); "
        "User.create!(username: 'PreviewAdmin', email: '" + ADMIN_EMAIL +
        "', admin: true, password: ENV.fetch('CAFE_PREVIEW_ADMIN_PASSWORD'), "
        "password_confirmation: ENV.fetch('CAFE_PREVIEW_ADMIN_PASSWORD'))"
        "\"; "
        "./node_modules/.bin/webpack --config config/webpack/development.js"
    )
    # Keep this one-shot setup container for diagnostics; no automatic cleanup.
    cmd = ["docker", "run", "--name", SETUP, "--env-file", str(ENV_SETUP)]
    cmd += web_common(bundle, node)
    cmd += ["--entrypoint", "sh", IMAGE, "-lc", runner]
    result = execute(*cmd, timeout=250, must=False)
    need(result.returncode == 0,
         "new preview setup failed; inspect only new setup container logs")
    need(sql("SELECT COUNT(*) FROM products") == "20", "new catalogue count differs")
    need(sql("SELECT COUNT(*) FROM categories") == "8", "new category count differs")
    need(sql("SELECT COUNT(*) FROM product_variants") == "18",
         "new drink size count differs")
    need(sql("SELECT COUNT(*) FROM product_modifier_options") == "30",
         "new add-on count differs")
    need(sql("SELECT COUNT(*) FROM users WHERE admin IS TRUE") == "1",
         "new preview administrator count differs")
    need((WORK / "packs" / "manifest.json").is_file(),
         "fresh Webpacker manifest absent")
    print("CAFE RC71 NEW PG SCHEMA / SEEDS / ADMIN / WEBPACK PASS", flush=True)

    cmd = ["docker", "run", "-d", "--name", WEB, "--env-file", str(ENV_RUN)]
    cmd += web_common(bundle, node)
    cmd += ["--publish", "127.0.0.1:3003:3003",
            "--restart", "no", "--entrypoint", "sh", IMAGE,
            "-lc", "bundle exec rails server -b 0.0.0.0 -p 3003"]
    execute(*cmd, timeout=35)
    print("CAFE RC71 NEW LOOPBACK-ONLY WEB CONTAINER STARTED", flush=True)
    print("CAFE RC71 PRIVATE ADMIN CREDENTIALS SAVED LOCALLY — DO NOT SHARE")
    print("CAFE RC71 LAUNCH COMPLETE — RUN --verify NEXT")


def http_status(path):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=6)
    try:
        c.request("GET", path)
        r = c.getresponse()
        r.read(65536)
        return r.status
    except (OSError, TimeoutError):
        return 0
    finally:
        c.close()


def verify():
    stage_valid()
    net = inspect("network", NET)
    pg = inspect("container", PG)
    setup = inspect("container", SETUP)
    web = inspect("container", WEB)
    need(all((net, pg, setup, web)), "one or more new preview objects absent")
    need(net.get("Internal") is True, "new preview network not private")
    need(pg["State"]["Running"] and web["State"]["Running"],
         "new PG/web not running")
    need(set(web["NetworkSettings"]["Networks"]) == {NET} and
         set(pg["NetworkSettings"]["Networks"]) == {NET},
         "new containers connected to unapproved Docker network")
    ports = (web["HostConfig"].get("PortBindings") or {}).get("3003/tcp") or []
    need(len(ports) == 1 and ports[0].get("HostIp") == "127.0.0.1"
         and ports[0].get("HostPort") == "3003",
         "preview port exposed beyond localhost")
    mounts = {m["Destination"]: m for m in web["Mounts"]}
    need(mounts["/app"]["RW"] is False and
         mounts["/app"]["Source"] == str(SOURCE) and
         mounts["/bundle"]["RW"] is False and
         mounts["/app/node_modules"]["RW"] is False,
         "preview source/dependency readonly isolation differs")
    need(sql("SELECT COUNT(*) FROM products") == "20" and
         sql("SELECT COUNT(*) FROM users WHERE admin IS TRUE") == "1" and
         sql("SELECT COUNT(*) FROM orders") == "0",
         "preview database baseline differs")
    statuses = {}
    for _ in range(25):
        statuses = {p: http_status(p) for p in ("/", "/menu", "/cart", "/info")}
        if all(code == 200 for code in statuses.values()):
            break
        time.sleep(1)
    need(all(code == 200 for code in statuses.values()),
         "preview HTTP GET health not PASS — inspect only NEW web logs")
    need(http_status("/demo_checkout") == 302,
         "empty cart checkout should redirect")
    need(http_status("/admin/demo_orders") == 302,
         "guest must be redirected before admin order queue")
    print("CAFE RC71 NEW PG 20 PRODUCTS / 1 ADMIN / ZERO ORDERS PASS")
    print("CAFE RC71 NEW CODE/DEPS RO / ISOLATED NETWORK / PORT 3003 PASS")
    print("CAFE RC71 PUBLIC GET / MENU / CART / INFO HTTP 200 PASS")
    print("CAFE RC71 GUEST CHECKOUT / ADMIN REDIRECT PASS")
    print("CAFE RC71 PREVIEW VERIFIED — BROWSER WRITABLE E2E STILL OPEN")
    print("CAFE RC71 BROWSE: http://127.0.0.1:3003")
    print("CAFE RC71 CREDENTIALS FILE: " + str(CRED))
    print("CAFE RC71 NO ORIGINAL SERVICES, PGs, MEDIA OR CHECKOUT CHANGES")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group(required=True)
    for name in ("check", "stage", "launch", "verify"):
        options.add_argument("--" + name, action="store_true")
    mode = vars(parser.parse_args())
    try:
        for name in ("check", "stage", "launch", "verify"):
            if mode[name]:
                globals()[name]()
                break
    except (Stop, OSError, KeyError, TypeError, ValueError) as error:
        message = str(error)
        if not message.startswith("CAFE RC71 STOP:"):
            message = "CAFE RC71 STOP: stage/operation failed; inspect only preview objects"
        print(message, file=sys.stderr, flush=True)
        print("No retries, forced cleanup, Docker restarts, schema replay or source resets.",
              file=sys.stderr, flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
