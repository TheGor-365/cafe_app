#!/usr/bin/env python3
"""Fail-closed staged private Cafe QA Rails runtime (existing internal Docker network).

--check  : READ-ONLY validates exact owner preflight, candidate, sandbox and
           protected media; refuses existing target resources.
--create : creates NEW private 10-file snapshot copy and NEW Docker container,
           NOT started, NO published ports, no writes into original project.
--smoke  : starts ONLY the new candidate container and tests internal real HTTP.
           POST is denied (405) so shared SANDBOX-only PG cannot be mutated via
           normal browser POST. A separately cloned PG is needed for multipart
           and interactive admin tests. Never expose this test DB publicly.

This script must be obtained from an exact SHA-pinned GitHub commit. Does not
stop, restart, remove or reconfigure any existing Docker or local service.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

HOME = Path.home()
BASE = HOME / ".local/share/cafe_app"
PREFLIGHT = BASE / "cafe_header_audit_v3_20261104.py"
PREFLIGHT_BLOB = "0f1da472340e94a6216941bd5165cc11f2627f18"
HEADERS = BASE / "cafe_headers_candidate_v1_20261104.rb"
HEADERS_BLOB = "5e708c8a84675bf30ef94f8c0583469c92304c4f"
STAGE = BASE / "headers_private_web_candidate_20261104"
COPIED_MEDIA = STAGE / "uploads"
CONFIG = STAGE / "config.ru"
NEW_WEB = "cafe-upload-security-headers-private-20261104"
ORIGIN_WEB = "cafe-upload-security-sandbox-precache-20261104"
NETWORK = "cafe-upload-security-sandbox-20261104"
IMAGE = "cafe-legacy-full:node14"
MEDIA_DEST = "/app/public/uploads"
CONFIG_DEST = "/app/config.ru"
HEADERS_DEST = "/app/qa_headers_candidate.rb"
POLICY = {
    "MAGICK_TIME_LIMIT": "30",
    "MAGICK_WIDTH_LIMIT": "8KP",
    "MAGICK_HEIGHT_LIMIT": "8KP",
    "MAGICK_AREA_LIMIT": "32MP",
    "MAGICK_MEMORY_LIMIT": "128MiB",
    "MAGICK_MAP_LIMIT": "256MiB",
    "MAGICK_DISK_LIMIT": "512MiB",
    "MAGICK_THREAD_LIMIT": "2",
    "MAGICK_FILE_LIMIT": "64",
}

# This file is mounted at /app/config.ru IN A NEW CONTAINER ONLY. All parent
# source files, including owner's original config.ru, remain read-only.
# Block non-GET/HEAD HTTP methods while this QA web shares isolated sandbox PG.
# No form submissions, avatars or admin writes should occur on this candidate.
RACK_CONFIG = """# frozen_string_literal: true
require_relative 'config/environment'
require_relative 'qa_headers_candidate'

class CafeQaReadOnlyMethods
  def initialize(app)
    @app = app
  end

  def call(env)
    method = env['REQUEST_METHOD'].to_s.upcase
    unless method == 'GET' || method == 'HEAD'
      return [405, {'Content-Type' => 'text/plain; charset=utf-8',
                     'Allow' => 'GET, HEAD',
                     'Cache-Control' => 'no-store'},
              ['QA read-only: GET/HEAD only']]
    end
    @app.call(env)
  end
end

use CafeQaReadOnlyMethods
use CafeHeadersCandidate
run Rails.application
"""

# This Ruby snippet is read-only; its only HTTP POST is intended to return 405
# BEFORE Rails is invoked. Private image body is hashed but never displayed.
RUBY_SMOKE = r"""
require 'net/http'
require 'uri'
require 'digest'

