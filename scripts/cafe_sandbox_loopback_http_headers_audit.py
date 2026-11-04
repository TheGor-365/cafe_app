#!/usr/bin/env python3
"""One-shot REAL loopback HTTP GET/HEAD QA, isolated within existing Cafe sandbox.

Uses an ephemeral WEBrick server bound to 127.0.0.1:0 INSIDE the isolated
sandbox Rails runner process, not a new Docker container or host port.
The server is always shut down; original 3001/3002, PG and private media stay
untouched. This is not a public / browser / reverse-proxy test.
"""
import argparse
import importlib.util
from pathlib import Path
import re
import subprocess
import sys

BASE = Path.home() / ".local/share/cafe_app"
PREFLIGHT = BASE / "cafe_header_audit_v3_20261104.py"
PREFLIGHT_BLOB = "0f1da472340e94a6216941bd5165cc11f2627f18"
CANDIDATE = BASE / "cafe_headers_candidate_v1_20261104.rb"
CANDIDATE_BLOB = "5e708c8a84675bf30ef94f8c0583469c92304c4f"
SANDBOX = "cafe-upload-security-sandbox-precache-20261104"

# Injected after exact SHA-pinned candidate source in the sandbox rails runner.
# All private paths, HTTP bodies and Docker stderr remain inside the child.
RUBY_LOOPBACK = r"""
require 'rack/handler/webrick'
require 'webrick'
require 'net/http'
require 'digest'
require 'uri'

$cafe_loopback_step = 'start'
server = nil
worker = nil

begin
  $cafe_loopback_step = 'sandbox_identity'
  cluster = ActiveRecord::Base.connection.select_value(
    'SELECT system_identifier::text FROM pg_control_system()'
  ).to_s
  raise 'Wrong sandbox PostgreSQL' unless
    cluster == ENV.fetch('EXPECTED_SANDBOX_CLUSTER')
  raise 'Wrong Rails env' unless Rails.env.development?
  raise 'Missing in-memory Rack candidate' unless defined?(CafeHeadersCandidate)

  def assert_response(response, type)
    raise 'Non-200 HTTP' unless response.code.to_i == 200
    mime = response['Content-Type'].to_s.split(';', 2).first.to_s.strip.downcase
    raise 'Wrong MIME' unless mime == type
    raise 'Missing nosniff' unless response['X-Content-Type-Options'].to_s.downcase == 'nosniff'
    raise 'Missing Referrer-Policy' if response['Referrer-Policy'].to_s.empty?
    if type == 'text/html'
      report = response['Content-Security-Policy-Report-Only'].to_s
      raise 'Missing diagnostic CSP' unless report.include?("script-src 'self'")
      raise 'Enforcing CSP unexpectedly present' unless
        response['Content-Security-Policy'].to_s.empty?
    else
      raise 'HTML CSP leaked onto JPEG' unless
        response['Content-Security-Policy-Report-Only'].to_s.empty?
    end
  end

  def request_http(port, path, method)
    client = Net::HTTP.new('127.0.0.1', port, nil)
    client.open_timeout = 3
    client.read_timeout = 10
    req = method == :head ? Net::HTTP::Head.new(path) : Net::HTTP::Get.new(path)
    client.request(req)
  end

  # Select only existing private snapshot media. Never emit path or raw bytes.
  $cafe_loopback_step = 'private_jpeg_sample'
  root = '/app/public/uploads/'
  sample = Dir.glob(root + '**/*').sort.find do |path|
    File.file?(path) && !File.symlink?(path) &&
      File.realpath(path).start_with?(root) &&
      %w[.jpg .jpeg].include?(File.extname(path).downcase) &&
      File.size(path) <= 5_000_000
  end
  raise 'No isolated JPEG sample' unless sample
  before_sha = Digest::SHA256.file(sample).hexdigest
  url = URI::DEFAULT_PARSER.escape(sample.sub('/app/public', ''))
  raise 'Unsafe sample path' unless url.start_with?('/uploads/')

  # WEBrick binds ONLY to Docker-container loopback and picks an ephemeral
  # port; it cannot publish a host port or modify the existing Rails listener.
  $cafe_loopback_step = 'webrick_init'
  server = WEBrick::HTTPServer.new(
    BindAddress: '127.0.0.1',
    Port: 0,
    AccessLog: [],
    Logger: WEBrick::Log.new(File::NULL, WEBrick::Log::FATAL),
    RequestTimeout: 10,
    MaxClients: 4
  )
  server.mount('/', Rack::Handler::WEBrick,
               CafeHeadersCandidate.new(Rails.application))
  port = server.listeners.first.addr[1]
  raise 'No ephemeral server port' unless port.is_a?(Integer) && port > 0
  $cafe_loopback_step = 'webrick_start'
  worker = Thread.new { server.start }

  # No fixed public port, proxy, Docker restart, container creation, or db write.
  # A short startup grace period avoids racing the worker loop.
  sleep 0.1
  raise 'Loopback worker terminated unexpectedly' unless worker.alive?

  $cafe_loopback_step = 'signup_get'
  signup = request_http(port, '/users/sign_up', :get)
  assert_response(signup, 'text/html')
  puts 'LOOPBACK_HTTP_SIGNUP_HTML_PASS'

  $cafe_loopback_step = 'info_get'
  info = request_http(port, '/info', :get)
  assert_response(info, 'text/html')
  puts 'LOOPBACK_HTTP_INFO_HTML_PASS'

  $cafe_loopback_step = 'jpeg_head'
  head = request_http(port, url, :head)
  assert_response(head, 'image/jpeg')
  raise 'HEAD unexpectedly downloaded body' unless head.body.to_s.empty?
  puts 'LOOPBACK_HTTP_JPEG_HEAD_PASS'

  $cafe_loopback_step = 'jpeg_get'
  photo = request_http(port, url, :get)
  assert_response(photo, 'image/jpeg')
  raise 'JPEG GET payload differs from original' unless
    Digest::SHA256.hexdigest(photo.body.to_s) == before_sha
  raise 'Original media changed after HTTP' unless
    Digest::SHA256.file(sample).hexdigest == before_sha
  puts 'LOOPBACK_HTTP_JPEG_GET_SHA_PASS'

  puts 'LOOPBACK_HTTP_SECURITY_HEADERS_CANDIDATE_COMPLETE'
rescue StandardError => error
  kind = error.class.name.to_s
  kind = 'UnknownError' unless /\A[A-Za-z][A-Za-z0-9_:]*\z/.match?(kind)
  puts 'CAFE_LOOPBACK_HTTP_ERROR:' + $cafe_loopback_step.to_s + ':' + kind
  exit 9
ensure
  if server
    begin
      server.shutdown
      worker.join(3) if worker
    rescue StandardError
      # Process exit still closes the ephemeral listener.
    end
  end
end
"""


