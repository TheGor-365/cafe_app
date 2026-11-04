#!/usr/bin/env python3
"""Launch ONLY a separate Rails web for the restored QA security sandbox.

--check: audit original services, distinct PG clusters, sandbox media and mounts;
         verify sandbox web name does not already exist. No changes.
--create: clone known-safe runtime mounts from patched QA, with fresh sandbox
          media and PG URL, but NEVER share QA/live network or secret mounts.
          Create new Rails container WITHOUT HOST PORT, not started.
--smoke: start ONLY sandbox Rails, verify PG cluster, patched CarrierWave 2.2.7,
         uploader restrictions, internal HTTP 200; production still HTTP 200.

Never restarts/stops/destroys existing Rails or DB/volume, changes a proxy,
modifies original app source or private original uploads.
"""
import argparse
import hashlib
from http.client import HTTPConnection
import json
from pathlib import Path
import subprocess
import sys
import time

HOME = Path.home()
PROJECT = HOME / "Рабочий стол/rails_projects/lite/cafe_app"
ROOT = HOME / ".local/share/cafe_app"
WORK = ROOT / "security_bundle_build_20261104"
BUNDLE = ROOT / "bundle_carrierwave_227_20261104"
OVERRIDE = ROOT / "qa_patched_avatar_20261104/avatar_uploader.rb"
MEDIA = ROOT / "uploads_security_sandbox_20261104"
QA_WEB = "cafe-app-patched-qa-candidate-20261104"
NEW_WEB = "cafe-upload-security-sandbox-rails-20261104"
QA_DB = "cafe-upload-qa-pg-20261103"
LIVE_DB = "cafe-app-db"
SANDBOX_DB = "cafe-upload-security-sandbox-pg-20261104"
SANDBOX_NET = "cafe-upload-security-sandbox-20261104"
QA_NET = "cafe-upload-qa-net-20261103"
LIVE_WEB = "cafe-app-local-3001-web"
QA_PROXY = "cafe-upload-qa-proxy-patched-20261104"
IMAGE = "cafe-legacy-full:node14"
SANDBOX_URL = "postgresql://postgres@cafe-app-db:5432/cafe"

# Known original local paths and published Git objects — do not overwrite.
EXPECTED = {
    "Gemfile": "c5fde478cd117c12",
    "Gemfile.lock": "99f86e38d68e203e",
    "app/uploaders/avatar_uploader.rb": "846a9692269fd8d9",
}
UPLOADER_GIT_BLOB = "314c4912610989deed400c5db7db7db20fe1f98a"


def require(ok, reason):
    if not ok:
        raise RuntimeError("SANDBOX RAILS BLOCKED: " + reason)


def run(*args, check=True, capture=True):
    return subprocess.run(args, check=check, text=True,
                          stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                          stderr=subprocess.PIPE if capture else subprocess.DEVNULL)


def docker(*args, **opts):
    return run("docker", *args, **opts)


def inspect(name):
    return json.loads(docker("inspect", name).stdout)[0]


def object_exists(name):
    return docker("container", "inspect", name, check=False).returncode == 0


def pgid(name):
    return docker("exec", "--user", "postgres", name, "psql",
                  "-X", "-At", "-U", "postgres", "-d", "cafe", "-c",
                  "SELECT system_identifier::text FROM pg_control_system();").stdout.strip()


def psql(name, q):
    return docker("exec", "--user", "postgres", name, "psql",
                  "-X", "-At", "-U", "postgres", "-d", "cafe",
                  "-c", q).stdout.strip()


def http(port, path):
    conn = HTTPConnection("127.0.0.1", port, timeout=8)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        body = response.read().decode(errors="replace")
        return response.status, body
    finally:
        conn.close()


def blob_hash(path):
    return run("git", "-C", str(PROJECT), "hash-object", str(path)).stdout.strip()


def manifest_media(path):
    require(path.is_dir() and not path.is_symlink(), "missing private sandbox media")
    count = 0
    for child in path.rglob("*"):
        require(not child.is_symlink(), "sandbox media symlink")
        require(child.is_file() or child.is_dir(), "unsafe sandbox media type")
        if child.is_file():
            count += 1
    return count


