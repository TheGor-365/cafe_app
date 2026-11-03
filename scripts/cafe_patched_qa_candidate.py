#!/usr/bin/env python3
"""Prepare and smoke-test a new isolated QA Rails candidate with CarrierWave 2.2.7.

--check : inspect only, no writes or Docker state changes
--create: private snapshot of QA media, GitHub-reviewed uploader override,
          then docker create (NOT started, no published port)
--smoke : start only the NEW QA candidate; validate patched gem,
          actual QA PostgreSQL identity, uploader and internal HTTP.
          Does NOT switch host port 3002 or touch live port 3001.

If a gate fails after --create, keep new candidate/media for diagnostics.
Do not retry blindly. Never removes/restarts live or existing QA containers.
"""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path.home() / ".local/share/cafe_app"
PROJECT = Path.home() / "Рабочий стол/rails_projects/lite/cafe_app"
WORK = ROOT / "security_bundle_build_20261104"
BUNDLE = ROOT / "bundle_carrierwave_227_20261104"
QA_UPLOADS = ROOT / "uploads_qa_20261103"
NEW_UPLOADS = ROOT / "uploads_patched_qa_20261104"
OVERRIDE = ROOT / "qa_patched_avatar_20261104"
NEW = "cafe-app-patched-qa-candidate-20261104"
QA = "cafe-app-uploads-qa-avatar-20261103"
QA_DB = "cafe-upload-qa-pg-20261103"
LIVE = "cafe-app-local-3001-web"
LIVE_DB = "cafe-app-db"
QA_NET = "cafe-upload-qa-net-20261103"
QA_URL = "postgresql://postgres@cafe-app-db:5432/cafe"
IMAGE = "cafe-legacy-full:node14"
REF = "origin/feature/cafe-patched-qa-candidate-20261104"
EXPECTED_UPLOADER_BLOB = "314c4912610989deed400c5db7db7db20fe1f98a"
EXPECTED_HASHES = {
    "Gemfile": "c5fde478cd117c12",
    "Gemfile.lock": "99f86e38d68e203e",
    "app/uploaders/avatar_uploader.rb": "846a9692269fd8d9",
}
UPLOAD_REL = "qa/security/avatar_uploader.rb"


def run(*argv, capture=True):
    return subprocess.run(argv, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None)


def out(*argv):
    return run(*argv).stdout.strip()


