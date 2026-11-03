#!/usr/bin/env python3
"""Drive real HTTP multipart Rails security tests exclusively in sandbox web.

--check: inspect only. --run: send synthetic valid and invalid avatar uploads
over actual sandbox localhost HTTP, with real CSRF cookies and SQL/file checks.

This is NEVER aimed at 3001/3002 host ports. No public URLs, no real users.
"""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path.home() / ".local/share/cafe_app"
LAUNCHER = ROOT / "cafe_sandbox_rails_20261104.py"
RUBY = ROOT / "cafe_sandbox_multipart_probe_20261104.rb"
RUBY_BLOB = "PLACEHOLDER"
NEW = "cafe-upload-security-sandbox-rails-20261104"
SANDBOX_DB = "cafe-upload-security-sandbox-pg-20261104"
SANDBOX_NET = "cafe-upload-security-sandbox-20261104"
SANDBOX_MEDIA = ROOT / "uploads_security_sandbox_20261104"


def require(value, reason):
    if not value:
        raise RuntimeError("SANDBOX HTTP TEST BLOCKED: " + reason)


def launcher():
    require(LAUNCHER.is_file() and not LAUNCHER.is_symlink(),
            "sandbox Rails launch helper absent")
    spec = importlib.util.spec_from_file_location("cafe_sandbox_launcher", LAUNCHER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(module.NEW_WEB == NEW and module.SANDBOX_DB == SANDBOX_DB,
            "loaded launcher points elsewhere")
    return module


def ruby_blob():
    require(RUBY.is_file() and not RUBY.is_symlink(),
            "reviewed multipart Ruby test fixture missing")
    result = subprocess.run(
        ["git", "hash-object", str(RUBY)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, check=True)
    require(result.stdout.strip() == RUBY_BLOB, "Ruby test fixture blob mismatch")
    return RUBY.read_bytes()


def check():
    app = launcher()
    app.audit()  # exact QA/live network isolation and original source check
    require(app.object_exists(NEW), "sandbox Rails container missing")
    rails = app.inspect(NEW)
    require(rails["State"]["Status"] == "running",
            "sandbox Rails not started")
    require(set(rails["NetworkSettings"]["Networks"]) == {SANDBOX_NET},
            "sandbox Rails network changed")
    require(not rails["HostConfig"]["PortBindings"],
            "sandbox Rails has published host port")
    mounts = {m["Destination"]: m for m in rails["Mounts"]}
    require(mounts["/app/public/uploads"]["Source"] ==
            str(SANDBOX_MEDIA) and mounts["/app/public/uploads"]["RW"],
            "multipart tests could write into wrong uploads directory")
    require(mounts["/app"]["RW"] is False,
            "application source directory writable")
    require("/run/secrets/cafe_pg_password" not in mounts,
            "sandbox container unexpectedly has live secret mount")
    new_env = dict(i.split("=", 1) for i in rails["Config"]["Env"])
    require(new_env["DATABASE_URL"] == app.SANDBOX_URL,
            "sandbox Rails target database changed")
    require(new_env["BUNDLE_GEMFILE"] == "/app/Gemfile",
            "patched Gemfile not active")
    expected = app.pgid(SANDBOX_DB)
    require(expected.isdigit() and expected not in
            (app.pgid(app.QA_DB), app.pgid(app.LIVE_DB)),
            "sandbox PostgreSQL identity not distinct")

    ruby = ruby_blob()
    require(b"QaMultipartClient" in ruby and
            b"SANDBOX REAL HTTP MULTIPART SECURITY PASS" in ruby,
            "Ruby test fixture lacks required checks")
    baseline = app.psql(SANDBOX_DB,
                        "SELECT COUNT(*), COUNT(*) FILTER (WHERE id=21) FROM products;")
    require(baseline == "20|0", "sandbox catalog changed before test")
    print("SANDBOX MULTIPART ISOLATION AND RUBY SHA PASS", flush=True)
    return app, expected, ruby


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--run", action="store_true")
    args = parser.parse_args()
    try:
        app, expected, ruby = check()
        if args.check:
            print("SANDBOX MULTIPART CHECK COMPLETE — NO WRITES", flush=True)
            return
        print("BEGIN REAL HTTP MULTIPART TESTS IN ISOLATED SANDBOX", flush=True)
        probe = subprocess.run(
            ["docker", "exec", "-i",
             "--env", "EXPECTED_SANDBOX_CLUSTER=" + expected,
             NEW, "bundle", "exec", "rails", "runner", "-"],
            input=ruby,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=240,
        )
        # Do not print raw error bodies or test passwords; only safe Rails summaries.
        stdout = probe.stdout.decode(errors="replace")
        if probe.returncode != 0:
            print("MULTIPART PROBE NONZERO EXIT:", probe.returncode,
                  file=sys.stderr, flush=True)
            print("PROBE OUTPUT (truncated):\n" + stdout[-2500:],
                  file=sys.stderr)
            stderr = probe.stderr.decode(errors="replace")
            print("PROBE DIAGNOSTICS (last 1200 chars):\n" + stderr[-1200:],
                  file=sys.stderr)
            raise RuntimeError("multipart probe failed (sandbox only)")
        require("SANDBOX REAL HTTP MULTIPART SECURITY PASS" in stdout,
                "Ruby suite missing final success marker")
        print(stdout.strip(), flush=True)

        require(app.http(3001, "/info")[0] == 200 and
                app.http(3002, "/menu")[0] == 200,
                "live or QA HTTP failed after sandbox-only testing")
        count = app.psql(SANDBOX_DB,
            "SELECT COUNT(*) FROM products;")
        require(count == "20", "sandbox catalog changed during upload tests")
        print("PRODUCTION 3001 / PATCHED QA 3002 STILL HTTP 200", flush=True)
        print("SANDBOX MULTIPART TEST COMMAND COMPLETE", flush=True)
    except Exception as exc:
        print("SANDBOX MULTIPART STOPPED:", type(exc).__name__,
              str(exc)[:350], file=sys.stderr, flush=True)
        print("Do not delete or overwrite original QA/production resources.",
              file=sys.stderr, flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
