#!/usr/bin/env python3
"""Private fourth-DB Rails HTTP QA: READ-ONLY bootstrap before interactive E2E.

--check          : SHA-reviewed read-only owner preflight + 4th DB + unique targets
--create         : copy 10 private media files, create NEW web Docker (NOT started)
--inspect-partial : READ-ONLY, verify an interrupted v1 media/Rack stage
--resume-create  : create ONLY missing Docker object from verified partial stage
--verify-created : inspect mounts/PG link/network/security/medias (READ-ONLY)
--smoke          : start ONLY new web, verify GET/HEAD, POST405, 4th PG identity

Never changes existing services, source, DBs, proxy, ports or original media.
This candidate deliberately preserves PGOPTIONS=read-only AND GET/HEAD-only.
No login, upload, real users, public network, or production authorization.
"""
import argparse
import hashlib
from pathlib import Path
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time

HOME = Path.home()
BASE = HOME / ".local/share/cafe_app"
DB_HELPER = BASE / "cafe_private_e2e_postgres_v1_20261105.py"
DB_BLOB = "068ac1ac8625c0993cfdc2bc33f4e8d688738e47"
HEADER_HELPER = BASE / "cafe_private_headers_mountfix_v1_20261104.py"
HEADER_BLOB = "0990c74fc281d236332116a2cff44df360a9482c"
E2E_WEB = "cafe-upload-security-e2e-web-readonly-20261105"
STAGE = BASE / "e2e_web_readonly_20261105"
MEDIA = STAGE / "uploads"
RACK = STAGE / "config.ru"
DB_URL = "postgresql://postgres@cafe-e2e-postgres:5432/cafe"
DB_NAME = "cafe-upload-security-e2e-pg-20261105"
NETWORK = "cafe-upload-security-e2e-net-20261105"
SOURCE_WEB = "cafe-upload-security-headers-mountfix-20261104"
IMAGE = "cafe-legacy-full:node14"
MEDIA_DEST = "/app/public/uploads"
RACK_DEST = "/app/config.ru"
MODES = ("check", "create", "inspect-partial", "resume-create", "verify-created", "smoke")