def audit():
    require(PROJECT.is_dir(), "original project directory missing")
    require(run("git", "-C", str(PROJECT),
                "branch", "--show-current").stdout.strip() ==
            "feature/cafe-integration-local-20261101",
            "owner Git working branch changed")
    for name, expected in EXPECTED.items():
        path = PROJECT / name
        require(path.is_file() and not path.is_symlink(),
                "missing original file " + name)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(digest.startswith(expected), "original source changed: " + name)
    require(manifest_media(MEDIA) == 10,
            "sandbox restored media count differs from verified snapshot")
    require(OVERRIDE.is_file() and not OVERRIDE.is_symlink(),
            "protected QA uploader override missing")
    require(blob_hash(OVERRIDE) == UPLOADER_GIT_BLOB,
            "QA uploader does not match audited GitHub blob")
    for rel in ("Gemfile", "Gemfile.lock"):
        require((WORK / rel).is_file() and
                not (WORK / rel).is_symlink(),
                "staged patched bundle metadata missing " + rel)
    require("carrierwave (2.2.7)" in (WORK / "Gemfile.lock").read_text(),
            "patched gem lock mismatch")
    require(BUNDLE.is_dir() and not BUNDLE.is_symlink(), "patched bundle missing")

    source = inspect(QA_WEB)
    sandbox_db = inspect(SANDBOX_DB)
    live = inspect(LIVE_WEB)
    live_db = inspect(LIVE_DB)
    qa_db = inspect(QA_DB)
    qa_proxy = inspect(QA_PROXY)
    for n, x in [(QA_WEB, source), (SANDBOX_DB, sandbox_db),
                 (LIVE_WEB, live), (LIVE_DB, live_db),
                 (QA_DB, qa_db), (QA_PROXY, qa_proxy)]:
        require(x["State"]["Status"] == "running",
                "existing container not running: " + n)
    nets = lambda c: set(c["NetworkSettings"]["Networks"])
    require(nets(source) == {QA_NET}, "patched QA web network changed")
    require(nets(qa_db) == {QA_NET}, "QA DB network changed")
    require(nets(sandbox_db) == {SANDBOX_NET},
            "sandbox DB connected to unexpected network")
    require(SANDBOX_NET not in nets(live) and
            SANDBOX_NET not in nets(live_db) and
            SANDBOX_NET not in nets(source) and
            QA_NET not in nets(sandbox_db),
            "isolation between sandbox, QA and live broken")
    details = json.loads(
        docker("network", "inspect", SANDBOX_NET).stdout)[0]
    require(details["Internal"] is True,
            "sandbox Docker network is not internal")
    require(not sandbox_db["HostConfig"]["PortBindings"],
            "sandbox PG has a host-published port")
    require(source["Config"]["Image"] == IMAGE and
            source["Config"]["User"] == "1000:1000",
            "patched QA runtime user/image changed")
    require(source["HostConfig"]["ReadonlyRootfs"],
            "patched QA root is writable")
    require(not source["HostConfig"]["PortBindings"],
            "patched QA has a host port")
    mounts = {m["Destination"]: m for m in source["Mounts"]}
    require(mounts["/app"]["Source"] == str(PROJECT) and
            not mounts["/app"]["RW"],
            "patched QA project source mount changed")
    require(mounts["/bundle"]["Source"] == str(BUNDLE) and
            not mounts["/bundle"]["RW"],
            "patched QA bundle mount differs")
    require(mounts["/app/app/uploaders/avatar_uploader.rb"]["Source"] ==
            str(OVERRIDE) and
            not mounts["/app/app/uploaders/avatar_uploader.rb"]["RW"],
            "patched uploader override differs")
    require(mounts["/app/Gemfile"]["Source"] == str(WORK / "Gemfile"),
            "patched Gemfile differs")
    require(mounts["/app/Gemfile.lock"]["Source"] ==
            str(WORK / "Gemfile.lock"),
            "patched lockfile differs")
    for dest, mount in mounts.items():
        require(not mount["RW"] or dest == "/app/public/uploads",
                "unexpected RW source mount " + dest)

    clusters = {n: pgid(n) for n in (LIVE_DB, QA_DB, SANDBOX_DB)}
    require(len(set(clusters.values())) == 3 and
            all(x.isdigit() for x in clusters.values()),
            "sandbox, QA, live PostgreSQL not distinct")
    require(psql(SANDBOX_DB,
                 "SELECT COUNT(*), COUNT(*) FILTER (WHERE id=21) FROM products;") ==
            "20|0", "sandbox products differ from snapshot")
    require(http(3001, "/info")[0] == 200 and
            http(3002, "/menu")[0] == 200,
            "existing public loopback health failed")
    print("SANDBOX QA/LIVE NETWORK AND POSTGRES ISOLATION PASS", flush=True)
    print("RESTORED SANDBOX MEDIA: 10 FILES", flush=True)
    print("PATCHED CARRIERWAVE BUNDLE AND ORIGINAL SOURCE PASS", flush=True)
    print("EXISTING PORTS 3001/3002 HTTP 200", flush=True)
    print("SANDBOX RAILS PREFLIGHT PASS", flush=True)
    return source, clusters


