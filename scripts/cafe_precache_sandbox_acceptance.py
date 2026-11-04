#!/usr/bin/env python3
"""Second (separate) sandbox Rails candidate for QA avatar pre-cache policy.

--check  : read-only; verifies original 10 sandbox media bytes, 3 PG clusters,
           active QA/live ports, exact existing sandbox web, new uploader blob.
--create : creates but DOES NOT START a separate read-only Rails container
           with a NEW reviewed uploader bind. No published ports or network
           outside existing internal sandbox.
--smoke  : starts ONLY the new sandbox Rails and checks real sandbox PG,
           CarrierWave 2.2.7 and internal HTML.
--test   : invokes existing SHA-pinned Ruby real HTTP multipart security suite
           INSIDE the new sandbox container. All writes are sandbox only.

Never changes /app source, current QA uploader overlay, original backups,
active port 3001/3002, live or QA databases, existing Rails/PG containers.
Does not remove existing resources or run migrations/seeds.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path.home() / ".local/share/cafe_app"
ORIGINAL_LAUNCH = ROOT / "cafe_sandbox_rails_20261104.py"
ORIGINAL_LAUNCH_BLOB = "09089ae4823c42e61ac4ac270348eb2b386838a1"
FORENSICS_SCRIPT = ROOT / "cafe_sandbox_media_forensics_20261104.py"
FORENSICS_BLOB = "250587d9fd767131b0afdaf2e9c2e14df0a6fcb8"
RUBY_PROBE = ROOT / "cafe_sandbox_multipart_probe_20261104.rb"
RUBY_PROBE_BLOB = "750cad1022099dd6d9d632908a0a8fa4276e356f"
NEW_UPLOADER = ROOT / "cafe_avatar_precache_qa_20261104.rb"
NEW_UPLOADER_BLOB = "4800d9324417a1e2c262270781782e8a87a8bd22"
CURRENT = "cafe-upload-security-sandbox-rails-20261104"
NEW = "cafe-upload-security-sandbox-precache-20261104"
NETWORK = "cafe-upload-security-sandbox-20261104"
MEDIA_DEST = "/app/public/uploads"
UPLOAD_DEST = "/app/app/uploaders/avatar_uploader.rb"


def gate(condition, why):
    if not condition:
        raise RuntimeError("PRECACHE SANDBOX BLOCKED: " + why)


def checked_blob(path, sha):
    gate(path.is_file() and not path.is_symlink(),
         "reviewed helper missing or symlink: " + path.name)
    result = subprocess.run(
        ["git", "hash-object", str(path)], capture_output=True, text=True, check=True
    )
    gate(result.stdout.strip() == sha, "Git blob changed: " + path.name)


def module(path, sha, name):
    checked_blob(path, sha)
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def docker(*args, check=True):
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=check
    )


def audit():
    l = module(ORIGINAL_LAUNCH, ORIGINAL_LAUNCH_BLOB, "cafe_sandbox_launch")
    f = module(FORENSICS_SCRIPT, FORENSICS_BLOB, "cafe_sandbox_forensics")
    l.audit()  # refuses wrong source/PG/QA network/ports/uploads
    f.verify_environment()
    baseline = f.verified_archive()
    current = f.current_files()
    gate(baseline == current and len(current) == 10,
         "sandbox media not reset to exact 10-file private backup")
    gate(f.sql(f.SANDBOX_DB, "SELECT COUNT(*) FROM users;") == "2",
         "sandbox users no longer match original restored database")
    gate(f.sql(f.SANDBOX_DB, """
        SELECT COUNT(*) FILTER (WHERE email LIKE 'accept-%@example.test'),
               COUNT(*) FILTER (WHERE email LIKE 'reject-%@example.test')
        FROM users;
    """) == "0|0", "sandbox has residual generated users")
    checked_blob(NEW_UPLOADER, NEW_UPLOADER_BLOB)
    old = l.inspect(CURRENT)
    gate(old["State"]["Status"] == "running", "old sandbox Rails changed")
    gate(old["HostConfig"]["ReadonlyRootfs"], "old sandbox root writable")
    gate(set(old["NetworkSettings"]["Networks"]) == {NETWORK},
         "old sandbox network changed")
    gate(not old["HostConfig"]["PortBindings"], "old sandbox has public port")
    mounts = {m["Destination"]: m for m in old["Mounts"]}
    gate(mounts[MEDIA_DEST]["Source"] == str(l.MEDIA) and
         mounts[MEDIA_DEST]["RW"], "old sandbox media mount changed")
    gate(mounts[UPLOAD_DEST]["Source"] == str(l.OVERRIDE) and
         not mounts[UPLOAD_DEST]["RW"], "old sandbox uploader changed")
    gate(not mounts["/app"]["RW"], "owner application source writable")
    gate("/run/secrets/cafe_pg_password" not in mounts,
         "unexpected secret mount in existing sandbox")
    env = dict(x.split("=", 1) for x in old["Config"]["Env"])
    gate(env["DATABASE_URL"] == l.SANDBOX_URL and
         env["BUNDLE_GEMFILE"] == "/app/Gemfile",
         "existing sandbox app database/bundle settings changed")
    gate(not any(word in key.upper() for key in env for word in
                 ("TOKEN", "PASSWORD", "SECRET", "API_KEY", "CREDENTIAL")),
         "sandbox has secret-like environment key")
    print("CLEAN 10-FILE SANDBOX MEDIA BASELINE PASS", flush=True)
    print("PRECACHE CANDIDATE SHA AND INTERNAL PG NETWORK PASS", flush=True)
    print("HOST 3001 AND 3002 STILL HTTP 200", flush=True)
    return l, f, old


def create():
    l, f, old = audit()
    gate(not l.object_exists(NEW),
         "new candidate already exists — never overwrite or retry blindly")
    host, config = old["HostConfig"], old["Config"]
    gate(config["Image"] == l.IMAGE and config["User"] == "1000:1000",
         "unexpected original sandbox image/user")
    gate(config.get("Entrypoint") == ["sh"], "sandbox ENTRYPOINT changed")
    gate(config.get("Cmd") == [
        "-lc", "bundle exec rails server -b 0.0.0.0 -p 3001"
    ], "sandbox Rails command changed")
    args = [
        "create", "--name", NEW, "--network", NETWORK,
        "--read-only", "--user", "1000:1000", "--workdir", "/app",
        "--memory", "1024m", "--pids-limit", "256", "--restart", "no",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges"
    ]
    for key in config["Env"]:
        args += ["--env", key]
    tmpfs = host.get("Tmpfs") or {}
    gate(set(tmpfs) >= {"/app/log", "/app/tmp", "/tmp"},
         "sandbox runtime tmpfs mounts unexpectedly missing")
    for path, options in tmpfs.items():
        args += ["--tmpfs", path + (":" + options if options else "")]
    old_mounts = {m["Destination"]: m for m in old["Mounts"]}
    for dest, m in sorted(old_mounts.items(), key=lambda e: e[0].count("/")):
        gate(m["Type"] in ("bind", "volume"), "unexpected Docker mount type")
        gate(dest == MEDIA_DEST or not m["RW"],
             "unexpected shared writable mount " + dest)
        if dest == UPLOAD_DEST:
            spec = "type=bind,source={},target={},readonly".format(
                NEW_UPLOADER, UPLOAD_DEST)
        elif m["Type"] == "volume":
            spec = "type=volume,source={},target={}".format(m["Name"], dest)
            if not m["RW"]:
                spec += ",readonly"
        else:
            spec = "type=bind,source={},target={}".format(m["Source"], dest)
            if not m["RW"]:
                spec += ",readonly"
        args += ["--mount", spec]
    args += ["--entrypoint", "sh", l.IMAGE, "-lc",
             "bundle exec rails server -b 0.0.0.0 -p 3001"]
    docker(*args).check_returncode()
    newer = l.inspect(NEW)
    new_mounts = {m["Destination"]: m for m in newer["Mounts"]}
    gate(newer["State"]["Status"] == "created", "new candidate started unexpectedly")
    gate(set(newer["NetworkSettings"]["Networks"]) == {NETWORK},
         "new candidate network not internal sandbox-only")
    gate(not newer["HostConfig"]["PortBindings"], "new candidate public port detected")
    gate(new_mounts[UPLOAD_DEST]["Source"] == str(NEW_UPLOADER) and
         not new_mounts[UPLOAD_DEST]["RW"], "new private uploader overlay differs")
    gate(new_mounts[MEDIA_DEST]["Source"] == str(l.MEDIA) and
         new_mounts[MEDIA_DEST]["RW"], "new candidate media bind differs")
    gate(not new_mounts["/app"]["RW"], "new candidate /app unexpectedly writable")
    print("NEW PRE-CACHE SANDBOX RAILS CREATED — NOT STARTED", flush=True)
    print("QA 3002 AND PRODUCTION 3001 NOT SWITCHED", flush=True)


def smoke():
    l, f, _ = audit()
    gate(l.object_exists(NEW), "new sandbox Rails container missing")
    now = l.inspect(NEW)
    gate(now["State"]["Status"] in ("created", "running"),
         "candidate in unexpected state")
    gate(set(now["NetworkSettings"]["Networks"]) == {NETWORK},
         "candidate not isolated")
    gate(not now["HostConfig"]["PortBindings"], "candidate exposed host ports")
    mounts = {m["Destination"]: m for m in now["Mounts"]}
    gate(mounts[UPLOAD_DEST]["Source"] == str(NEW_UPLOADER) and
         not mounts[UPLOAD_DEST]["RW"], "candidate uploader changed")
    gate(mounts[MEDIA_DEST]["Source"] == str(l.MEDIA),
         "candidate media not sandbox-only")
    if now["State"]["Status"] == "created":
        docker("start", NEW).check_returncode()
    gate(l.inspect(NEW)["State"]["Status"] == "running", "candidate failed to start")

    expected = l.pgid(l.SANDBOX_DB)
    ruby = (
        "id=ActiveRecord::Base.connection.select_value("
        "'SELECT system_identifier::text FROM pg_control_system()').to_s;"
        "raise 'wrong database' unless id==ENV.fetch('QA_SANDBOX_CLUSTER');"
        "require 'carrierwave';"
        "raise 'wrong CarrierWave' unless "
        "Gem.loaded_specs.fetch('carrierwave').version.to_s=='2.2.7';"
        "u=AvatarUploader.new;"
        "raise 'new pre-cache guard absent' unless "
        "u.respond_to?(:verify_pre_cache_image!) && "
        "u.method(:cache!).owner==AvatarUploader;"
        "raise 'wrong catalog' unless Product.count==20;"
        "puts 'NEW PRE-CACHE CARRIERWAVE/SQL POLICY PASS'"
    )
    result = docker(
        "exec", "--env", "QA_SANDBOX_CLUSTER=" + expected,
        NEW, "bundle", "exec", "rails", "runner", ruby
    )
    gate(result.returncode == 0,
         "Rails runner pre-cache smoke failed: " + result.stderr[-350:])
    print(result.stdout.strip(), flush=True)
    ready = False
    request = (
        "require 'net/http';r=Net::HTTP.start('127.0.0.1',3001,"
        "open_timeout:3,read_timeout:8){|h|h.get('/users/sign_up')};"
        "raise 'HTTP bad' unless r.code=='200';"
        "raise 'no avatar field' unless r.body.include?('name=\"user[avatar]\"');"
        "raise 'no multipart form' unless r.body.include?('multipart/form-data');"
        "puts 'PRECACHE SANDBOX INTERNAL HTML 200 PASS'"
    )
    for _ in range(25):
        result = docker("exec", NEW, "ruby", "-rlogger", "-e", request)
        if result.returncode == 0:
            ready = True
            print(result.stdout.strip(), flush=True)
            break
        time.sleep(1)
    gate(ready, "new sandbox HTTP form did not become ready")
    gate(l.http(3001, "/info")[0] == 200 and
         l.http(3002, "/menu")[0] == 200, "active sites lost HTTP 200")
    print("NEW PRE-CACHE SANDBOX SMOKE PASS", flush=True)
    print("NO UPLOAD REQUESTS SENT", flush=True)


def test():
    l, f, _ = audit()
    checked_blob(RUBY_PROBE, RUBY_PROBE_BLOB)
    gate(l.object_exists(NEW), "new sandbox Rails missing")
    new = l.inspect(NEW)
    gate(new["State"]["Status"] == "running", "candidate Rails stopped")
    gate(set(new["NetworkSettings"]["Networks"]) == {NETWORK} and
         not new["HostConfig"]["PortBindings"], "candidate not private")
    mount = {m["Destination"]: m for m in new["Mounts"]}
    gate(mount[UPLOAD_DEST]["Source"] == str(NEW_UPLOADER),
         "new uploader overlay not loaded")
    cluster = l.pgid(l.SANDBOX_DB)
    print("RUNNING REAL MULTIPART IN PRE-CACHE SANDBOX ONLY", flush=True)
    output = subprocess.run(
        ["docker", "exec", "-i", "--env",
         "EXPECTED_SANDBOX_CLUSTER=" + cluster, NEW,
         "bundle", "exec", "rails", "runner", "-"],
        input=RUBY_PROBE.read_bytes(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=240, check=False
    )
    stdout = output.stdout.decode(errors="replace")
    if output.returncode != 0:
        print("PRE-CACHE MULTIPART FAILED (sandbox only): " +
              output.stderr.decode(errors="replace")[-1100:], file=sys.stderr)
        gate(False, "test suite returned nonzero; preserve sandbox evidence")
    gate("SANDBOX REAL HTTP MULTIPART SECURITY PASS" in stdout,
         "real multipart suite did not emit success")
    print(stdout.strip(), flush=True)
    gate(f.current_files() == f.verified_archive(),
         "sandbox files differ from private ten-file baseline")
    gate(f.sql(f.SANDBOX_DB, "SELECT COUNT(*) FROM users;") == "2",
         "sandbox synthetic user cleanup differs")
    gate(l.http(3001, "/info")[0] == 200 and
         l.http(3002, "/menu")[0] == 200, "original active HTTP changed")
    print("PRE-CACHE SANDBOX HTTP MULTIPART + CLEANUP PASS", flush=True)
    print("PRODUCTION 3001 / PATCHED QA 3002 UNCHANGED", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    for name in ("check", "create", "smoke", "test"):
        modes.add_argument("--" + name, action="store_true")
    options = parser.parse_args()
    try:
        if options.check:
            l, _, _ = audit()
            gate(not l.object_exists(NEW),
                 "new pre-cache sandbox container already exists")
            print("NEW PRE-CACHE SANDBOX CHECK PASS — NO WRITES", flush=True)
        elif options.create:
            create()
        elif options.smoke:
            smoke()
        else:
            test()
    except Exception as error:
        print("PRE-CACHE QA BLOCKED:", type(error).__name__,
              str(error)[:350], file=sys.stderr, flush=True)
        print("Never overwrite, delete or repeat create after a failure.",
              file=sys.stderr, flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