def require(ok, reason):
    if not ok:
        raise RuntimeError("CAFE LOOPBACK GATE BLOCKED: " + reason)


def run(*args, input_data=None, timeout=75):
    try:
        return subprocess.run(
            args, input=input_data, capture_output=True,
            timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("CAFE LOOPBACK GATE BLOCKED: child process timeout")


def check_sha(path, blob):
    require(path.is_file() and not path.is_symlink(), "reviewed local helper missing")
    response = run("git", "hash-object", str(path), timeout=15)
    require(response.returncode == 0 and
            response.stdout.decode(errors="replace").strip() == blob,
            "reviewed local helper Git blob mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    check_sha(PREFLIGHT, PREFLIGHT_BLOB)
    check_sha(CANDIDATE, CANDIDATE_BLOB)

    spec = importlib.util.spec_from_file_location("cafe_loopback_preflight", PREFLIGHT)
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    _p, _l, cluster, _web = previous.required_runtime()

    inline_source = CANDIDATE.read_text(encoding="utf-8") + "\n" + RUBY_LOOPBACK
    result = run(
        "docker", "exec", "-i", "--env",
        "EXPECTED_SANDBOX_CLUSTER=" + cluster,
        SANDBOX, "bundle", "exec", "rails", "runner", "-",
        input_data=inline_source.encode("utf-8"),
    )
    stdout_lines = [line.strip() for line in
                    result.stdout.decode(errors="replace").splitlines()]
    if result.returncode != 0:
        marker = "runner_boot_or_unknown"
        for line in stdout_lines:
            hit = re.fullmatch(
                r"CAFE_LOOPBACK_HTTP_ERROR:([a-z_]+):([A-Za-z][A-Za-z0-9_:]*)",
                line,
            )
            if hit:
                marker = hit.group(1) + "/" + hit.group(2)
                break
        raise RuntimeError("CAFE LOOPBACK GATE BLOCKED: " +
                           "internal HTTP at " + marker + " (raw details suppressed)")

    expected = (
        "LOOPBACK_HTTP_SIGNUP_HTML_PASS",
        "LOOPBACK_HTTP_INFO_HTML_PASS",
        "LOOPBACK_HTTP_JPEG_HEAD_PASS",
        "LOOPBACK_HTTP_JPEG_GET_SHA_PASS",
        "LOOPBACK_HTTP_SECURITY_HEADERS_CANDIDATE_COMPLETE",
    )
    require(all(stdout_lines.count(value) == 1 for value in expected),
            "internal HTTP evidence incomplete")
    for line in expected:
        print(line, flush=True)
    # No writes to source, media, SQL or Docker network/port configuration.
    previous.required_runtime()
    print("LOOPBACK_REAL_HTTP_CANDIDATE_READ_ONLY_COMPLETE", flush=True)
    print("NO EXTERNAL PORT OR QA/PRODUCTION CUTOVER", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        message = str(error)
        if not message.startswith("CAFE LOOPBACK GATE BLOCKED: "):
            message = "CAFE LOOPBACK GATE BLOCKED: internal validation error"
        print(message, file=sys.stderr)
        raise SystemExit(1)