begin
  id = ActiveRecord::Base.connection.select_value(
    'SELECT system_identifier::text FROM pg_control_system()'
  ).to_s
  raise 'Wrong PG cluster' unless id == ENV.fetch('EXPECTED_SANDBOX_CLUSTER')
  raise 'Wrong Rails env' unless Rails.env.development?
  raise 'Wrong ImageMagick time bound' unless ENV['MAGICK_TIME_LIMIT'] == '30'
  mode = ActiveRecord::Base.connection.select_value('SHOW default_transaction_read_only').to_s
  raise 'QA database connection is not read-only' unless mode == 'on'

  def qa_request(path, method)
    client = Net::HTTP.new('127.0.0.1', 3001, nil)
    client.open_timeout = 3
    client.read_timeout = 12
    request = case method
              when :head then Net::HTTP::Head.new(path)
              when :post then Net::HTTP::Post.new(path)
              else Net::HTTP::Get.new(path)
              end
    client.request(request)
  end
  def qa_assert(response, mime)
    raise 'HTTP not 200' unless response.code == '200'
    value = response['Content-Type'].to_s.split(';', 2).first.to_s.strip.downcase
    raise 'Unexpected HTTP MIME' unless value == mime
    raise 'Missing nosniff' unless response['X-Content-Type-Options'].to_s.downcase == 'nosniff'
    raise 'Missing referrer policy' if response['Referrer-Policy'].to_s.empty?
    if mime == 'text/html'
      raise 'Missing report-only CSP' unless
        response['Content-Security-Policy-Report-Only'].to_s.include?("script-src 'self'")
      raise 'Enforcing CSP not expected' unless response['Content-Security-Policy'].to_s.empty?
    else
      raise 'JPEG got HTML CSP' unless response['Content-Security-Policy-Report-Only'].to_s.empty?
    end
  end

  qa_assert(qa_request('/users/sign_up', :get), 'text/html')
  qa_assert(qa_request('/info', :get), 'text/html')
  puts 'PRIVATE_QA_REAL_HTTP_HTML_HEADERS_PASS'

  root = '/app/public/uploads/'
  sample = Dir.glob(root + '**/*').sort.find do |path|
    File.file?(path) && !File.symlink?(path) &&
      File.realpath(path).start_with?(root) &&
      %w[.jpg .jpeg].include?(File.extname(path).downcase) &&
      File.size(path) <= 5_000_000
  end
  raise 'No private sandbox JPEG' unless sample
  digest = Digest::SHA256.file(sample).hexdigest
  path = URI::DEFAULT_PARSER.escape(sample.sub('/app/public', ''))
  raise 'Image outside uploads' unless path.start_with?('/uploads/')
  qa_assert(qa_request(path, :head), 'image/jpeg')
  photo = qa_request(path, :get)
  qa_assert(photo, 'image/jpeg')
  raise 'JPEG download mismatch' unless Digest::SHA256.hexdigest(photo.body.to_s) == digest
  raise 'Original changed' unless Digest::SHA256.file(sample).hexdigest == digest
  puts 'PRIVATE_QA_REAL_HTTP_JPEG_SHA_PASS'

  denied = qa_request('/users', :post)
  raise 'POST was not blocked' unless denied.code == '405'
  raise 'Wrong allowed methods' unless denied['Allow'].to_s == 'GET, HEAD'
  puts 'PRIVATE_QA_POST_BLOCKED_405_PASS'

  require 'carrierwave'
  raise 'CarrierWave not pinned' unless
    Gem.loaded_specs.fetch('carrierwave').version.to_s == '2.2.7'
  raise 'Pre-cache uploader guard absent' unless
    AvatarUploader.new.respond_to?(:verify_pre_cache_image!)
  puts 'PRIVATE_QA_CARRIERWAVE_POLICY_PASS'
  puts 'PRIVATE_QA_READ_ONLY_RUNTIME_HTTP_COMPLETE'
rescue StandardError => error
  kind = error.class.name.to_s
  kind = 'UnknownError' unless /\A[A-Za-z][A-Za-z0-9_:]*\z/.match?(kind)
  puts 'PRIVATE_QA_SMOKE_BLOCKED:' + kind
  exit 9