def mount_specs(source):
    """Translate *audited* read-only QA mount graph, omitting live secrets."""
    mounts = {m["Destination"]: m for m in source["Mounts"]}
    specs = []
    excluded = {"/run/secrets/cafe_pg_password"}
    require("/run/secrets/cafe_pg_password" in mounts,
            "expected secret mount absent, review config")
    for dest, m in sorted(mounts.items(), key=lambda x: x[0].count("/")):
        if dest in excluded:
            continue
        if dest == "/app/public/uploads":
            spec = "type=bind,source={},target={}".format(MEDIA, dest)
        elif m["Type"] == "volume":
            require(m["Name"], "volume without name at " + dest)
            spec = "type=volume,source={},target={}".format(m["Name"], dest)
            require(not m["RW"], "shared volume cannot be writable")
            spec += ",readonly"
        elif m["Type"] == "bind":
            require(not m["RW"], "shared bind cannot be writable")
            spec = "type=bind,source={},target={},readonly".format(
                m["Source"], dest)
        else:
            raise RuntimeError("unsupported QA mount type at " + dest)
        specs.extend(["--mount", spec])

    require(any("target=/app/public/uploads" in s and
                "readonly" not in s for s in specs),
            "sandbox uploads are not writable")
    return specs


def environ(source):
    entries = {}
    for entry in source["Config"]["Env"]:
        k, mark, v = entry.partition("=")
        require(mark == "=" and k not in entries,
                "invalid / duplicate QA environment key")
        entries[k] = v
    require(entries.get("DATABASE_URL") ==
            "postgresql://postgres@cafe-app-db:5432/cafe",
            "patched QA DATABASE_URL unexpected")
    # Refuse actual secret/token variables rather than accidentally forwarding.
    for key in entries:
        require(not any(x in key.upper() for x in (
            "PASSWORD", "SECRET", "TOKEN", "CREDENTIAL", "API_KEY")),
            "unexpected secret-like environment variable: " + key)
    entries["DATABASE_URL"] = SANDBOX_URL
    entries["BUNDLE_GEMFILE"] = "/app/Gemfile"
    require(entries.get("RAILS_ENV") == "development",
            "Rails sandbox must use development environment")
    result = []
    for name in sorted(entries):
        result.extend(["--env", name + "=" + entries[name]])
    return result


def create():
    source, _ = audit()
    require(not object_exists(NEW_WEB),
            "sandbox Rails container already exists, do not recreate")
    host = source["HostConfig"]
    args = [
        "create", "--name", NEW_WEB,
        "--network", SANDBOX_NET,
        "--read-only", "--user", "1000:1000",
        "--workdir", "/app", "--memory", "1024m",
        "--pids-limit", "256", "--restart", "no",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges"
    ]
    for path, options in (host.get("Tmpfs") or {}).items():
        args += ["--tmpfs", path + (":" + options if options else "")]
    require(set(host.get("Tmpfs") or {}) >=
            {"/app/log", "/app/tmp", "/tmp"},
            "sandbox missing protected runtime tmpfs mounts")
    args += environ(source)
    args += mount_specs(source)
    args += ["--entrypoint", "sh", IMAGE,
             "-lc", "bundle exec rails server -b 0.0.0.0 -p 3001"]
    docker(*args)

    candidate = inspect(NEW_WEB)
    require(candidate["State"]["Status"] == "created",
            "new Rails unexpectedly started")
    require(set(candidate["NetworkSettings"]["Networks"]) == {SANDBOX_NET},
            "sandbox Rails has a network outside sandbox")
    require(not candidate["HostConfig"]["PortBindings"],
            "sandbox Rails publishes a host port")
    require(candidate["HostConfig"]["ReadonlyRootfs"],
            "sandbox Rails root not readonly")
    new_mounts = {m["Destination"]: m for m in candidate["Mounts"]}
    require(new_mounts["/app/public/uploads"]["Source"] == str(MEDIA) and
            new_mounts["/app/public/uploads"]["RW"],
            "sandbox Rails uploads are not correctly scoped")
    require(not new_mounts["/app"]["RW"],
            "sandbox Rails application source writable")
    require("/run/secrets/cafe_pg_password" not in new_mounts,
            "live secret mounted into sandbox")
    print("SANDBOX RAILS CREATED — NOT STARTED, NO HOST PORT", flush=True)
    print("NO PROD / QA DOCKER OR DATABASE CHANGES", flush=True)


