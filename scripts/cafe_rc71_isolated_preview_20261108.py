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
import hashlib
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
DEPS = WORK / "dependencies"
DEVISE = DEPS / "devise"
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
ACCESS_NET = "cafe-rc71-access-net-20261108"
PG_VOLUME = "cafe-rc71-pgdata-20261108"
BUNDLE_VOLUME = "cafe-rc71-bundle-20261108"
PG = "cafe-rc71-pg-20261108"
BUNDLE_SEED = "cafe-rc71-bundle-seed-20261108"
BUNDLE_SETUP = "cafe-rc71-bundle-setup-20261108"
SETUP = "cafe-rc71-setup-20261108"
WEB = "cafe-rc71-web-20261108"
PROXY = "cafe-rc71-proxy-20261108"
PORT = 3003
ADMIN_EMAIL = "preview-admin@example.test"
DEVISE_REPO = "https://github.com/heartcombo/devise.git"
DEVISE_BRANCH = "ca-omniauth-2"
DEVISE_REVISION = "e16d60d0fedc5f5e6f541b2b9e901a2d53f8ceda"
ENV_RUN = WORK / "preview-web.env"
ENV_SETUP = WORK / "preview-setup.env"
ENV_PG = WORK / "preview-postgres.env"
CRED = WORK / "preview-admin-local-only.txt"
RUNTIME_LOCK = WORK / "Gemfile.preview.lock"
BUNDLE_MARKER = WORK / "bundle.json"
SOURCE_MOUNTPOINTS = ("node_modules", "public/packs", "public/uploads", "tmp", "log")


class Stop(RuntimeError):
    pass


def need(condition, reason):
    if not condition:
        raise Stop("CAFE RC71 STOP: " + reason)