end
"""


def require(ok, reason):
    if not ok:
        raise RuntimeError("PRIVATE QA GATE BLOCKED: " + reason)


def run(*args, input_data=None, timeout=45):
    try:
        return subprocess.run(args, input=input_data, capture_output=True,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        raise RuntimeError("PRIVATE QA GATE BLOCKED: command timed out")


def docker(*args, input_data=None, timeout=45):
    return run("docker", *args, input_data=input_data, timeout=timeout)


def checked_blob(path, expected):
    require(path.is_file() and not path.is_symlink(), "reviewed helper absent")
    result = run("git", "hash-object", str(path), timeout=15)
    require(result.returncode == 0 and
            result.stdout.decode(errors="replace").strip() == expected,
            "reviewed Git blob differs")


def existing(name):
    result = docker("container", "inspect", name, timeout=15)
    return result.returncode == 0


def inspect(name):
    result = docker("inspect", name, timeout=20)
    require(result.returncode == 0, "expected Docker resource absent")
    return json.loads(result.stdout)[0]


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as data:
        for chunk in iter(lambda: data.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def files_manifest(path):
    require(path.is_dir() and not path.is_symlink(), "private media folder absent")
    out = {}
    for entry in path.rglob("*"):
        require(not entry.is_symlink() and
                (entry.is_file() or entry.is_dir()),
                "unexpected sandbox media entry")
        if entry.is_file():
            rel = entry.relative_to(path)
            require(not any(part in (".", "..") for part in rel.parts),
                    "unsafe media path")
            out[rel.as_posix()] = sha(entry)
    require(len(out) == 10, "unexpected original sandbox media count")
    return out


def checked_preflight():
    checked_blob(PREFLIGHT, PREFLIGHT_BLOB)
    checked_blob(HEADERS, HEADERS_BLOB)
    require(os.getuid() == 1000, "host UID is not expected container UID 1000")
    spec = importlib.util.spec_from_file_location("cafe_qa_preflight", PREFLIGHT)
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    p, launcher, cluster, web = prior.required_runtime()
    require(web["Config"]["Image"] == IMAGE and
            web["Config"]["User"] == "1000:1000",
            "protected original Rails image/user changed")
    require(set(web["NetworkSettings"]["Networks"]) == {NETWORK},
            "unexpected origin Docker network")
    require(not web["HostConfig"]["PortBindings"],
            "origin sandbox unexpectedly exposes port")
    mounts = {item["Destination"]: item for item in web["Mounts"]}
    require(mounts[MEDIA_DEST]["RW"], "origin media mount not writable")
    require(mounts["/app"]["RW"] is False, "owner source is writable")
    require(CONFIG_DEST not in mounts and HEADERS_DEST not in mounts,
            "overlay destination collision")
    original_media = Path(mounts[MEDIA_DEST]["Source"])
    require(original_media == launcher.MEDIA, "media source changed")
    existing_manifest = files_manifest(original_media)
    env = dict(item.split("=", 1) for item in web["Config"]["Env"])
    require(len(env) == len(web["Config"]["Env"]),
            "duplicated origin environment entries")
    require(env.get("DATABASE_URL") == launcher.SANDBOX_URL and
            env.get("BUNDLE_GEMFILE") == "/app/Gemfile" and
            env.get("RAILS_ENV") == "development",
            "origin database/bundle/env changed")
    require(not any(
        word in key.upper()
        for key in env
        for word in ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "API_KEY")
    ), "unexpected secret-like origin environment")
    require(not any(key.startswith("MAGICK_") for key in env),
            "origin has unexpected image policy variables")
    require("PGOPTIONS" not in env,
            "origin has unexpected PostgreSQL session options")
    require(launcher.pgid(launcher.SANDBOX_DB) == cluster,
            "origin PostgreSQL identity changed")
    require(web["Config"].get("Cmd") == [
        "-lc", "bundle exec rails server -b 0.0.0.0 -p 3001"
    ], "origin Rails startup command changed")
    require(web["Config"].get("Entrypoint") == ["sh"],
            "origin Rails entrypoint changed")
    require(set(web["HostConfig"].get("Tmpfs") or {}) >= {
        "/app/log", "/app/tmp", "/tmp"
    }, "origin protected tmpfs mounts changed")
    return prior, launcher, web, cluster, existing_manifest, env


def verify_staged_media(expected):
    require(STAGE.is_dir() and not STAGE.is_symlink(), "new QA stage absent")
    require(CONFIG.is_file() and not CONFIG.is_symlink(),
            "QA config.ru overlay missing")
    require(CONFIG.read_text(encoding="utf-8") == RACK_CONFIG,
            "QA config.ru overlay changed")
    require(files_manifest(COPIED_MEDIA) == expected,
            "new private QA media differs from original")
    require(sha(HEADERS) and sha(CONFIG), "overlay source unreadable")


def is_no_new_privileges_enabled(options):
    """Accept Docker's three documented TRUE spellings; reject missing/false."""
    if not isinstance(options, list):
        return False
    return any(isinstance(value, str) and
               value.strip() in (
                   "no-new-privileges",
                   "no-new-privileges=true",
                   "no-new-privileges:true",
               ) for value in options)


