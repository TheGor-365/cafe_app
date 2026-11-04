#!/usr/bin/env python3
"""Read-only in-process Rack candidate audit in existing private Cafe sandbox.

No Rails service/proxy/container restarts, SQL/media writes, file retrieval or
public URL requests. Rails runner process is independent of serving Rails.
"""
import argparse
import importlib.util
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path.home() / ".local/share/cafe_app"
PRIOR = ROOT / "cafe_header_audit_v3_20261104.py"
PRIOR_BLOB = "0f1da472340e94a6216941bd5165cc11f2627f18"
CANDIDATE = ROOT / "cafe_headers_candidate_v1_20261104.rb"
CANDIDATE_BLOB = "5e708c8a84675bf30ef94f8c0583469c92304c4f"
SANDBOX = "cafe-upload-security-sandbox-precache-20261104"

RUBY_PROBE = r"""
require 'rack/mock'
require 'uri'

$cafe_header_stage = 'db_cluster'
begin
  id = ActiveRecord::Base.connection.select_value(
    'SELECT system_identifier::text FROM pg_control_system()'
  ).to_s
  raise 'Wrong PG cluster' unless id == ENV.fetch('EXPECTED_SANDBOX_CLUSTER')
  raise 'Wrong Rails environment' unless Rails.env.development?
  raise 'Missing Rack candidate' unless defined?(CafeHeadersCandidate)

  def header(response, key)
    pair = response.headers.find { |name, _| name.to_s.casecmp(key).zero? }
    pair && pair[1].to_s
  end
  def assert_html(response)
    raise 'HTML status not 200' unless response.status == 200
    raise 'Wrong HTML MIME' unless header(response, 'Content-Type').to_s.start_with?('text/html')
    raise 'HTML nosniff absent' unless header(response, 'X-Content-Type-Options') == 'nosniff'
    raise 'HTML referrer absent' if header(response, 'Referrer-Policy').to_s.empty?
    raise 'Report-Only CSP absent' unless
      header(response, 'Content-Security-Policy-Report-Only').to_s.include?("script-src 'self'")
  end

  $cafe_header_stage = 'rack_wrapper'
  request = Rack::MockRequest.new(CafeHeadersCandidate.new(Rails.application))
  options = { 'HTTP_HOST' => '127.0.0.1:3001' }

  $cafe_header_stage = 'signup_get'
  signup = request.get('/users/sign_up', options)
  assert_html(signup)
  puts 'QA_RACK_SIGNUP_HEADERS_PASS'

  $cafe_header_stage = 'info_get'
  info = request.get('/info', options)
  assert_html(info)
  puts 'QA_RACK_INFO_HEADERS_PASS'

  $cafe_header_stage = 'jpeg_selection'
  root = '/app/public/uploads/'
  file = Dir.glob(root + '**/*').sort.find do |path|
    File.file?(path) && !File.symlink?(path) &&
      File.realpath(path).start_with?(root) &&
      %w[.jpg .jpeg].include?(File.extname(path).downcase) &&
      File.size(path) <= 5_000_000
  end
  raise 'No safe sandbox JPEG' unless file
  url = URI::DEFAULT_PARSER.escape(file.sub('/app/public', ''))
  raise 'Out of scope JPEG' unless url.start_with?('/uploads/')

  $cafe_header_stage = 'jpeg_head'
  image = request.head(url, options)
  raise 'JPEG HEAD unhealthy' unless image.status == 200
  raise 'JPEG MIME wrong' unless header(image, 'Content-Type').to_s.start_with?('image/jpeg')
  raise 'JPEG nosniff absent' unless header(image, 'X-Content-Type-Options') == 'nosniff'
  raise 'JPEG referrer absent' if header(image, 'Referrer-Policy').to_s.empty?
  raise 'JPEG must not get HTML CSP' unless
    header(image, 'Content-Security-Policy-Report-Only').nil?
  puts 'QA_RACK_JPEG_HEAD_HEADERS_PASS'
  puts 'QA_RACK_EXISTING_ENFORCING_CSP:' +
    (header(signup, 'Content-Security-Policy').to_s.empty? ? 'NO' : 'YES')
  puts 'QA_RACK_IN_PROCESS_CANDIDATE_CHECK_COMPLETE'
rescue StandardError => error
  kind = error.class.name.to_s
  kind = 'UnknownError' unless /\A[A-Za-z][A-Za-z0-9_:]*\z/.match?(kind)
  puts 'CAFE_QA_HEADER_PROBE_ERROR:' + $cafe_header_stage.to_s + ':' + kind
  exit 9
end
"""


