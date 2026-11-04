#!/usr/bin/env python3
"""Read-only HTTP security headers + ImageMagick limits audit inside isolated cafe QA.

No application edits, Docker creates/removes/restarts, uploads, DB changes,
public URL requests, secret extraction or private image-content output.

The owning second sandbox Rails was already verified using a SHA-pinned
pre-cache uploader and 10/10 real HTTP multipart tests (2026-11-04).
This gate audits actual runtime configuration, not merely checked-in files.
"""
import argparse
import ast
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

BASE = Path.home() / ".local/share/cafe_app"
ACCEPTANCE = BASE / "cafe_precache_sandbox_acceptance_20261104.py"
ACCEPTANCE_BLOB = "eb0bfc5e923d45f991d1d9ea26ad47e18ed02989"
EXPECTED_RAILS = "cafe-upload-security-sandbox-precache-20261104"
EXPECTED_IMAGE = "cafe-legacy-full:node14"
EXPECTED_NETWORK = "cafe-upload-security-sandbox-20261104"

# No file URL, user identity, email, session cookie, image body or request token
# is included in the JSON payload returned from Rails.
RUBY = r"""
require 'json'
require 'net/http'
require 'uri'

cluster = ActiveRecord::Base.connection.select_value(
  'SELECT system_identifier::text FROM pg_control_system()'
).to_s
raise 'Wrong sandbox PostgreSQL cluster' unless
  cluster == ENV.fetch('EXPECTED_SANDBOX_CLUSTER')
raise 'Wrong CarrierWave version' unless
  Gem.loaded_specs.fetch('carrierwave').version.to_s == '2.2.7'
raise 'Wrong Rails environment' unless Rails.env.development?

ROOT = '/app/public/uploads'
raise 'Sandbox media missing' unless File.directory?(ROOT)
raise 'Missing pre-cache uploader' unless AvatarUploader.new.respond_to?(:verify_pre_cache_image!)

def http_get(path, method = :get)
  client = Net::HTTP.new('127.0.0.1', 3001, nil)
  client.open_timeout = 3
  client.read_timeout = 10
  request = method == :head ? Net::HTTP::Head.new(path) : Net::HTTP::Get.new(path)
  client.request(request)
end

def safe_headers(response)
  {
    'status' => response.code.to_i,
    'content_type' => response['Content-Type'].to_s.split(';').first.strip.downcase,
    'nosniff' => response['X-Content-Type-Options'].to_s.downcase == 'nosniff',
    'csp_present' => !response['Content-Security-Policy'].to_s.empty?,
    'csp_report_only' => !response['Content-Security-Policy-Report-Only'].to_s.empty?,
    'frame_protection' => response['X-Frame-Options'].to_s,
    'referrer_policy_present' => !response['Referrer-Policy'].to_s.empty?,
    'cache_control_present' => !response['Cache-Control'].to_s.empty?,
    'cors_any_origin' => response['Access-Control-Allow-Origin'].to_s.strip == '*',
    'content_disposition' => response['Content-Disposition'].to_s.split(';').first.downcase
  }
end

result = {
  'environment' => Rails.env,
  'development_detailed_errors' => !!Rails.application.config.consider_all_requests_local,
  'gem_version' => '2.2.7',
  'html' => safe_headers(http_get('/users/sign_up')),
  'info' => safe_headers(http_get('/info')),
  'image' => {'sample' => 'not_found'}
}

# Find only a file from our restored isolated media; never print its
# private path or any bytes. The HTTP URL is constructed *internally*.
extensions = %w(.png .jpg .jpeg .gif)
paths = Dir.glob(ROOT + '/**/*').sort.select do |path|
  File.file?(path) && !File.symlink?(path) &&
    extensions.include?(File.extname(path).downcase) && File.size(path) <= 5_000_000
end
if paths.any?
  private_path = paths.first
  url = private_path.sub('/app/public', '')
  raise 'Sample image path outside /uploads' unless url.start_with?('/uploads/')
  uri_path = URI::DEFAULT_PARSER.escape(url)
  result['image'] = safe_headers(http_get(uri_path, :head))
  result['image']['sample'] = 'existing_private_media'
  result['image']['probe'] = 'HTTP HEAD (no body downloaded)'
end

# This marker is machine-readable but never contains user data.
puts 'CAFE_SECURITY_HEADERS_JSON:' + JSON.generate(result)
"""