def check(value, message):
    if not value:
        raise RuntimeError("STOP: " + message)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(128 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inspect(name):
    return json.loads(out("docker", "inspect", name))[0]


def exists(name):
    return subprocess.run(["docker", "container", "inspect", name],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def sql(name, query):
    return out("docker", "exec", "--user", "postgres", name,
               "psql", "-X", "-At", "-U", "postgres", "-d", "cafe", "-c", query)


def http(port, url):
    client = http.client.HTTPConnection("127.0.0.1", port, timeout=8)
    try:
        client.request("GET", url)
        response = client.getresponse()
        response.read()
        return response.status
    finally:
        client.close()


def base_audit():
    check(PROJECT.is_dir() and ROOT.is_dir(), "missing local project or private root")
    check(out("git", "-C", str(PROJECT), "branch", "--show-current") ==
          "feature/cafe-integration-local-20261101", "unexpected Git working branch")
    for rel, sha in EXPECTED_HASHES.items():
        path = PROJECT / rel
        check(path.is_file() and not path.is_symlink(), rel + " missing or symlink")
        check(sha256(path).startswith(sha), rel + " differs from verified local baseline")
    for rel in ["Gemfile", "Gemfile.lock"]:
        path = WORK / rel
        check(path.is_file() and not path.is_symlink(), "staged " + rel + " missing")
    check("carrierwave (2.2.7)" in (WORK / "Gemfile.lock").read_text(),
          "staged Gemfile.lock not pinned to CarrierWave 2.2.7")
    check("'= 2.2.7'" in (WORK / "Gemfile").read_text(),
          "staged Gemfile not pinned to CarrierWave 2.2.7")
    check(BUNDLE.is_dir() and not BUNDLE.is_symlink(),
          "isolated patched bundle missing")
    check((BUNDLE / "ruby/2.5.0/gems/carrierwave-2.2.7").is_dir(),
          "installed patched gem not found in new bundle")
    check(QA_UPLOADS.is_dir() and not QA_UPLOADS.is_symlink(),
          "QA original isolated uploads missing")

    qa, qa_db, live, live_db = (
        inspect(QA), inspect(QA_DB), inspect(LIVE), inspect(LIVE_DB)
    )
    for name, item in ((QA, qa), (QA_DB, qa_db), (LIVE, live), (LIVE_DB, live_db)):
        check(item["State"]["Status"] == "running", name + " is not running")
    nets = lambda item: set(item["NetworkSettings"]["Networks"])
    check(nets(qa) == {QA_NET} and nets(qa_db) == {QA_NET},
          "unexpected QA network configuration")
    check(QA_NET not in nets(live) and QA_NET not in nets(live_db),
          "production connected to QA private network")
    env = dict(item.split("=", 1) for item in qa["Config"]["Env"])
    check(env.get("DATABASE_URL") == QA_URL, "QA database URL changed")
    check(qa["HostConfig"]["ReadonlyRootfs"], "QA root filesystem is not readonly")
    check(qa["Config"]["Image"] == IMAGE, "unexpected QA image")
    check(qa["Config"]["User"] == "1000:1000", "unexpected QA user")

    mounts = {m["Destination"]: m for m in qa["Mounts"]}
    for name in ["/app", "/bundle", "/app/public/uploads"]:
        check(name in mounts, "missing QA mount " + name)
    check(not mounts["/app"]["RW"] and
          mounts["/app"]["Source"] == str(PROJECT), "QA /app source not readonly project")
    check(mounts["/bundle"]["Type"] == "volume" and
          mounts["/bundle"]["Name"] == "cafe-legacy-bundle-20261101" and
          not mounts["/bundle"]["RW"], "original read-only gem volume mismatch")
    check(mounts["/app/public/uploads"]["Source"] == str(QA_UPLOADS) and
          mounts["/app/public/uploads"]["RW"], "old QA uploads mount mismatch")
    for dest in ["/app/Gemfile", "/app/Gemfile.lock",
                 "/app/app/uploaders/avatar_uploader.rb"]:
        check(dest not in mounts, "QA already overlays protected " + dest)

    cluster_sql = "SELECT system_identifier::text FROM pg_control_system();"
    qa_cluster, live_cluster = sql(QA_DB, cluster_sql), sql(LIVE_DB, cluster_sql)
    check(qa_cluster.isdigit() and live_cluster.isdigit() and
          qa_cluster != live_cluster, "QA and live PostgreSQL cluster mismatch")
    check(http(3001, "/info") == 200 and http(3002, "/menu") == 200,
          "existing live or QA HTTP health check failed")

    branch_blob = out("git", "-C", str(PROJECT), "rev-parse", REF + ":" + UPLOAD_REL)
    check(branch_blob == EXPECTED_UPLOADER_BLOB,
          "reviewed uploader in Git branch differs")
    print("QA/LIVE ISOLATION PASS", flush=True)
    print("PATCHED BUNDLE AND LOCAL SOURCES VERIFIED", flush=True)
    return qa, qa_cluster


def media_inventory(path):
    result = {}
    for child in path.rglob("*"):
        check(not child.is_symlink(), "unsafe symlink in media: " + str(child))
        relative = child.relative_to(path).as_posix()
        if child.is_file():
            result[relative] = sha256(child)
        else:
            check(child.is_dir(), "unexpected special file " + str(child))
            result[relative] = "directory"
    return result


def create():
    qa, _ = base_audit()
    check(not exists(NEW), "candidate container already exists")
    for dest in [NEW_UPLOADS, OVERRIDE]:
        check(not dest.exists() and not dest.is_symlink(),
              str(dest) + " already exists")

    # New private QA image copy; no cleanup/removal of existing files.
    source_manifest = media_inventory(QA_UPLOADS)
    shutil.copytree(str(QA_UPLOADS), str(NEW_UPLOADS), symlinks=False)
    check(source_manifest == media_inventory(NEW_UPLOADS),
          "new QA copy integrity mismatch")
    os.chmod(str(NEW_UPLOADS), 0o700)
    OVERRIDE.mkdir(mode=0o700)
    uploader_src = subprocess.check_output(
        ["git", "-C", str(PROJECT), "show", REF + ":" + UPLOAD_REL]
    )
    uploader_dest = OVERRIDE / "avatar_uploader.rb"
    uploader_dest.write_bytes(uploader_src)
    os.chmod(str(uploader_dest), 0o600)
    check(out("git", "-C", str(PROJECT), "hash-object", str(uploader_dest)) ==
          EXPECTED_UPLOADER_BLOB, "candidate uploader SHA mismatch")

    cfg, host = qa["Config"], qa["HostConfig"]
    args = ["docker", "create", "--name", NEW, "--network", QA_NET,
            "--read-only", "--user", cfg["User"],
            "--workdir", cfg.get("WorkingDir") or "/app",
            "--restart", "no", "--memory", "1024m", "--pids-limit", "256"]
    for entry in cfg.get("Env") or []:
        args += ["--env", entry]
    args += ["--env", "BUNDLE_GEMFILE=/app/Gemfile"]
    for opt in host.get("SecurityOpt") or []:
        args += ["--security-opt", opt]
    for cap in host.get("CapDrop") or []:
        args += ["--cap-drop", cap]
    for path, options in (host.get("Tmpfs") or {}).items():
        args += ["--tmpfs", path + (":" + options if options else "")]

    old_mounts = {m["Destination"]: m for m in qa["Mounts"]}
    for dest, mount in sorted(old_mounts.items(), key=lambda item: item[0].count("/")):
        if dest == "/bundle":
            spec = "type=bind,source={},target=/bundle,readonly".format(BUNDLE)
        elif dest == "/app/public/uploads":
            spec = "type=bind,source={},target={}".format(NEW_UPLOADS, dest)
        elif mount["Type"] == "volume":
            spec = "type=volume,source={},target={}".format(mount["Name"], dest)
        elif mount["Type"] == "bind":
            spec = "type=bind,source={},target={}".format(mount["Source"], dest)
        else:
            raise RuntimeError("Unsupported original QA Docker mount type")
        if dest not in ("/bundle", "/app/public/uploads") and not mount["RW"]:
            spec += ",readonly"
        args += ["--mount", spec]

    extra = {
        "/app/Gemfile": WORK / "Gemfile",
        "/app/Gemfile.lock": WORK / "Gemfile.lock",
        "/app/app/uploaders/avatar_uploader.rb": uploader_dest
    }
    for dest, src in extra.items():
        args += ["--mount", "type=bind,source={},target={},readonly".format(src, dest)]
    args += [cfg["Image"]] + (cfg.get("Cmd") or [])
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)
    candidate = inspect(NEW)
    mounts = {m["Destination"]: m for m in candidate["Mounts"]}
    check(candidate["State"]["Status"] == "created",
          "candidate should be created but NOT started")
    check(set(candidate["NetworkSettings"]["Networks"]) == {QA_NET},
          "unexpected candidate network")
    check(not candidate["HostConfig"]["PortBindings"],
          "candidate unexpectedly publishes a host port")
    for dest, path in [("/bundle", BUNDLE),
                       ("/app/public/uploads", NEW_UPLOADS),
                       ("/app/Gemfile", WORK / "Gemfile"),
                       ("/app/Gemfile.lock", WORK / "Gemfile.lock"),
                       ("/app/app/uploaders/avatar_uploader.rb", uploader_dest)]:
        check(mounts[dest]["Source"] == str(path),
              "candidate mount source differs: " + dest)
        check(mounts[dest]["RW"] == (dest == "/app/public/uploads"),
              "candidate mount RW wrong: " + dest)
    check(not mounts["/app"]["RW"], "candidate project mount became RW")

    print("NEW PATCHED QA CANDIDATE CREATED — NOT STARTED", flush=True)
    print("NO HOST PORT PUBLISHED / ORIGINAL QA INTACT", flush=True)
    print("MEDIA SNAPSHOT SHA256 MATCH", flush=True)


def smoke():
    _, qa_cluster = base_audit()
    check(exists(NEW), "candidate not created")
    candidate = inspect(NEW)
    check(candidate["State"]["Status"] in ("created", "running"),
          "candidate in unexpected state")
    check(set(candidate["NetworkSettings"]["Networks"]) == {QA_NET},
          "candidate not on QA-only network")
    check(not candidate["HostConfig"]["PortBindings"],
          "candidate publishes a host port")
    mounts = {m["Destination"]: m for m in candidate["Mounts"]}
    check(mounts["/bundle"]["Source"] == str(BUNDLE) and not mounts["/bundle"]["RW"],
          "candidate patched gem mount differs")
    check(mounts["/app/public/uploads"]["Source"] == str(NEW_UPLOADS),
          "candidate media mount differs")
    check(mounts["/app/app/uploaders/avatar_uploader.rb"]["Source"] ==
          str(OVERRIDE / "avatar_uploader.rb"), "candidate uploader override differs")
    if candidate["State"]["Status"] == "created":
        subprocess.run(["docker", "start", NEW], check=True,
                       stdout=subprocess.DEVNULL)
    assert inspect(NEW)["State"]["Status"] == "running"
    # This checks actual executable code under the new Gemfile and bundle,
    # and verifies that SQL points to isolated QA PG, not live production PG.
    rails = (
        "require 'net/http'; "
        "id=ActiveRecord::Base.connection.select_value("
        "'SELECT system_identifier::text FROM pg_control_system()').to_s; "
        "raise 'Wrong QA cluster' unless id==ENV.fetch('QA_CLUSTER_EXPECTED'); "
        "require 'carrierwave'; "
        "raise 'CarrierWave not patched' unless "
        "Gem.loaded_specs.fetch('carrierwave').version.to_s=='2.2.7'; "
        "u=AvatarUploader.new; "
        "raise 'QA uploader missing file policy' unless "
        "u.extension_allowlist==%w(jpg jpeg png gif) && "
        "u.size_range.end==2097152 && "
        "u.content_type_allowlist.first.match('image/png'); "
        "puts 'PATCHED RAILS/SQL/AVATAR POLICY PASS'"
    )
    check_result = run("docker", "exec", "--env", "QA_CLUSTER_EXPECTED=" + qa_cluster,
                       NEW, "bundle", "exec", "rails", "runner", rails)
    print(check_result.stdout.strip(), flush=True)

    # Warm up and smoke only the new backend's private internal 3001 port.
    ruby = (
        "require 'net/http'; "
        "r=Net::HTTP.start('127.0.0.1',3001,"
        "open_timeout:3,read_timeout:8) {|h| h.get('/users/sign_up')}; "
        "raise 'wrong form code' unless r.code=='200'; "
        "raise 'avatar input missing' unless r.body.include?('name=\"user[avatar]\"'); "
        "raise 'multipart form missing' unless r.body.include?('multipart/form-data'); "
        "puts 'PATCHED QA INTERNAL HTML 200 PASS'"
    )
    ok = False
    for _ in range(20):
        result = subprocess.run(["docker", "exec", NEW, "ruby", "-rlogger", "-e", ruby],
                                capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout.strip(), flush=True)
            ok = True
            break
        time.sleep(1)
    check(ok, "new QA internal Rails HTTP smoke timed out")
    check(http(3001, "/info") == 200 and http(3002, "/menu") == 200,
          "original site/QA HTTP changed")
    print("LIVE 3001 AND EXISTING QA 3002 UNCHANGED", flush=True)
    print("PATCHED QA CANDIDATE INTERNAL SMOKE PASS", flush=True)
    print("NO QA PROXY SWITCH — BROWSER STILL ON PREVIOUS QA", flush=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    mode = cli.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--create", action="store_true")
    mode.add_argument("--smoke", action="store_true")
    args = cli.parse_args()
    try:
        if args.check:
            base_audit()
            check(not exists(NEW), "candidate already exists")
            check(not NEW_UPLOADS.exists(), "candidate media copy already exists")
            check(not OVERRIDE.exists(), "candidate override directory already exists")
            print("PATCHED QA CANDIDATE PREFLIGHT PASS — NO CHANGES MADE")
        elif args.create:
            create()
        else:
            smoke()
    except Exception as exc:
        print("CANDIDATE BLOCKED:", type(exc).__name__, str(exc)[:500],
              file=sys.stderr)
        print("Do NOT delete or retry over existing candidate; inspect it first.",
              file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