def require(value, reason):
    if not value:
        raise RuntimeError("QA HEADER AUDIT BLOCKED: " + reason)


def safe_run(*args, input_data=None, timeout=65):
    try:
        return subprocess.run(args, input=input_data, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout,
                              check=False)
    except subprocess.TimeoutExpired:
        raise RuntimeError("QA HEADER AUDIT BLOCKED: child process timeout")


def checked_blob(file, expected):
    require(file.is_file() and not file.is_symlink(), "reviewed helper missing")
    actual = safe_run("git", "hash-object", str(file), timeout=20)
    require(actual.returncode == 0 and
            actual.stdout.decode(errors="replace").strip() == expected,
            "reviewed helper Git blob mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()

    checked_blob(PRIOR, PRIOR_BLOB)
    checked_blob(CANDIDATE, CANDIDATE_BLOB)

    spec = importlib.util.spec_from_file_location("cafe_header_preflight", PRIOR)
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    _p, _l, cluster, _web = prior.required_runtime()

    runner = CANDIDATE.read_text(encoding="utf-8") + "\n" + RUBY_PROBE
    result = safe_run("docker", "exec", "-i", "--env",
                      "EXPECTED_SANDBOX_CLUSTER=" + cluster, SANDBOX,
                      "bundle", "exec", "rails", "runner", "-",
                      input_data=runner.encode("utf-8"))
    lines = [x.strip() for x in result.stdout.decode(errors="replace").splitlines()]
    if result.returncode != 0:
        stage = "runner_boot_or_unknown"
        for line in lines:
            found = re.fullmatch(
                r"CAFE_QA_HEADER_PROBE_ERROR:([a-z_]+):([A-Za-z][A-Za-z0-9_:]*)",
                line,
            )
            if found:
                stage = found.group(1) + "/" + found.group(2)
                break
        raise RuntimeError("QA HEADER AUDIT BLOCKED: Rails runner at " + stage)

    needed = {
        "QA_RACK_SIGNUP_HEADERS_PASS", "QA_RACK_INFO_HEADERS_PASS",
        "QA_RACK_JPEG_HEAD_HEADERS_PASS",
        "QA_RACK_IN_PROCESS_CANDIDATE_CHECK_COMPLETE",
    }
    require(needed <= set(lines), "in-process observations incomplete")
    for label in (
        "QA_RACK_SIGNUP_HEADERS_PASS", "QA_RACK_INFO_HEADERS_PASS",
        "QA_RACK_JPEG_HEAD_HEADERS_PASS",
    ):
        print(label, flush=True)
    report = [x for x in lines if x.startswith("QA_RACK_EXISTING_ENFORCING_CSP:")]
    require(len(report) == 1 and report[0].split(":")[-1] in ("NO", "YES"),
            "enforcing CSP observation missing")
    print(report[0], flush=True)
    prior.required_runtime()
    print("QA HEADERS IN-PROCESS CANDIDATE AUDIT COMPLETE", flush=True)
    print("RUNNING HTTP SERVICES/DB/MEDIA/PROXY UNMODIFIED", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        msg = str(error)
        if not msg.startswith("QA HEADER AUDIT BLOCKED: "):
            msg = "QA HEADER AUDIT BLOCKED: internal validation error"
        print(msg, file=sys.stderr)
        raise SystemExit(1)