def require(ok, message):
    if not ok:
        raise RuntimeError("SANDBOX AUDIT BLOCKED: " + message)


def shell(*args, input_data=None):
    return subprocess.run(
        args, input=input_data, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, timeout=60,
    )


def verify_sha(path, expected):
    require(path.is_file() and not path.is_symlink(),
            "missing expected reviewed local helper: " + path.name)
    digest = shell("git", "hash-object", str(path))
    require(digest.returncode == 0 and digest.stdout.decode().strip() == expected,
            "Git blob changed for " + path.name)


def owner():
    verify_sha(ACCEPTANCE, ACCEPTANCE_BLOB)
    spec = importlib.util.spec_from_file_location("cafe_precache_owner", ACCEPTANCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(module.NEW == EXPECTED_RAILS and
            module.NETWORK == EXPECTED_NETWORK,
            "reviewed sandbox launcher target differs")
    return module


def required_runtime():
    p = owner()
    l, f, old = p.audit()  # read-only: exact 10 restored files, 3 separate PGs
    require(l.object_exists(EXPECTED_RAILS),
            "pre-cache sandbox Rails not created")
    web = l.inspect(EXPECTED_RAILS)
    require(web["State"]["Status"] == "running",
            "pre-cache sandbox Rails stopped")
    require(set(web["NetworkSettings"]["Networks"]) == {EXPECTED_NETWORK},
            "sandbox Rails has unexpected external network")
    require(not web["HostConfig"]["PortBindings"],
            "sandbox Rails exposes an external port")
    require(web["HostConfig"]["ReadonlyRootfs"],
            "sandbox Rails root filesystem writable")
    require(web["Config"]["Image"] == EXPECTED_IMAGE,
            "sandbox Rails container image differs")
    require(web["Config"]["User"] == "1000:1000",
            "sandbox Rails container user differs")
    mount = {m["Destination"]: m for m in web["Mounts"]}
    require(mount["/app"]["RW"] is False,
            "sandbox project /app writable")
    require(mount["/app/public/uploads"]["RW"] is True and
            mount["/app/public/uploads"]["Source"] == str(l.MEDIA),
            "sandbox media mount differs")
    require(mount["/app/app/uploaders/avatar_uploader.rb"]["Source"] ==
            str(p.NEW_UPLOADER) and
            not mount["/app/app/uploaders/avatar_uploader.rb"]["RW"],
            "pre-cache uploader mount differs")
    require("/run/secrets/cafe_pg_password" not in mount,
            "sandbox Rails has a live secret mount")
    env = dict(item.split("=", 1) for item in web["Config"]["Env"])
    require(env.get("DATABASE_URL") == l.SANDBOX_URL,
            "sandbox database target is wrong")
    require(env.get("BUNDLE_GEMFILE") == "/app/Gemfile",
            "patched bundle not selected")
    cluster = l.pgid(l.SANDBOX_DB)
    require(cluster.isdigit() and
            cluster not in (l.pgid(l.QA_DB), l.pgid(l.LIVE_DB)),
            "sandbox database identity is not unique")
    require(l.http(3001, "/info")[0] == 200 and
            l.http(3002, "/menu")[0] == 200,
            "original active site HTTP unhealthy")
    print("SANDBOX BUNDLE/NETWORK/MEDIA/SQL PREFLIGHT PASS", flush=True)
    print("PRODUCTION 3001 AND QA 3002 STILL HTTP 200", flush=True)
    return p, l, cluster, web


def redact_value(raw):
    """Resource output normalization: only numeric-ish single tokens."""
    raw = raw.strip().split()[0].strip(",;") if raw.strip() else "not_set"
    return raw[:28] if re.fullmatch(r"[0-9A-Za-z._+\-/]+", raw) else "unreadable"


def parse_limits(raw):
    """Accept ImageMagick 6/7 resource display without echoing source paths."""
    limits = {}
    labels = ("width", "height", "area", "memory", "map",
              "disk", "time", "thread", "file", "list")
    for line in raw.splitlines():
        m = re.match(r"^\s*([A-Za-z]+)\s*:\s*(\S+)", line)
        if m and m.group(1).lower() in labels:
            limits[m.group(1).lower()] = redact_value(m.group(2))
    return limits


def observe_ruby(rails, cluster):
    proc = shell(
        "docker", "exec", "-i",
        "--env", "EXPECTED_SANDBOX_CLUSTER=" + cluster,
        rails, "bundle", "exec", "rails", "runner", "-",
        input_data=RUBY.encode("utf-8"),
    )
    require(proc.returncode == 0,
            "internal Rails HTTP header probe failed, exit " +
            str(proc.returncode) + " (details retained locally)")
    marker = b"CAFE_SECURITY_HEADERS_JSON:"
    lines = [line[len(marker):] for line in proc.stdout.splitlines()
             if line.startswith(marker)]
    require(len(lines) == 1,
            "expected one scrubbed internal HTTP observation")
    value = json.loads(lines[0].decode("utf-8"))
    require(value.get("environment") == "development" and
            value.get("gem_version") == "2.2.7",
            "unexpected Rails runtime or gem")
    for key in ("html", "info", "image"):
        require(isinstance(value.get(key), dict),
                "missing observation " + key)
    require(value["html"]["status"] == 200 and
            value["info"]["status"] == 200,
            "isolated internal Rails HTML health check failed")
    return value


def observe_image_magick(rails):
    version = shell("docker", "exec", rails, "identify", "-version")
    limits = shell("docker", "exec", rails, "identify", "-list", "resource")
    policy = shell("docker", "exec", rails, "identify", "-list", "policy")
    result = {
        "tool_available": version.returncode == 0,
        "resource_listing_available": limits.returncode == 0,
        "policy_listing_available": policy.returncode == 0,
        "limits": parse_limits(limits.stdout.decode(errors="replace"))
                  if limits.returncode == 0 else {},
        "policy_mentions_rights": bool(
            re.search(r"\brights\s*:", policy.stdout.decode(errors="replace"),
                      re.IGNORECASE)
        ) if policy.returncode == 0 else False,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="read-only audit, no changes")
    opts = parser.parse_args()
    require(opts.check, "--check is required; no mutating modes exist")
    p, l, cluster, web = required_runtime()
    headers = observe_ruby(EXPECTED_RAILS, cluster)
    image = observe_image_magick(EXPECTED_RAILS)
    for label in ("html", "info", "image"):
        entry = headers[label]
        status = entry.get("status")
        if status is None:
            print("HTTP_" + label.upper() + "_HEADERS: NOT_OBSERVED", flush=True)
            continue
        print("HTTP_" + label.upper() + "_STATUS:", status, flush=True)
        print("HTTP_" + label.upper() + "_CONTENT_TYPE:",
              entry.get("content_type") or "missing", flush=True)
        for field in ("nosniff", "csp_present", "csp_report_only",
                      "referrer_policy_present", "cors_any_origin"):
            print("HTTP_" + label.upper() + "_" + field.upper() + ":",
                  "YES" if entry.get(field) else "NO", flush=True)
    print("IMAGE_HEAD_SAMPLE:", headers["image"].get("sample", "unavailable"),
          flush=True)
    print("IMAGEMAGICK_TOOL_AVAILABLE:",
          "YES" if image["tool_available"] else "NO", flush=True)
    print("IMAGEMAGICK_RESOURCE_LIST_AVAILABLE:",
          "YES" if image["resource_listing_available"] else "NO", flush=True)
    for kind in ("width", "height", "area", "memory", "map", "disk", "time"):
        print("IMAGEMAGICK_LIMIT_" + kind.upper() + ":",
              image["limits"].get(kind, "NOT_CONFIGURED_OR_UNREPORTED"),
              flush=True)
    print("IMAGEMAGICK_POLICY_LIST_AVAILABLE:",
          "YES" if image["policy_listing_available"] else "NO", flush=True)
    print("IMAGEMAGICK_POLICY_RIGHTS_PRESENT:",
          "YES" if image["policy_mentions_rights"] else "NO", flush=True)
    print("SANDBOX IMAGE/HEADER AUDIT OBSERVATIONS COMPLETE", flush=True)
    print("OBSERVATION ONLY — NOT PUBLIC SECURITY RELEASE APPROVAL", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("READ-ONLY SECURITY AUDIT STOPPED:", type(error).__name__,
              str(error)[:250], file=sys.stderr)
        raise SystemExit(1)