RUBY_SMOKE = r"""
require 'net/http'
require 'digest'
require 'uri'

begin
  id = ActiveRecord::Base.connection.select_value(
    'SELECT system_identifier::text FROM pg_control_system()'
  ).to_s
  raise 'Wrong PG cluster' unless id == ENV.fetch('EXPECTED_E2E_CLUSTER')
  raise 'Wrong DB' unless ActiveRecord::Base.connection.current_database == 'cafe'
  raise 'Wrong Rails env' unless Rails.env.development?
  readonly = ActiveRecord::Base.connection.select_value(
    'SHOW default_transaction_read_only'
  ).to_s
  raise 'PG session is not readonly' unless readonly == 'on'
  count = ActiveRecord::Base.connection.select_value(
    'SELECT COUNT(*) FROM products'
  ).to_i
  raise 'Wrong product baseline' unless count == 20
  bad = ActiveRecord::Base.connection.select_value(
    'SELECT COUNT(*) FROM products WHERE id=21'
  ).to_i
  raise 'Deleted test product present' unless bad == 0
  raise 'ImageMagick resource env missing' unless ENV['MAGICK_TIME_LIMIT'] == '30'
  require 'carrierwave'
  raise 'CarrierWave version drifted' unless
    Gem.loaded_specs.fetch('carrierwave').version.to_s == '2.2.7'
  raise 'Pre-cache guard missing' unless
    AvatarUploader.new.respond_to?(:verify_pre_cache_image!)
  puts 'E2E_FOURTH_DB_READ_ONLY_CARRIERWAVE_PASS'

  def request(method, path)
    connection = Net::HTTP.new('127.0.0.1', 3001, nil)
    connection.open_timeout = 4
    connection.read_timeout = 12
    req = case method
          when :head then Net::HTTP::Head.new(path)
          when :post then Net::HTTP::Post.new(path)
          else Net::HTTP::Get.new(path)
          end
    connection.request(req)
  end
  def check_headers(response, type)
    raise 'Not 200' unless response.code == '200'
    raise 'Wrong type' unless
      response['Content-Type'].to_s.split(';', 2).first.to_s.strip.downcase == type
    raise 'Missing nosniff' unless response['X-Content-Type-Options'].to_s.downcase == 'nosniff'
    raise 'Missing referrer policy' if response['Referrer-Policy'].to_s.empty?
    if type == 'text/html'
      raise 'Missing report-only CSP' unless
        response['Content-Security-Policy-Report-Only'].to_s.include?("script-src 'self'")
      raise 'Unexpected enforced CSP' unless
        response['Content-Security-Policy'].to_s.empty?
    else
      raise 'Unexpected JPEG CSP' unless
        response['Content-Security-Policy-Report-Only'].to_s.empty?
    end
  end

  check_headers(request(:get, '/users/sign_up'), 'text/html')
  check_headers(request(:get, '/info'), 'text/html')
  puts 'E2E_FOURTH_DB_READ_ONLY_HTML_HEADERS_PASS'
  root = '/app/public/uploads/'
  sample = Dir.glob(root + '**/*').sort.find do |path|
    File.file?(path) && !File.symlink?(path) &&
      File.realpath(path).start_with?(root) &&
      %w[.jpg .jpeg].include?(File.extname(path).downcase) &&
      File.size(path) <= 5_000_000
  end
  raise 'Private JPEG absent' unless sample
  digest = Digest::SHA256.file(sample).hexdigest
  path = URI::DEFAULT_PARSER.escape(sample.sub('/app/public', ''))
  raise 'Path outside uploads' unless path.start_with?('/uploads/')
  check_headers(request(:head, path), 'image/jpeg')
  photo = request(:get, path)
  check_headers(photo, 'image/jpeg')
  raise 'Image SHA differs' unless Digest::SHA256.hexdigest(photo.body.to_s) == digest
  puts 'E2E_FOURTH_DB_PRIVATE_JPEG_HTTP_SHA_PASS'

  response = request(:post, '/users')
  raise 'POST was not rejected' unless response.code == '405'
  raise 'Unexpected Allow' unless response['Allow'].to_s == 'GET, HEAD'
  after = ActiveRecord::Base.connection.select_value(
    'SELECT COUNT(*) FROM products'
  ).to_i
  raise 'Product count changed during read-only smoke' unless after == 20
  puts 'E2E_FOURTH_DB_POST_DENIED_405_PASS'
  puts 'E2E_FOURTH_DB_RO_HTTP_SMOKE_COMPLETE'
rescue StandardError => error
  klass = error.class.name.to_s
  klass = 'Error' unless /\A[A-Za-z][A-Za-z0-9_:]*\z/.match?(klass)
  puts 'E2E_FOURTH_DB_SMOKE_BLOCKED:' + klass
  exit 17
end
"""


def require(condition, reason):
    if not condition:
        raise RuntimeError("E2E FOURTH WEB BLOCKED: " + reason)


def run(*args, input_data=None, timeout=40):
    try:
        return subprocess.run(args, input=input_data,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=False, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError("E2E FOURTH WEB BLOCKED: subprocess timeout")


def docker(*args, input_data=None, timeout=40):
    return run("docker", *args, input_data=input_data, timeout=timeout)


def inspect(name):
    p = docker("inspect", name, timeout=15)
    require(p.returncode == 0, "expected container unavailable")
    return json.loads(p.stdout)[0]


def file_blob(path, value):
    require(path.is_file() and not path.is_symlink(), "reviewed helper missing")
    p = run("git", "hash-object", str(path), timeout=15)
    require(p.returncode == 0 and p.stdout.decode().strip() == value,
            "reviewed helper blob mismatch")


def load_helper(path, identifier):
    spec = importlib.util.spec_from_file_location(identifier, path)
    require(spec is not None and spec.loader is not None,
            "reviewed helper import failed")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def get_members():
    p = docker("network", "inspect", NETWORK, timeout=15)
    require(p.returncode == 0, "fourth dedicated network inaccessible")
    net = json.loads(p.stdout)[0]
    require(net["Internal"] is True,
            "fourth E2E PostgreSQL network is not internal")
    return {entry.get("Name") for entry in (net.get("Containers") or {}).values()}


def source_environment(candidate):
    entries = candidate["Config"]["Env"]
    env = dict(entry.split("=", 1) for entry in entries)
    require(len(env) == len(entries), "duplicate source environment key")
    require(env.get("DATABASE_URL") is not None and
            env.get("PGOPTIONS") == "-c default_transaction_read_only=on",
            "private QA source not locked to readonly PG")
    require(env.get("BUNDLE_GEMFILE") == "/app/Gemfile" and
            env.get("RAILS_ENV") == "development",
            "private QA source environment unexpected")
    require(not any(
        keyword in key.upper()
        for key in env
        for keyword in ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "API_KEY")
    ), "protected environment variable should not be copied")
    return env


