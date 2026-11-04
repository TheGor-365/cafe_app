#!/usr/bin/env python3
"""Read-only ImageMagick resource candidate gate for the existing private Cafe sandbox.

No Docker create/start/stop/restart, database writes, uploads or local source
changes. Resource limits are applied only to individual docker exec processes.
This does NOT apply the candidate to the already-running Rails web process.
The previous owner-approved HTTP audit is SHA-pinned and re-used as preflight.
"""
import argparse
import importlib.util
from pathlib import Path
import re
import subprocess
import sys

HOME = Path.home()
BASE = HOME / ".local/share/cafe_app"
PREVIOUS = BASE / "cafe_header_audit_v3_20261104.py"
PREVIOUS_BLOB = "0f1da472340e94a6216941bd5165cc11f2627f18"
SANDBOX = "cafe-upload-security-sandbox-precache-20261104"
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
FIELDS = {
    "MAGICK_TIME_LIMIT": "time",
    "MAGICK_WIDTH_LIMIT": "width",
    "MAGICK_HEIGHT_LIMIT": "height",
    "MAGICK_AREA_LIMIT": "area",
    "MAGICK_MEMORY_LIMIT": "memory",
    "MAGICK_MAP_LIMIT": "map",
    "MAGICK_DISK_LIMIT": "disk",
    "MAGICK_THREAD_LIMIT": "thread",
    "MAGICK_FILE_LIMIT": "file",
}
UNIT = {
    "": 1,
    "B": 1,
    "P": 1,
    "K": 1024,
    "KiB": 1024,
    "KB": 1000,
    "M": 1024**2,
    "MiB": 1024**2,
    "MB": 1000**2,
    "G": 1024**3,
    "GiB": 1024**3,
    "GB": 1000**3,
    "KP": 1024,
    "MP": 1024**2,
}
# Input is a private restored sandbox JPEG; no original bytes or names leave
# the container. The SHA comparison is local and only fixed markers are output.
RUBY_JPEG = r"""
require 'digest'
require 'open3'
begin
  root = '/app/public/uploads/'
  sample = Dir.glob(root + '**/*').sort.find do |path|
    File.file?(path) && !File.symlink?(path) &&
      File.realpath(path).start_with?(root) &&
      %w[.jpg .jpeg].include?(File.extname(path).downcase) &&
      File.size(path) <= 5_000_000
  end
  raise 'No approved sandbox sample' unless sample
  before = Digest::SHA256.file(sample).hexdigest
  _out, _err, status = Open3.capture3(
    'identify', '-format', '%[fx:mean]', sample
  )
  raise 'Bounded JPEG decode failed' unless status.success?
  raise 'Private sample modified' unless
    Digest::SHA256.file(sample).hexdigest == before
  puts 'CANDIDATE_JPEG_DECODE_PASS'
  puts 'CANDIDATE_JPEG_SHA_UNCHANGED'
rescue StandardError => error
  puts 'CANDIDATE_JPEG_STOPPED:' + error.class.name
  exit 9
end
"""


def require(condition, marker):
    if not condition:
        raise RuntimeError("IMAGEMAGICK CANDIDATE BLOCKED: " + marker)


