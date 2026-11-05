#!/usr/bin/env python3
"""P1.1: prove the pinned Rails runtime without a database or private mounts.

This is a read-only runtime probe, NOT a schema writer.
--probe starts one ephemeral --rm container with --network none and NO
PostgreSQL credentials, original media, source checkout or host ports.
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile

HOME = Path.home()
REPO = HOME / "Рабочий стол/rails_projects/lite/cafe_app"
HEAD = "090b9d37419fcd9f393d8b686ac0f4563ef7b613"
GATE = HOME / ".local/share/cafe_app/cafe_synthetic_p1_target_preflight_v1_20261105.py"
GATE_BLOB = "501914861518530bed0d18c8f1ca08550fe65e4d"
IMAGE = "cafe-legacy-full:node14"
SOURCE_WEB = "cafe-upload-security-headers-mountfix-20261104"
MAX_ARCHIVE = 80 * 1024 * 1024
CANDIDATE_GEM_MOUNTS = {
    "/usr/local/bundle", "/app/vendor/bundle",
    "/usr/local/lib/ruby/gems", "/app/node_modules",
}
TRACKED = {
    "db/schema.rb": "2506954d1ea3e6368eb219956863b2acb91441c8",
    "db/seeds.rb": "dae2eed43c78ff79a14e3bf3e83d59a649803cd4",
    "Gemfile.lock": "06f3924bf211e56d0845bca1f6508bb81bf8a324",
}

def require(value, reason):
    if not value:
        raise RuntimeError("CAFE P1.1 RAILS PROBE STOP: " + reason)

def failure_kind(stderr):
    """Only emit fixed labels, never Docker stderr, paths, env or credentials."""
    value = stderr.decode(errors="replace").lower()
    if "bundler::gemnotfound" in value or "could not find" in value:
        return "ruby_bundle_missing"
    if "gemfile.lock" in value or "bundle install" in value or "bundler" in value:
        return "ruby_bundle_resolution"
    if "permission denied" in value:
        return "filesystem_permission"
    if "read-only file system" in value:
        return "readonly_filesystem"
    if "executable file not found" in value or "not found in $path" in value:
        return "runtime_binary_unavailable"
    if "mount" in value or "volume" in value:
        return "docker_mount_rejected"
    if "no space left on device" in value:
        return "host_space"
    if "network is unreachable" in value or "connection refused" in value:
        return "network_or_dependency"
    return "unspecified_failure"

def run(argv, timeout=35, max_stdout=MAX_ARCHIVE, stage="controlled"):
    # Each stage is a trusted internal literal, not command-derived text.
    require(stage in ("git_metadata", "docker_inspect", "git_archive",
                      "isolated_rails_container"), "invalid internal stage")
    try:
        completed = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("CAFE P1.1 RAILS PROBE STOP: " + stage +
                           " unavailable_or_timeout")
    require(completed.returncode == 0,
            stage + " failed [" + failure_kind(completed.stderr) + "]")
    require(len(completed.stdout) <= max_stdout,
            stage + " output_exceeds_limit")
    return completed.stdout

def git(*args):
    return run(["git", "-C", str(REPO), *args], timeout=40,
               stage="git_metadata").decode().strip()

def preflight():
    require(os.getuid() == 1000 and REPO.is_dir() and
            (REPO / ".git").exists(), "wrong local operator or repository")
    require(GATE.is_file() and not GATE.is_symlink() and
            GATE.stat().st_uid == os.getuid() and
            GATE.stat().st_mode & 0o022 == 0, "pinned P1 gate absent/untrusted")
    require(git("hash-object", str(GATE)) == GATE_BLOB,
            "installed P1 gate blob SHA mismatch")
    require(git("cat-file", "-t", HEAD) == "commit",
            "reviewed Git commit not locally fetched")
    for filename, expected in TRACKED.items():
        require(git("rev-parse", HEAD + ":" + filename) == expected,
                "reviewed Rails source changed: " + filename)
    spec = importlib.util.spec_from_file_location("cafe_verified_p1_local_target", GATE)
    require(spec is not None and spec.loader is not None,
            "cannot import immutable P1 gate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.check()  # Fifth DB STILL empty; four PG, media, SCRAM, ACL, ports validated.
    print("P1.1 EXISTING FIFTH-DB TARGET AND PINNED RAILS SOURCE PASS",
          flush=True)

def allowed_gem_mounts():
    import json
    raw = run(["docker", "inspect", "--type=container", SOURCE_WEB],
              timeout=22, stage="docker_inspect")
    obj = json.loads(raw.decode())
    require(len(obj) == 1 and obj[0]["State"]["Status"] == "running" and
            obj[0]["Config"]["Image"] == IMAGE,
            "trusted Rails QA source container unavailable")
    found = []
    for mount in obj[0]["Mounts"]:
        dest = mount["Destination"]
        if dest not in CANDIDATE_GEM_MOUNTS:
            continue
        require(mount["Type"] == "volume" and mount["RW"] is False and
                mount.get("Name"), "unexpected writable/private Ruby gem mount")
        found.append("type=volume,source={},target={},readonly".format(
            mount["Name"], dest))
    require(len(found) == len(set(found)), "duplicate Ruby dependencies mount")
    return found

def archive_into(dst):
    # The only source is the fixed, publicly tracked Git tree, not a dirty
    # checkout. Reject tar symlinks, links, devices and path traversal.
    archive = run(["git", "-C", str(REPO), "archive",
                   "--format=tar", HEAD], timeout=55, stage="git_archive")
    require(len(archive) < MAX_ARCHIVE, "Git source archive exceeds bound")
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tf:
        members = tf.getmembers()
        require(len(members) <= 10000, "unexpected Git entry count")
        for member in members:
            posix = PurePosixPath(member.name)
            require(not posix.is_absolute() and
                    ".." not in posix.parts and
                    all(part not in ("", ".") for part in posix.parts) and
                    (member.isfile() or member.isdir()),
                    "untrusted Git archive member")
            path = dst.joinpath(*posix.parts)
            require(path == dst or dst in path.parents,
                    "archive member outside temporary source")
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True, mode=0o700)
                continue
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            source = tf.extractfile(member)
            require(source is not None and member.size <= 16 * 1024 * 1024,
                    "Git archive file unavailable/oversized")
            with source, path.open("xb") as out:
                remaining = member.size
                while remaining:
                    chunk = source.read(min(65536, remaining))
                    require(bool(chunk), "short Git archive member")
                    out.write(chunk)
                    remaining -= len(chunk)
    for path, expected in TRACKED.items():
        import hashlib
        value = hashlib.sha1(b"blob " +
            str((dst / path).stat().st_size).encode() + b"\0" +
            (dst / path).read_bytes()).hexdigest()
        require(value == expected, "staged Git source blob mismatch: " + path)

def probe():
    preflight()
    gem_mounts = allowed_gem_mounts()
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="cafe-p1-rails-probe-") as path:
        stage = Path(path)
        source = stage / "git-source"
        source.mkdir(mode=0o700)
        archive_into(source)
        args = [
            "docker", "run", "--rm", "--pull=never",
            "--network=none", "--user=1000:1000", "--workdir=/app",
            "--read-only", "--memory=1024m", "--pids-limit=256",
            "--cap-drop=ALL", "--security-opt=no-new-privileges",
            "--tmpfs=/tmp:rw,nosuid,nodev,size=128m,uid=1000,gid=1000",
            "--env=HOME=/tmp", "--env=BUNDLE_GEMFILE=/app/Gemfile",
            "--env=RAILS_ENV=test", "--env=RUBYOPT=-rlogger",
            "--mount=type=bind,source={},target=/app,readonly".format(source),
        ]
        for mount in gem_mounts:
            args.append("--mount=" + mount)
        args += ["--entrypoint=sh", IMAGE, "-lc",
                 "ruby -v && bundle exec rails -v"]
        output = run(args, timeout=150, max_stdout=8192,
                     stage="isolated_rails_container").decode(errors="replace")
        require(re.search(r"ruby 2\.5\.8(?:p[0-9]+)?\b", output) and
                re.search(r"Rails 6\.0\.", output),
                "legacy Ruby/Rails version mismatch")
        print("P1.1 IMMUTABLE GIT SOURCE / PRIVATE TEMP EXTRACTION PASS",
              flush=True)
        print("P1.1 RUBY 2.5.8 / RAILS 6.0 RUNTIME BOOT PASS",
              flush=True)
        print("P1.1 DOCKER NETWORK NONE / NO DB CREDENTIALS OR PRIVATE MEDIA PASS",
              flush=True)
        print("P1.1 RAILS RUNTIME PROBE PASS — NO DATABASE WRITES",
              flush=True)
        print("NO SCHEMA/SEED LOAD AUTHORIZED", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true", required=True)
    parser.parse_args()
    try:
        probe()
    except Exception as exc:
        msg = str(exc)
        if not msg.startswith("CAFE P1.1 RAILS PROBE STOP:"):
            msg = "CAFE P1.1 RAILS PROBE STOP: internal probe failed"
        print(msg, file=sys.stderr)
        print("Do not write fifth schema or change original containers.",
              file=sys.stderr)
        sys.exit(1)
