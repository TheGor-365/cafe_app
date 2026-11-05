#!/usr/bin/env python3
"""Isolate OCI Docker read-only startup failure without any PostgreSQL access.

--diagnose ONLY. Rechecks owner P1, executes ordered disposable Docker tests
with --network=none and --read-only throughout. No secret mounts, database
connections, file writes outside automatically deleted private staging,
existing-container operations, or service port exposure.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HOME = Path.home()
SOURCE = HOME / ".local/share/cafe_app/cafe_synthetic_p1_rails_probe_v3_20261105.py"
SOURCE_SHA = "e41e9a6f20caa5b628073881d80e312ccac3ba8f"
REPO = HOME / "Рабочий стол/rails_projects/lite/cafe_app"
IMAGE = "cafe-legacy-full:node14"
MARKER = b"CAFE_P11_OCI_SHELL_MARKER\n"
BASE = [
    "docker", "run", "--rm", "--pull=never",
    "--network=none", "--read-only", "--user=1000:1000",
    "--memory=1024m", "--pids-limit=256", "--restart=no",
    "--cap-drop=ALL", "--security-opt=no-new-privileges",
]
TMPFS = "--tmpfs=/tmp:rw,nosuid,nodev,size=128m,uid=1000,gid=1000"
SAFE_ENV = [
    "--env=HOME=/tmp", "--env=BUNDLE_GEMFILE=/app/Gemfile",
    "--env=RAILS_ENV=test", "--env=RUBYOPT=-rlogger",
]
# Hardcoded host script and Docker shell command; diagnostic data is REDACTED.
SHELL_MARK = "printf 'CAFE_P11_OCI_SHELL_MARKER\\n'"

def require(value, reason):
    if not value:
        raise RuntimeError("CAFE P1.1 DOCKER START DIAG STOP: " + reason)

def trusted_probe():
    require(os.getuid() == 1000, "expected private QA owner UID")
    require(SOURCE.is_file() and not SOURCE.is_symlink() and
            SOURCE.stat().st_uid == os.getuid() and
            SOURCE.stat().st_mode & 0o022 == 0,
            "immutable P1.1 v3 helper absent/untrusted")
    p = subprocess.run(["git", "-C", str(REPO), "hash-object", str(SOURCE)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=18, check=False)
    require(p.returncode == 0 and p.stdout.decode().strip() == SOURCE_SHA,
            "installed P1.1 helper Git blob differs")
    spec = importlib.util.spec_from_file_location("cafe_p11_verified_runner", SOURCE)
    require(spec is not None and spec.loader is not None,
            "cannot import immutable source helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Same real P1 immutable SHA gate. Quiet the old repeated PASS log spam.
    with redirect_stdout(io.StringIO()):
        module.preflight()
    print("P1.1 DIAG PRECHECK — FIFTH DB EMPTY / FOUR ORIGINAL PG ISOLATED PASS",
          flush=True)
    return module

def case(label, args, expected=MARKER):
    require(label in ("BASE", "TMPFS", "SOURCE_RO", "BUNDLE_CACHE_RO",
                      "LOGIN_SHELL", "RUBY", "BUNDLER"),
            "invalid internal probe phase")
    try:
        result = subprocess.run(args, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=90,
                                check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("CAFE P1.1 DOCKER START DIAG STOP: " +
                           label + " unavailable_or_timeout")
    if result.returncode != 0 or expected not in result.stdout:
        category = runner.failure_kind(result.stderr)
        reason = "OCI_OR_SHELL_ERROR" if MARKER not in result.stdout else "AFTER_SHELL_MARKER"
        raise RuntimeError(
            "CAFE P1.1 DOCKER START DIAG STOP: " + label +
            " [" + reason + " / " + category + "]"
        )
    print("P1.1 DIAG " + label + " PASS", flush=True)

def diagnose():
    global runner
    runner = trusted_probe()
    gem_mounts = runner.allowed_gem_mounts()
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="cafe-p11-docker-ro-diag-") as temp:
        source = Path(temp) / "git-source"
        source.mkdir(mode=0o700)
        runner.archive_into(source)
        print("P1.1 DIAG PINNED GIT ARCHIVE VERIFIED PASS", flush=True)
        source_mount = "--mount=type=bind,source={},target=/app,readonly".format(source)
        shared_mounts = ["--mount=" + item for item in gem_mounts]
        # Every case has NO NETWORK, NO HOST PORT, read-only root, capabilities dropped.
        case("BASE", BASE + ["--entrypoint=sh", IMAGE, "-c", SHELL_MARK])
        case("TMPFS", BASE + [TMPFS, "--entrypoint=sh", IMAGE, "-c", SHELL_MARK])
        case("SOURCE_RO", BASE + [TMPFS, source_mount, "--entrypoint=sh",
                                 IMAGE, "-c", SHELL_MARK])
        case("BUNDLE_CACHE_RO", BASE + [TMPFS, source_mount, *shared_mounts,
                                       "--entrypoint=sh", IMAGE, "-c", SHELL_MARK])
        case("LOGIN_SHELL", BASE + [TMPFS, source_mount, *shared_mounts,
                                    *SAFE_ENV, "--entrypoint=sh", IMAGE,
                                    "-lc", SHELL_MARK])
        case("RUBY", BASE + [TMPFS, source_mount, *shared_mounts, *SAFE_ENV,
                            "--entrypoint=sh", IMAGE, "-lc",
                            SHELL_MARK + " && ruby -v"])
        case("BUNDLER", BASE + [TMPFS, source_mount, *shared_mounts, *SAFE_ENV,
                               "--entrypoint=sh", IMAGE, "-lc",
                               SHELL_MARK + " && bundle --version"])
    print("P1.1 DIAG DOCKER START / READONLY MOUNTS PASS", flush=True)
    print("NO RAILS SCHEMA, POSTGRES, MEDIA OR ORIGINAL SERVICE WRITES", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnose", action="store_true", required=True)
    parser.parse_args()
    try:
        diagnose()
    except Exception as exc:
        reason = str(exc)
        if not reason.startswith("CAFE P1.1 DOCKER START DIAG STOP:"):
            reason = "CAFE P1.1 DOCKER START DIAG STOP: internal diagnostic failed"
        print(reason, file=sys.stderr)
        print("No schema load, no protected container or database changes.",
              file=sys.stderr)
        sys.exit(1)