def preflight(require_free=False):
    file_blob(DB_HELPER, DB_BLOB)
    file_blob(HEADER_HELPER, HEADER_BLOB)
    require(os.getuid() == 1000, "unexpected host file permissions/UID")
    fourth = load_helper(DB_HELPER, "reviewed_cafe_e2e_db")
    headers = load_helper(HEADER_HELPER, "reviewed_cafe_headers")
    # Its original SHA-pinned preflight also audits 3001/3002, 3 original
    # Postgres clusters, private media and sandbox source before any work.
    _, launcher, source_web, _, manifest, source_env = headers.checked_preflight()
    headers.check_new_container(source_web, launcher, manifest, source_env)
    candidate = inspect(SOURCE_WEB)
    require(candidate["State"]["Status"] == "running",
            "existing protected headers QA process not running")
    # Only PRE-CREATION: parent DB audit expects only a PG network member.
    # Post-creation we use independently reviewed two-member checks below.
    if require_free:
        fourth.verify_running()
        require(not headers.existing(E2E_WEB),
                "new E2E web Docker name already exists; do not recreate")
        require(not STAGE.exists() and not STAGE.is_symlink(),
                "new private E2E media stage already exists")
    else:
        require(fourth.validated_dump().is_file(),
                "verified original QA dump missing")
        fourth.owner_preflight()
        fourth.inspect_new(created=False) if get_members() == {DB_NAME} else None
    e2e_db = inspect(DB_NAME)
    require(e2e_db["State"]["Status"] == "running",
            "fourth independent postgres is not running")
    require(set(e2e_db["NetworkSettings"]["Networks"]) == {NETWORK} and
            not e2e_db["HostConfig"]["PortBindings"],
            "fourth DB network or port unexpectedly changed")
    return fourth, headers, launcher, candidate, manifest


def media_matches(headers, expected):
    require(MEDIA.is_dir() and not MEDIA.is_symlink(),
            "new media copy absent")
    require(headers.files_manifest(MEDIA) == expected,
            "ten new copied QA media have changed")
    require(RACK.is_file() and not RACK.is_symlink() and
            headers.sha(RACK) == headers.sha(headers.CONFIG),
            "private readonly Rack config differs from verified previous QA")