def check_new_container(web, launcher, expected, env):
    require(existing(NEW_WEB), "new QA container absent")
    new = inspect(NEW_WEB)
    require(new["Config"]["Image"] == IMAGE and
            new["Config"]["User"] == "1000:1000",
            "QA candidate runtime image/user differs")
    require(new["HostConfig"]["ReadonlyRootfs"],
            "QA candidate root is writable")
    require(not new["HostConfig"]["PortBindings"],
            "QA candidate published host port")
    require(set(new["NetworkSettings"]["Networks"]) == {NETWORK},
            "QA candidate connected outside internal sandbox")
    require(new["HostConfig"]["CapDrop"] and
            "ALL" in new["HostConfig"]["CapDrop"],
            "QA candidate capabilities were not dropped")
    require(is_no_new_privileges_enabled(
                new["HostConfig"].get("SecurityOpt")),
            "QA candidate no-new-privileges missing or disabled")
    require(new["HostConfig"]["RestartPolicy"]["Name"] == "no",
            "candidate unexpectedly has restart policy")
    mounts = {item["Destination"]: item for item in new["Mounts"]}
    require(mounts["/app"]["Source"] ==
            {item["Destination"]: item for item in web["Mounts"]}["/app"]["Source"]
            and mounts["/app"]["RW"] is False,
            "owner app source mount changed")
    require(mounts[MEDIA_DEST]["Source"] == str(COPIED_MEDIA) and
            mounts[MEDIA_DEST]["RW"],
            "new media must be private copy")
    require(mounts[CONFIG_DEST]["Source"] == str(CONFIG) and
            not mounts[CONFIG_DEST]["RW"],
            "missing readonly config.ru overlay")
    require(mounts[HEADERS_DEST]["Source"] == str(HEADERS) and
            not mounts[HEADERS_DEST]["RW"],
            "missing readonly headers candidate overlay")
    require("/run/secrets/cafe_pg_password" not in mounts,
            "QA candidate secret mount present")
    for destination, mount in mounts.items():
        require(not mount["RW"] or destination == MEDIA_DEST,
                "unexpected writable mount in new candidate")
    candidate_env = dict(item.split("=", 1) for item in new["Config"]["Env"])
    require(candidate_env.get("DATABASE_URL") == launcher.SANDBOX_URL,
            "QA candidate uses wrong database")
    require(candidate_env.get("BUNDLE_GEMFILE") == "/app/Gemfile",
            "QA candidate uses wrong bundle")
    require(candidate_env.get("RAILS_ENV") == "development",
            "QA candidate not in internal-only development")
    require(candidate_env.get("PGOPTIONS") ==
            "-c default_transaction_read_only=on",
            "QA PostgreSQL session must be read-only")
    for key, val in POLICY.items():
        require(candidate_env.get(key) == val, "ImageMagick policy not inherited")
    for key, val in env.items():
        require(candidate_env.get(key) == val, "protected environment key differs")
    require(new["Config"]["Entrypoint"] == ["sh"] and
            new["Config"]["Cmd"] == web["Config"]["Cmd"],
            "QA server startup differs")
    require(new["State"]["Status"] in ("created", "running"),
            "QA candidate status differs")
    verify_staged_media(expected)
    return new