def smoke():
    _, clusters = audit()
    require(object_exists(NEW_WEB),
            "sandbox Rails missing; run --create first")
    candidate = inspect(NEW_WEB)
    require(candidate["State"]["Status"] in {"created", "running"},
            "unexpected sandbox Rails state")
    require(set(candidate["NetworkSettings"]["Networks"]) == {SANDBOX_NET},
            "sandbox Rails network isolation failed")
    require(not candidate["HostConfig"]["PortBindings"],
            "sandbox Rails unexpectedly publishes ports")
    mounts = {m["Destination"]: m for m in candidate["Mounts"]}
    require(mounts["/app/public/uploads"]["Source"] == str(MEDIA) and
            mounts["/app/public/uploads"]["RW"], "sandbox media mount mismatch")
    require("/run/secrets/cafe_pg_password" not in mounts,
            "unexpected secret bind in sandbox")
    if candidate["State"]["Status"] == "created":
        docker("start", NEW_WEB)
    require(inspect(NEW_WEB)["State"]["Status"] == "running",
            "new sandbox Rails didn't start")

    verify = (
        "id=ActiveRecord::Base.connection.select_value("
        "'SELECT system_identifier::text FROM pg_control_system()').to_s; "
        "raise 'Not sandbox PG' unless id==ENV.fetch('EXPECTED_SANDBOX_ID'); "
        "require 'carrierwave'; "
        "raise 'Wrong gem version' unless "
        "Gem.loaded_specs.fetch('carrierwave').version.to_s=='2.2.7'; "
        "u=AvatarUploader.new; "
        "raise 'Uploader policy missing' unless "
        "u.extension_allowlist==%w(jpg jpeg png gif) && "
        "u.size_range.max==2097152 && "
        "u.content_type_allowlist.first.match('image/png'); "
        "raise 'Wrong catalog' unless Product.count==20; "
        "puts 'SANDBOX RAILS SQL/CARRIERWAVE POLICY PASS'"
    )
    result = docker("exec", "--env",
                    "EXPECTED_SANDBOX_ID=" + clusters[SANDBOX_DB],
                    NEW_WEB, "bundle", "exec", "rails", "runner", verify)
    print(result.stdout.strip(), flush=True)

    ready = False
    for _ in range(30):
        ruby = (
            "require 'net/http'; "
            "r=Net::HTTP.start('127.0.0.1',3001,"
            "open_timeout:2,read_timeout:6) {|h| h.get('/users/sign_up')}; "
            "raise 'Wrong form HTTP' unless r.code=='200'; "
            "raise 'No avatar input' unless r.body.include?('name=\"user[avatar]\"'); "
            "raise 'No multipart form' unless r.body.include?('multipart/form-data'); "
            "puts 'SANDBOX INTERNAL SIGNUP HTML 200 PASS'"
        )
        test = docker("exec", NEW_WEB, "ruby", "-rlogger", "-e", ruby,
                      check=False)
        if test.returncode == 0:
            print(test.stdout.strip(), flush=True)
            ready = True
            break
        time.sleep(1)
    require(ready, "sandbox internal HTTP readiness failed")
    require(http(3001, "/info")[0] == 200 and
            http(3002, "/menu")[0] == 200,
            "original active ports changed")

    print("PRODUCTION 3001 / QA 3002 HTTP 200", flush=True)
    print("SANDBOX RAILS READY — ONLY INTERNAL NETWORK", flush=True)
    print("NO MULTIPART UPLOAD TESTS PERFORMED", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--create", action="store_true")
    modes.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    try:
        if args.check:
            audit()
            require(not object_exists(NEW_WEB), "sandbox web already exists")
            print("SANDBOX RAILS CHECK COMPLETE — NO CHANGES", flush=True)
        elif args.create:
            create()
        else:
            smoke()
    except Exception as e:
        print("SANDBOX RAILS STOPPED:",
              type(e).__name__, str(e)[:350], file=sys.stderr)
        print("Do not recreate/overwrite resources after failure; "
              "diagnose separately.", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