def inspect_web(headers, launcher, expected, state):
    require(headers.existing(E2E_WEB), "new E2E web container missing")
    web = inspect(E2E_WEB)
    source = inspect(SOURCE_WEB)
    require(web["State"]["Status"] == state,
            "new E2E web state differs from expected")
    require(web["Config"]["Image"] == IMAGE and
            web["Config"]["User"] == "1000:1000",
            "new E2E web image or user unexpected")
    require(web["HostConfig"]["ReadonlyRootfs"],
            "new E2E rootfs is not read-only")
    require(not web["HostConfig"]["PortBindings"],
            "new E2E web has published host ports")
    require(web["HostConfig"].get("Memory") == 1024 * 1024 * 1024 and
            web["HostConfig"].get("PidsLimit") == 256,
            "new E2E web resource caps differ")
    require(web["HostConfig"]["RestartPolicy"]["Name"] == "no",
            "new E2E web restart policy unexpected")
    require("ALL" in (web["HostConfig"].get("CapDrop") or []),
            "new E2E web capabilities not dropped")
    require(headers.is_no_new_privileges_enabled(
                web["HostConfig"].get("SecurityOpt")),
            "new E2E web no-new-privileges absent")
    require(set(web["NetworkSettings"]["Networks"]) == {NETWORK},
            "new E2E web joined a different network")
    members = get_members()
    require(members.issubset({E2E_WEB, DB_NAME}) and DB_NAME in members,
            "unknown member on E2E PostgreSQL network")
    if state == "running":
        require(members == {E2E_WEB, DB_NAME},
                "new E2E Rails not on private PG network")
    source_mounts = {m["Destination"]: m for m in source["Mounts"]}
    mounts = {m["Destination"]: m for m in web["Mounts"]}
    require(set(mounts) == set(source_mounts),
            "unexpected E2E Docker mount targets")
    for dest, old in source_mounts.items():
        new = mounts[dest]
        if dest == MEDIA_DEST:
            require(new["Source"] == str(MEDIA) and new["RW"],
                    "QA media bind does not point to new private copy")
        elif dest == RACK_DEST:
            require(new["Source"] == str(RACK) and new["RW"] is False,
                    "QA Rack config not mounted read-only")
        else:
            require(new["Source"] == old["Source"] and
                    new["RW"] is False,
                    "new E2E web unexpectedly changed protected shared mount")
    env = source_environment(web)
    expected_env = source_environment(source)
    expected_env["DATABASE_URL"] = DB_URL
    require(env == expected_env,
            "new E2E web env differs beyond the intended database URL")
    require(web["Config"]["Entrypoint"] == source["Config"]["Entrypoint"] and
            web["Config"]["Cmd"] == source["Config"]["Cmd"],
            "new E2E Rails startup changed")
    media_matches(headers, expected)
    return web


def check():
    fourth, headers, launcher, source, manifest = preflight(require_free=True)
    require(get_members() == {DB_NAME},
            "extra member on E2E PG network before QA web creation")
    require(inspect(DB_NAME)["State"]["Status"] == "running",
            "fourth Postgres stopped")
    require(headers.CONFIG.read_text(encoding="utf-8") ==
            headers.bundled_rack_config(),
            "source Rack config is not the reviewed CSP/405 candidate")
    print("PRIVATE FOURTH-DB/OWNER QA ISOLATION PREFLIGHT PASS", flush=True)
    print("FOURTH NETWORK ONLY-POSTGRES MEMBERSHIP PASS", flush=True)
    print("NEW READ-ONLY WEB/MEDIA TARGETS AVAILABLE — NO CHANGES", flush=True)


def create():
    _, headers, launcher, source, manifest = preflight(require_free=True)
    require(get_members() == {DB_NAME}, "unknown fourth PG network member")
    require(not headers.existing(E2E_WEB), "new E2E candidate already exists")
    require(not STAGE.exists() and not STAGE.is_symlink(),
            "new E2E media stage exists; never overwrite")
    original_media = headers.COPIED_MEDIA
    require(headers.files_manifest(original_media) == manifest,
            "validated private QA source media changed")
    require(headers.CONFIG.read_text(encoding="utf-8") ==
            headers.bundled_rack_config(),
            "reviewed Rack overlay changed")

    os.umask(0o077)
    STAGE.mkdir(mode=0o700)
    MEDIA.mkdir(mode=0o700)
    for rel, expected_sha in manifest.items():
        target = MEDIA / rel
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as out, (original_media / rel).open("rb") as reader:
            shutil.copyfileobj(reader, out, 128 * 1024)
        require(headers.sha(target) == expected_sha,
                "new copy private media SHA mismatch")
    with RACK.open("x", encoding="utf-8") as out:
        out.write(headers.CONFIG.read_text(encoding="utf-8"))
    media_matches(headers, manifest)

    create_container_from_stage(source, headers, launcher, manifest)