def execute(*args, timeout=30, must=True):
    command_name = " ".join(str(value) for value in args[:2])
    try:
        r = subprocess.run(list(args), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise Stop("CAFE RC71 STOP: command unavailable or timed out: " + command_name)
    if must:
        need(r.returncode == 0,
             "command failed (" + command_name + "); preserve state for diagnosis")
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


def git_clean(path):
    status = execute("git", "-C", str(path), "status", "--porcelain=v1",
                     "--untracked-files=all").stdout.decode()
    return status == ""


def git_remote(path):
    return execute("git", "-C", str(path), "remote", "get-url", "origin").stdout.decode().strip()


def image_id(value):
    need(isinstance(value, str) and value.startswith("sha256:") and
         len(value) == 71 and all(char in "0123456789abcdef" for char in value[7:]),
         "Docker image identity is not an immutable sha256 ID")
    return value


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def runtime_lock_valid():
    need(RUNTIME_LOCK.is_file() and not RUNTIME_LOCK.is_symlink() and
         RUNTIME_LOCK.stat().st_uid == os.getuid() and
         stat.S_IMODE(RUNTIME_LOCK.stat().st_mode) == 0o600,
         "private runtime lockfile permissions differ")
    content = RUNTIME_LOCK.read_text()
    need(DEVISE_REVISION in content and "rails (6.0.3.6)" in content,
         "private runtime lockfile lost pinned dependencies")
    if BUNDLE_MARKER.exists():
        try:
            marker = json.loads(BUNDLE_MARKER.read_text())
        except (OSError, ValueError):
            raise Stop("CAFE RC71 STOP: private bundle marker invalid")
        need(marker.get("runtime_lock_sha256") == file_sha256(RUNTIME_LOCK),
             "private runtime lockfile changed after bundle preparation")
    else:
        need(file_sha256(RUNTIME_LOCK) == file_sha256(SOURCE / "Gemfile.lock"),
             "pre-build private runtime lockfile differs from pinned source")


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
    need(db["Config"]["Image"] == DB_IMAGE and db["State"]["Running"],
         "original PostgreSQL image or running status differs")
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
    return (mounts["/bundle"]["Name"], mounts["/app/node_modules"]["Name"],
            image_id(live["Image"]), image_id(db["Image"]))


def objects_absent():
    for kind, obj in (("network", NET), ("network", ACCESS_NET),
                      ("volume", PG_VOLUME),
                      ("volume", BUNDLE_VOLUME),
                      ("container", PG), ("container", BUNDLE_SEED),
                      ("container", BUNDLE_SETUP), ("container", SETUP),
                      ("container", WEB), ("container", PROXY)):
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
    # Docker cannot create nested mountpoints below the readonly /app bind.
    # Empty directories do not change the pinned Git tree and remain untracked.
    for folder in SOURCE_MOUNTPOINTS:
        (SOURCE / folder).mkdir(parents=True, exist_ok=True)
    need(git_clean(SOURCE), "mountpoint preparation changed pinned source content")
    DEPS.mkdir(mode=0o700)
    execute("git", "init", "--quiet", str(DEVISE))
    execute("git", "-C", str(DEVISE), "remote", "add", "origin", DEVISE_REPO)
    result = execute("git", "-C", str(DEVISE), "fetch", "--quiet", "--depth", "1",
                     "origin", DEVISE_REVISION, timeout=180, must=False)
    need(result.returncode == 0, "pinned Devise dependency fetch failed; preserve stage")
    execute("git", "-C", str(DEVISE), "checkout", "--quiet", "-b",
            DEVISE_BRANCH, "FETCH_HEAD")
    need(git_head(DEVISE) == DEVISE_REVISION and git_clean(DEVISE),
         "pinned Devise dependency differs")
    for folder in ("tmp", "tmp/pids", "log", "packs", "uploads"):
        (WORK / folder).mkdir(parents=True, exist_ok=True, mode=0o700)
    RUNTIME_LOCK.write_bytes((SOURCE / "Gemfile.lock").read_bytes())
    os.chmod(RUNTIME_LOCK, 0o600)
    (WORK / "stage.json").write_text(json.dumps(
        {"expected_head": EXPECTED_HEAD, "source_branch": SOURCE_BRANCH}) + "\n")
    print("CAFE RC71 PRIVATE IMMUTABLE SOURCE CHECKOUT PASS")
    print("CAFE RC71 STAGING PASS — NO DOCKER OR DATABASE CHANGES")


def stage_valid():
    baseline = local_baseline()
    need(WORK.is_dir() and not WORK.is_symlink(), "private preview stage absent")
    need(WORK.stat().st_uid == os.getuid() and
         (stat.S_IMODE(WORK.stat().st_mode) & 0o077) == 0,
         "preview stage permissions unsafe")
    need(SOURCE.is_dir() and not SOURCE.is_symlink(), "private Git clone absent")
    need(git_head(SOURCE) == EXPECTED_HEAD,
         "pinned private source changed")
    need(git_clean(SOURCE), "pinned private source has tracked or untracked changes")
    for folder in SOURCE_MOUNTPOINTS:
        mountpoint = SOURCE / folder
        need(mountpoint.is_dir() and not mountpoint.is_symlink(),
             "required readonly source mountpoint missing: " + folder)
    need(DEVISE.is_dir() and not DEVISE.is_symlink() and
         git_head(DEVISE) == DEVISE_REVISION and git_clean(DEVISE) and
         git_remote(DEVISE) == DEVISE_REPO,
         "pinned local Devise dependency differs")
    runtime_lock_valid()
    try:
        marker = json.loads((WORK / "stage.json").read_text())
    except (OSError, ValueError):
        raise Stop("CAFE RC71 STOP: stage marker absent or invalid")
    need(marker.get("expected_head") == EXPECTED_HEAD, "stage marker SHA differs")
    need(marker.get("source_branch") == SOURCE_BRANCH, "stage marker branch differs")
    return baseline


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
        "type=bind,source=" + str(DEVISE) + ",target=/vendor/devise,readonly",
        "type=bind,source=" + str(RUNTIME_LOCK) +
        ",target=/app/Gemfile.lock,readonly",
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


def pg_run_command(db_image):
    return [
        "docker", "run", "--pull=never", "-d", "--name", PG,
        "--network", NET, "--network-alias", "rc71-pg",
        "--env-file", str(ENV_PG),
        "--mount", "type=volume,source=" + PG_VOLUME +
        ",target=/var/lib/postgresql/data",
        "--restart", "no", image_id(db_image)
    ]


def bundle_seed_command(source_bundle, web_image):
    return [
        "docker", "run", "--pull=never", "--name", BUNDLE_SEED,
        "--network", "none", "--read-only",
        "--tmpfs", "/tmp:rw,size=64m,mode=1777",
        "--cap-drop", "ALL", "--cap-add", "CHOWN",
        "--security-opt", "no-new-privileges",
        "--mount", "type=volume,source=" + source_bundle +
        ",target=/source-bundle,readonly",
        "--mount", "type=volume,source=" + BUNDLE_VOLUME + ",target=/bundle",
        "--entrypoint", "sh", image_id(web_image), "-lc",
        "cp -a /source-bundle/. /bundle/ && chown -R 1000:1000 /bundle"
    ]


def bundle_setup_command(web_image):
    return [
        "docker", "run", "--pull=never", "--name", BUNDLE_SETUP,
        "--user", "1000:1000", "--workdir", "/app", "--read-only",
        "--tmpfs", "/tmp:rw,size=128m,mode=1777",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--pids-limit", "180",
        "--mount", "type=bind,source=" + str(SOURCE) + ",target=/app,readonly",
        "--mount", "type=volume,source=" + BUNDLE_VOLUME + ",target=/bundle",
        "--mount", "type=bind,source=" + str(DEVISE) +
        ",target=/vendor/devise,readonly",
        "--mount", "type=bind,source=" + str(RUNTIME_LOCK) +
        ",target=/app/Gemfile.lock",
        "--env", "BUNDLE_PATH=/bundle",
        "--env", "BUNDLE_LOCAL__DEVISE=/vendor/devise",
        "--env", "BUNDLE_APP_CONFIG=/tmp/bundle-config",
        "--env", "BUNDLE_FROZEN=false",
        "--env", "RUBYOPT=-rlogger",
        "--entrypoint", "sh", image_id(web_image), "-lc",
        "bundle lock --add-platform x86_64-linux && "
        "bundle install --jobs 2 --retry 2 && bundle check"
    ]


def setup_run_command(bundle, node, web_image, runner):
    command = ["docker", "run", "--pull=never", "--name", SETUP,
               "--env-file", str(ENV_SETUP)]
    command += web_common(bundle, node)
    command += ["--entrypoint", "sh", image_id(web_image), "-lc", runner]
    return command


def web_run_command(bundle, node, web_image):
    command = ["docker", "run", "--pull=never", "-d", "--name", WEB,
               "--env-file", str(ENV_RUN)]
    command += web_common(bundle, node)
    command += ["--network-alias", "rc71-web", "--restart", "no",
                "--entrypoint", "sh", image_id(web_image), "-lc",
                "bundle exec rails server -b 0.0.0.0 -p 3003"]
    return command


def proxy_run_command(web_image):
    proxy = (
        "const net=require('net');"
        "const server=net.createServer(client=>{"
        "const upstream=net.connect(3003,'rc71-web');"
        "client.pipe(upstream);upstream.pipe(client);"
        "const close=()=>{client.destroy();upstream.destroy()};"
        "client.on('error',close);upstream.on('error',close);});"
        "server.listen(3003,'0.0.0.0');"
    )
    return [
        "docker", "run", "--pull=never", "-d", "--name", PROXY,
        "--network", ACCESS_NET,
        "--publish", "127.0.0.1:3003:3003",
        "--read-only", "--tmpfs", "/tmp:rw,size=32m,mode=1777",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--pids-limit", "64", "--restart", "no",
        "--entrypoint", "node", image_id(web_image), "-e", proxy
    ]


def wait_pg():
    last_start = None
    stable_successes = 0
    for _ in range(60):
        # pg_isready can succeed against the temporary postmaster used by the
        # official image before POSTGRES_DB exists. Require two SQL successes
        # from the same final postmaster instead.
        r = execute("docker", "exec", PG, "psql", "-X", "-At", "-v",
                    "ON_ERROR_STOP=1", "-U", "postgres", "-d", "cafe", "-c",
                    "SELECT current_database() || '|' || pg_postmaster_start_time()",
                    timeout=8, must=False)
        value = r.stdout.decode().strip() if r.returncode == 0 else ""
        if value.startswith("cafe|"):
            start = value.split("|", 1)[1]
            stable_successes = stable_successes + 1 if start == last_start else 1
            last_start = start
            if stable_successes >= 2:
                return
        else:
            stable_successes = 0
            last_start = None
        time.sleep(1)
    raise Stop("CAFE RC71 STOP: new preview PG did not reach stable SQL readiness")


def sql(query):
    r = execute("docker", "exec", PG, "psql", "-X", "-At", "-v",
                "ON_ERROR_STOP=1", "-U", "postgres", "-d", "cafe",
                "-c", query, timeout=20)
    return r.stdout.decode().strip()


def launch():
    source_bundle, node, web_image, db_image = stage_valid()
    objects_absent()
    for dest in ("tmp", "tmp/pids", "log", "packs", "uploads"):
        need((WORK / dest).is_dir() and not (WORK / dest).is_symlink(),
             "preview scratch directory changed")
    execute("docker", "volume", "create", BUNDLE_VOLUME)
    result = execute(*bundle_seed_command(source_bundle, web_image),
                     timeout=300, must=False)
    need(result.returncode == 0,
         "private bundle seed failed; inspect only new bundle seed container logs")
    result = execute(*bundle_setup_command(web_image), timeout=600, must=False)
    need(result.returncode == 0,
         "private bundle install failed; inspect only new bundle setup container logs")
    BUNDLE_MARKER.write_text(json.dumps(
        {"runtime_lock_sha256": file_sha256(RUNTIME_LOCK)}) + "\n")
    os.chmod(BUNDLE_MARKER, 0o600)
    bundle = BUNDLE_VOLUME
    print("CAFE RC71 PRIVATE PINNED BUNDLE PREPARED; SHARED BUNDLE UNCHANGED",
          flush=True)
    os.umask(0o077)
    password = secrets.token_hex(24)
    admin_password = secrets.token_urlsafe(24)
    db_url = "postgresql://postgres:" + password + "@rc71-pg:5432/cafe"
    save_secret(ENV_PG, "POSTGRES_USER=postgres\nPOSTGRES_DB=cafe\nPOSTGRES_PASSWORD=" +
                password + "\nPOSTGRES_HOST_AUTH_METHOD=scram-sha-256\n")
    base_env = ("RAILS_ENV=development\nNODE_ENV=development\nRUBYOPT=-rlogger\n"
                "BUNDLE_PATH=/bundle\nBUNDLE_LOCAL__DEVISE=/vendor/devise\n"
                "BUNDLE_FROZEN=true\n"
                "RAILS_MAX_THREADS=2\n"
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
    execute("docker", "network", "create", "--driver", "bridge", ACCESS_NET)
    execute("docker", "volume", "create", PG_VOLUME)
    execute(*pg_run_command(db_image), timeout=35)
    wait_pg()
    need(sql("SELECT current_database()") == "cafe", "new PG database not cafe")
    print("CAFE RC71 NEW PRIVATE NETWORK / NEW PG CLUSTER PASS", flush=True)

    runner = (
        "set -eu; "
        "bundle exec rails runner \""
        "raise 'wrong preview target' unless Rails.env.development? && "
        "ActiveRecord::Base.connection.current_database == 'cafe' && "
        "ENV['DATABASE_URL'].to_s.include?('@rc71-pg:5432/cafe'); "
        "load Rails.root.join('db/schema.rb')"
        "\"; "
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
    cmd = setup_run_command(bundle, node, web_image, runner)
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

    cmd = web_run_command(bundle, node, web_image)
    execute(*cmd, timeout=35)
    execute(*proxy_run_command(web_image), timeout=35)
    execute("docker", "network", "connect", NET, PROXY, timeout=35)
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
    _, _, web_image, db_image = stage_valid()
    net = inspect("network", NET)
    access_net = inspect("network", ACCESS_NET)
    bundle_volume = inspect("volume", BUNDLE_VOLUME)
    bundle_seed = inspect("container", BUNDLE_SEED)
    bundle_setup = inspect("container", BUNDLE_SETUP)
    pg = inspect("container", PG)
    setup = inspect("container", SETUP)
    web = inspect("container", WEB)
    proxy = inspect("container", PROXY)
    need(all((net, access_net, bundle_volume, bundle_seed, bundle_setup,
              pg, setup, web, proxy)),
         "one or more new preview objects absent")
    need(net.get("Internal") is True, "new preview network not private")
    need(access_net.get("Internal") is False,
         "new loopback access network unexpectedly internal")
    need(pg["State"]["Running"] and web["State"]["Running"] and
         proxy["State"]["Running"], "new PG/web/proxy not running")
    need(bundle_seed["State"]["ExitCode"] == 0 and
         bundle_setup["State"]["ExitCode"] == 0 and
         setup["State"]["ExitCode"] == 0,
         "one or more one-shot setup containers did not exit successfully")
    need(pg["Image"] == db_image and web["Image"] == web_image,
         "preview containers are not pinned to reviewed immutable image IDs")
    need(set(web["NetworkSettings"]["Networks"]) == {NET} and
         set(pg["NetworkSettings"]["Networks"]) == {NET},
         "new containers connected to unapproved Docker network")
    need(not (web["HostConfig"].get("PortBindings") or {}),
         "Rails web must not publish a host port directly")
    need(set(proxy["NetworkSettings"]["Networks"]) == {NET, ACCESS_NET},
         "loopback proxy network isolation differs")
    ports = (proxy["HostConfig"].get("PortBindings") or {}).get("3003/tcp") or []
    need(len(ports) == 1 and ports[0].get("HostIp") == "127.0.0.1"
         and ports[0].get("HostPort") == "3003",
         "preview port exposed beyond localhost")
    need(not proxy["Mounts"] and proxy["HostConfig"].get("ReadonlyRootfs") is True and
         proxy["HostConfig"].get("CapDrop") == ["ALL"],
         "loopback proxy gained mounts or write/capability access")
    mounts = {m["Destination"]: m for m in web["Mounts"]}
    need(mounts["/app"]["RW"] is False and
         mounts["/app"]["Source"] == str(SOURCE) and
         mounts["/bundle"]["RW"] is False and
         mounts["/bundle"].get("Name") == BUNDLE_VOLUME and
         mounts["/app/node_modules"]["RW"] is False,
         "preview source/dependency readonly isolation differs")
    need(web["HostConfig"].get("ReadonlyRootfs") is True and
         web["HostConfig"].get("CapDrop") == ["ALL"] and
         web["HostConfig"].get("SecurityOpt") == ["no-new-privileges"],
         "preview container hardening differs")
    for private_file in (ENV_PG, ENV_RUN, ENV_SETUP, CRED):
        need(private_file.is_file() and not private_file.is_symlink() and
             private_file.stat().st_uid == os.getuid() and
             stat.S_IMODE(private_file.stat().st_mode) == 0o600,
             "preview credential file permissions differ")
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