def subprocess_safe(*args, input_data=None, timeout=60):
    try:
        return subprocess.run(
            args, input=input_data, capture_output=True, timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("IMAGEMAGICK CANDIDATE BLOCKED: command timeout")


def to_quantity(raw):
    """Convert ImageMagick's resource units without accepting infinity/unknown."""
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([A-Za-z]*)", raw.strip())
    require(match is not None, "unexpected resource unit")
    number, unit = match.groups()
    require(unit in UNIT, "unsupported resource unit")
    return float(number) * UNIT[unit]


def parse_resource(stdout):
    observed = {}
    for line in stdout.splitlines():
        match = re.fullmatch(r"\s*([A-Za-z]+):\s*(\S+)(?:\s+seconds)?\s*", line)
        if match:
            observed[match.group(1).lower()] = match.group(2)
    return observed


def verify_policy(observed):
    for env_key, expected in POLICY.items():
        label = FIELDS[env_key]
        require(label in observed, "missing " + label + " limit")
        actual = to_quantity(observed[label])
        upper_bound = to_quantity(expected)
        require(actual <= upper_bound * 1.001,
                label + " limit is not effective")
    return True


def self_test():
    assert to_quantity("8KP") == 8192
    assert to_quantity("8000P") == 8000
    assert to_quantity("32MP") == 32 * 1024 * 1024
    assert to_quantity("128MiB") == 128 * 1024 * 1024
    assert parse_resource("Resource limits:\n  Time: 30 seconds\n  Width: 8000P\n") == {
        "time": "30", "width": "8000P"}
    fake = {FIELDS[k]: v for k, v in POLICY.items()}
    assert verify_policy(fake)
    fake["time"] = "unlimited"
    try:
        verify_policy(fake)
    except RuntimeError:
        pass
    else:
        raise AssertionError("unlimited time must fail closed")
    print("IMAGEMAGICK CANDIDATE PARSER TESTS PASS")


def preflight():
    require(PREVIOUS.is_file() and not PREVIOUS.is_symlink(),
            "missing pinned owner audit")
    sha = subprocess_safe("git", "hash-object", str(PREVIOUS), timeout=15)
    require(sha.returncode == 0 and
            sha.stdout.decode().strip() == PREVIOUS_BLOB,
            "owner audit Git blob mismatch")
    spec = importlib.util.spec_from_file_location("cafe_pinned_audit", PREVIOUS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _p, _l, _cluster, _web = module.required_runtime()
    return module


def docker_exec(*command, input_data=None, timeout=60):
    env_args = []
    for key, value in sorted(POLICY.items()):
        env_args.extend(["--env", key + "=" + value])
    return subprocess_safe("docker", "exec", "-i", *env_args, SANDBOX,
                           *command, input_data=input_data, timeout=timeout)


def check():
    preflight()  # SHA/source/network/three-PG isolation; no changes

    limits = docker_exec("identify", "-list", "resource", timeout=25)
    require(limits.returncode == 0, "resource listing failed")
    observed = parse_resource(limits.stdout.decode(errors="replace"))
    verify_policy(observed)
    for key in FIELDS:
        print("CANDIDATE_" + FIELDS[key].upper() + "_LIMIT: " +
              observed[FIELDS[key]], flush=True)
    print("CANDIDATE_RESOURCE_LIMITS_EFFECTIVE_PASS", flush=True)

    # Synthetic in-memory images only; no filesystem output, no untrusted data.
    small = docker_exec("convert", "-size", "8x8", "xc:white",
                        "-format", "%w", "info:", timeout=15)
    require(small.returncode == 0 and small.stdout.strip() == b"8",
            "synthetic small image failed")
    oversized = docker_exec("convert", "-size", "10000x1", "xc:white",
                            "-format", "%w", "info:", timeout=15)
    require(oversized.returncode != 0,
            "synthetic width exceeded candidate cap")
    print("CANDIDATE_SYNTHETIC_WIDTH_ENFORCEMENT_PASS", flush=True)

    result = docker_exec("ruby", "-rlogger", "-",
                         input_data=RUBY_JPEG.encode(), timeout=55)
    lines = {line.strip() for line in result.stdout.decode(
        errors="replace").splitlines()}
    require(result.returncode == 0 and
            {"CANDIDATE_JPEG_DECODE_PASS",
             "CANDIDATE_JPEG_SHA_UNCHANGED"} <= lines,
            "bounded private JPEG decode/immutability failed")
    print("CANDIDATE_JPEG_DECODE_PASS", flush=True)
    print("CANDIDATE_JPEG_SHA_UNCHANGED", flush=True)

    # The pin-based owner audit checks 10 original media hashes and the two
    # working HTTP services. Repeat after the subprocess-only tests.
    preflight()
    print("IMAGE LIMIT CANDIDATE READ-ONLY CHECK COMPLETE", flush=True)
    print("NO RAILS WORKER POLICY CHANGE OR PUBLIC RELEASE APPROVAL",
          flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--self-test", action="store_true")
    options = parser.parse_args()
    if options.self_test:
        self_test()
    else:
        check()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        message = str(error)
        # No private stdout/stderr or exception arguments are displayed.
        if not message.startswith("IMAGEMAGICK CANDIDATE BLOCKED: "):
            message = "IMAGEMAGICK CANDIDATE BLOCKED: internal check"
        print(message, file=sys.stderr)
        raise SystemExit(1)