def inspect_partial():
    _fourth, headers, _launcher, _source, manifest = preflight()
    # No owner media bytes or filenames are logged, only SHA matches.
    require(not headers.existing(E2E_WEB),
            "target E2E Docker container exists; preserve it and inspect separately")
    require(get_members() == {DB_NAME},
            "fourth DB network has unexpected member")
    require(STAGE.is_dir() and not STAGE.is_symlink(),
            "interrupted new QA stage is missing or symlinked")
    require(MEDIA.is_dir() and not MEDIA.is_symlink(),
            "interrupted private media stage missing or symlinked")
    require(RACK.is_file() and not RACK.is_symlink(),
            "interrupted reviewed Rack file missing or symlinked")
    require(STAGE.stat().st_uid == 1000 and
            MEDIA.stat().st_uid == 1000 and
            RACK.stat().st_uid == 1000,
            "private QA stage owner differs")
    require(STAGE.stat().st_mode & 0o077 == 0 and
            MEDIA.stat().st_mode & 0o077 == 0 and
            RACK.stat().st_mode & 0o077 == 0,
            "private QA staging permissions are too open")
    media_matches(headers, manifest)
    print("E2E INTERRUPTED PRIVATE 10-MEDIA/RACK SHA256 STAGE PASS", flush=True)
    print("FOURTH DB NETWORK ONLY HAS POSTGRES / TARGET WEB ABSENT", flush=True)
    print("READ-ONLY PARTIAL-CREATION INSPECTION COMPLETE — NO CHANGES", flush=True)


def resume_create():
    # Only the new E2E web creation is permitted here. No recopy, overwrite,
    # remove, reconnect, restart, database restore or modifications to data.
    inspect_partial()
    _fourth, headers, launcher, source, manifest = preflight()
    require(not headers.existing(E2E_WEB), "new E2E web target appeared")
    require(get_members() == {DB_NAME},
            "fourth network changed since partial-stage inspection")
    media_matches(headers, manifest)
    create_container_from_stage(source, headers, launcher, manifest)


def create_container_from_stage(source, headers, launcher, manifest):
    # Use a stable Docker inspect dictionary; never reuse 'source' as an IO
    # reader while copying private media. Called only after strict staging
    # checks by --create or --resume-create.
    require(not headers.existing(E2E_WEB), "new E2E web already exists")
    require(get_members() == {DB_NAME},
            "unexpected fourth PostgreSQL network attachment")
    media_matches(headers, manifest)
    args = [
        "create", "--name", E2E_WEB, "--network", NETWORK,
        "--workdir", "/app", "--user", "1000:1000",
        "--read-only", "--memory", "1024m", "--pids-limit", "256",
        "--restart", "no", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
    ]
    env = source_environment(source)
    env["DATABASE_URL"] = DB_URL
    for key, val in sorted(env.items()):
        args.extend(["--env", key + "=" + val])
    for dest, opts in sorted((source["HostConfig"].get("Tmpfs") or {}).items()):
        args.extend(["--tmpfs", dest + (":" + opts if opts else "")])
    for mount in sorted(source["Mounts"],
                        key=lambda item: item["Destination"].count("/")):
        dest = mount["Destination"]
        require(mount["Type"] in ("volume", "bind"),
                "unexpected mounted filesystem type")
        if dest == MEDIA_DEST:
            spec = "type=bind,source={},target={}".format(MEDIA, dest)
        elif dest == RACK_DEST:
            spec = "type=bind,source={},target={},readonly".format(RACK, dest)
        else:
            require(not mount["RW"], "protected source has writable mount")
            if mount["Type"] == "volume":
                spec = "type=volume,source={},target={},readonly".format(
                    mount["Name"], dest)
            else:
                spec = "type=bind,source={},target={},readonly".format(
                    mount["Source"], dest)
        args.extend(["--mount", spec])
    args.extend(["--entrypoint", "sh", IMAGE, "-lc",
                 "bundle exec rails server -b 0.0.0.0 -p 3001"])
    result = docker(*args, timeout=65)
    require(result.returncode == 0,
            "new fourth-DB QA Docker create failed; preserve evidence")
    inspect_web(headers, launcher, manifest, "created")
    print("FOURTH-DB PRIVATE RAILS WEB CREATED — NOT STARTED", flush=True)
    print("PRIVATE 10-MEDIA SHA256 COPY VERIFIED / HTTP READ-ONLY", flush=True)
    print("NO HOST PORT / ORIGINAL RAILS AND PG UNCHANGED", flush=True)