def verify_created():
    _prior, launcher, web, _cluster, original, env = checked_preflight()
    candidate = check_new_container(web, launcher, original, env)
    require(candidate["State"]["Status"] == "created",
            "candidate must remain unstarted for this audit")
    print("PRIVATE QA CREATED-CONTAINER SECURITY OPTIONS PASS", flush=True)
    print("PRIVATE QA STAGED 10-MEDIA SHA256 COPY PASS", flush=True)
    print("PRIVATE QA CREATED-ONLY VALIDATION COMPLETE — NO CHANGES", flush=True)


def check():
    _prior, launcher, web, _cluster, original, env = checked_preflight()
    require(not STAGE.exists() and not STAGE.is_symlink(),
            "new QA stage already exists; never overwrite")
    require(not existing(NEW_WEB),
            "new QA container already exists; never overwrite")
    print("PRIVATE QA RUNTIME SOURCE/DB/NETWORK/MEDIA PREFLIGHT PASS", flush=True)
    print("UNIQUE QA STAGE AND CONTAINER AVAILABLE", flush=True)
    print("PRIVATE QA CHECK ONLY — NO DOCKER OR FILE CHANGES", flush=True)


def create():
    _prior, launcher, web, _cluster, manifest, env = checked_preflight()
    require(not STAGE.exists() and not STAGE.is_symlink(),
            "new QA stage already exists; do not retry")
    require(not existing(NEW_WEB),
            "new QA container already exists; do not retry")

    # All writes go to a unique private stage, not protected project/backup.
    os.umask(0o077)
    STAGE.mkdir(mode=0o700)
    COPIED_MEDIA.mkdir(mode=0o700)
    original = Path({item["Destination"]: item for item in web["Mounts"]}[
        MEDIA_DEST]["Source"])
    for rel, source_hash in manifest.items():
        item = COPIED_MEDIA / rel
        item.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Exclusive create: no overwrites/hardlinks/symlinks.
        fd = os.open(str(item), os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as dst, (original / rel).open("rb") as src:
            shutil.copyfileobj(src, dst, 1024 * 1024)
        require(sha(item) == source_hash, "new private QA JPEG copy changed")
    with CONFIG.open("x", encoding="utf-8") as dst:
        dst.write(RACK_CONFIG)
    verify_staged_media(manifest)

    host = web["HostConfig"]
    args = [
        "create", "--name", NEW_WEB,
        "--network", NETWORK, "--read-only",
        "--user", "1000:1000", "--workdir", "/app",
        "--memory", "1024m", "--pids-limit", "256",
        "--restart", "no", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
    ]
    for key, value in sorted(env.items()):
        args.extend(["--env", key + "=" + value])
    # Libpq makes this candidate's PostgreSQL connection read-only by default,
    # independent of the Rack method guard. Do not forward to old containers.
    args.extend(["--env", "PGOPTIONS=-c default_transaction_read_only=on"])
    for key, value in sorted(POLICY.items()):
        args.extend(["--env", key + "=" + value])
    for destination, opts in sorted((host.get("Tmpfs") or {}).items()):
        args.extend(["--tmpfs", destination + (":" + opts if opts else "")])

    for mount in sorted(web["Mounts"],
                        key=lambda entry: entry["Destination"].count("/")):
        dest = mount["Destination"]
        require(mount["Type"] in ("volume", "bind"),
                "unexpected inherited mount type")
        require(not mount["RW"] or dest == MEDIA_DEST,
                "cannot inherit writable existing mount")
        if dest == MEDIA_DEST:
            spec = "type=bind,source={},target={}".format(COPIED_MEDIA, dest)
        elif mount["Type"] == "volume":
            require(not mount["RW"], "inherited volume would be writable")
            spec = "type=volume,source={},target={},readonly".format(
                mount["Name"], dest)
        else:
            spec = "type=bind,source={},target={},readonly".format(
                mount["Source"], dest)
        args.extend(["--mount", spec])
    args.extend([
        "--mount", "type=bind,source={},target={},readonly".format(
            CONFIG, CONFIG_DEST),
        "--mount", "type=bind,source={},target={},readonly".format(
            HEADERS, HEADERS_DEST),
    ])
    args.extend(["--entrypoint", "sh", IMAGE, "-lc",
                 "bundle exec rails server -b 0.0.0.0 -p 3001"])
    result = docker(*args, timeout=55)
    require(result.returncode == 0, "new private QA Docker create failed")
    new = check_new_container(web, launcher, manifest, env)
    require(new["State"]["Status"] == "created",
            "new QA container unexpectedly started")
    checked_preflight()
    print("PRIVATE QA IMMUTABLE CONTAINER CREATED — NOT STARTED", flush=True)
    print("10 PRIVATE MEDIA COPIES SHA256 VERIFIED", flush=True)
    print("NO HOST PORT, NO QA/PRODUCTION CHANGES", flush=True)


def smoke():
    prior, launcher, web, cluster, manifest, env = checked_preflight()
    new = check_new_container(web, launcher, manifest, env)
    if new["State"]["Status"] == "created":
        started = docker("start", NEW_WEB, timeout=45)
        require(started.returncode == 0, "new QA candidate start failed")
    require(inspect(NEW_WEB)["State"]["Status"] == "running",
            "new QA candidate did not stay running")

    required = (
        "PRIVATE_QA_REAL_HTTP_HTML_HEADERS_PASS",
        "PRIVATE_QA_REAL_HTTP_JPEG_SHA_PASS",
        "PRIVATE_QA_POST_BLOCKED_405_PASS",
        "PRIVATE_QA_CARRIERWAVE_POLICY_PASS",
        "PRIVATE_QA_READ_ONLY_RUNTIME_HTTP_COMPLETE",
    )
    succeeded = False
    safe_error = "not_ready"
    for _ in range(20):
        check = docker(
            "exec", "-i", "--env", "EXPECTED_SANDBOX_CLUSTER=" + cluster,
            NEW_WEB, "bundle", "exec", "rails", "runner", "-",
            input_data=RUBY_SMOKE.encode("utf-8"), timeout=60,
        )
        lines = [line.strip() for line in
                 check.stdout.decode(errors="replace").splitlines()]
        if check.returncode == 0 and all(
                lines.count(marker) == 1 for marker in required):
            succeeded = True
            break
        for line in lines:
            match = re.fullmatch(
                r"PRIVATE_QA_SMOKE_BLOCKED:([A-Za-z][A-Za-z0-9_:]*)",
                line,
            )
            if match:
                safe_error = match.group(1)
        time.sleep(1)
    require(succeeded, "candidate internal HTTP not ready: " + safe_error +
            " (raw logs suppressed)")
    for line in required:
        print(line, flush=True)
    check_new_container(web, launcher, manifest, env)
    checked_preflight()
    print("PRIVATE QA PERSISTENT HEADERS/MAGICK HTTP GATE PASS", flush=True)
    print("ORIGINAL 3001/3002, PG AND ORIGINAL MEDIA UNCHANGED", flush=True)
    print("NOT CLEARED FOR USER LOGIN/UPLOAD OR PUBLIC RELEASE", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    for name in ("check", "create", "verify-created", "smoke"):
        modes.add_argument("--" + name, action="store_true")
    options = parser.parse_args()
    try:
        if options.check:
            check()
        elif options.verify_created:
            verify_created()
        elif options.create:
            create()
        else:
            smoke()
    except Exception as exc:
        message = str(exc)
        if not message.startswith("PRIVATE QA GATE BLOCKED: "):
            message = "PRIVATE QA GATE BLOCKED: internal validation"
        print(message, file=sys.stderr, flush=True)
        print("If --create was attempted, do not rerun or remove partial QA artifacts; inspect safely.",
              file=sys.stderr, flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