def verify_created():
    fourth, headers, launcher, _source, manifest = preflight()
    inspect_web(headers, launcher, manifest, "created")
    fourth.validated_dump()
    print("FOURTH-DB PRIVATE RAILS CREATED-ONLY SECURITY PASS", flush=True)
    print("POSTGRES/ROOTFS/MOUNTS/MEDIA/NET READ-ONLY INSPECT PASS", flush=True)
    print("NO CHANGES / USER LOGIN AND UPLOADS STILL BLOCKED", flush=True)


def smoke():
    fourth, headers, launcher, _source, manifest = preflight()
    candidate = inspect_web(headers, launcher, manifest, "created")
    require(candidate["State"]["Status"] == "created",
            "new private E2E Rails was already started; do not retry")
    fourth_cluster = fourth.sql(DB_NAME,
        "SELECT system_identifier::text FROM pg_control_system();")
    require(fourth_cluster.isdigit(), "private 4th PG ID unavailable")
    three = [launcher.pgid(name) for name in
             (launcher.LIVE_DB, launcher.QA_DB, launcher.SANDBOX_DB)]
    require(len(set(three + [fourth_cluster])) == 4,
            "private 4th PG identity collision")
    p = docker("start", E2E_WEB, timeout=45)
    require(p.returncode == 0,
            "new fourth-DB QA Rails start failed; do not retry")
    require(inspect(E2E_WEB)["State"]["Status"] == "running",
            "new E2E Rails stopped immediately")
    wanted = (
        "E2E_FOURTH_DB_READ_ONLY_CARRIERWAVE_PASS",
        "E2E_FOURTH_DB_READ_ONLY_HTML_HEADERS_PASS",
        "E2E_FOURTH_DB_PRIVATE_JPEG_HTTP_SHA_PASS",
        "E2E_FOURTH_DB_POST_DENIED_405_PASS",
        "E2E_FOURTH_DB_RO_HTTP_SMOKE_COMPLETE",
    )
    good = False
    safe_reason = "NotReady"
    for _ in range(20):
        child = docker("exec", "-i",
                       "--env", "EXPECTED_E2E_CLUSTER=" + fourth_cluster,
                       E2E_WEB, "bundle", "exec", "rails", "runner", "-",
                       input_data=RUBY_SMOKE.encode("utf-8"), timeout=60)
        lines = child.stdout.decode(errors="replace").splitlines()
        if child.returncode == 0 and all(lines.count(marker) == 1
                                          for marker in wanted):
            good = True
            break
        for line in lines:
            m = re.fullmatch("E2E_FOURTH_DB_SMOKE_BLOCKED:([A-Za-z][A-Za-z0-9_:]*)",
                             line.strip())
            if m:
                safe_reason = m.group(1)
        time.sleep(1)
    require(good, "new E2E QA internal read-only HTTP failed: " + safe_reason +
            " (no private raw logs printed)")
    for marker in wanted:
        print(marker, flush=True)
    inspect_web(headers, launcher, manifest, "running")
    fourth.validated_dump()
    print("FOURTH PRIVATE DB RAILS HTTP READ-ONLY E2E BOOTSTRAP PASS", flush=True)
    print("ORIGINAL 3001/3002/THREE PG AND MEDIA UNCHANGED", flush=True)
    print("NO LOGIN/UPLOAD/POST/ADMIN OR PUBLIC RELEASE AUTHORIZED", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    for mode in MODES:
        modes.add_argument("--" + mode, action="store_true")
    args = parser.parse_args()
    try:
        if args.check:
            check()
        elif args.create:
            create()
        elif args.inspect_partial:
            inspect_partial()
        elif args.resume_create:
            resume_create()
        elif args.verify_created:
            verify_created()
        else:
            smoke()
    except Exception as exc:
        message = str(exc)
        if not message.startswith("E2E FOURTH WEB BLOCKED:"):
            message = "E2E FOURTH WEB BLOCKED: internal audit failed"
        print(message, file=sys.stderr, flush=True)
        print("Do not blindly rerun or remove artifacts; inspect safely.",
              file=sys.stderr, flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
