#!/usr/bin/env python3
"""P1 first gate: read-only inspection before a fifth-DB-only Rails schema loader.

Owner runs --check once after fetching the SHA-pinned feature branch.
No Docker create/start/exec SQL writes, file writes, Rails tasks, checkout, ports,
media copying, schema import, fixture import, role changes, or migrations.
This program is NOT the schema loader and deliberately has no write mode.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

HOME = Path.home()
REPO = HOME / "Рабочий стол/rails_projects/lite/cafe_app"
PINNED_SCHEMA_REF = "refs/remotes/origin/feature/cafe-synthetic-schema-readonly-gate-20261105"
SOURCE = {
    "db/schema.rb": "2506954d1ea3e6368eb219956863b2acb91441c8",
    "db/seeds.rb": "dae2eed43c78ff79a14e3bf3e83d59a649803cd4",
    "db/migrate/20261102000100_create_cafe_drink_options.rb":
        "1d0ebdd9f4d7b5d70fb13868da97f76dd722f65e",
}
READONLY_GATE = HOME / ".local/share/cafe_app/cafe_synthetic_schema_readonly_v1_20261105.py"
READONLY_BLOB = "d16a2668ed71c6af3589425ad85178ab6f4be423"
PG = "cafe-upload-security-synthetic-pg-20261105"
NETWORK = "cafe-upload-security-synthetic-net-20261105"
PG_IMAGE = "postgres:16"
PG_DB = "cafe_synthetic"
RAILS_IMAGE = "cafe-legacy-full:node14"
ORIGINAL_WEB = "cafe-upload-security-headers-mountfix-20261104"
SECRET_PATH = HOME / ".local/share/cafe_app/synthetic_pg_scram_20261105/password"

def require(condition, reason):
    if not condition:
        raise RuntimeError("CAFE P1 TARGET PREFLIGHT STOP: " + reason)

def run(cmd, timeout=25):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=timeout, check=False)
    require(result.returncode == 0, "read-only inspection command failed")
    return result.stdout

def git(*args):
    return run(["git", "-C", str(REPO), *args], timeout=22).decode().strip()

def docker_json(*args):
    return json.loads(run(["docker", *args], timeout=25).decode())

def inspect_container(name):
    value = docker_json("inspect", "--type=container", name)
    require(isinstance(value, list) and len(value) == 1,
            "expected named Docker container not found")
    return value[0]

def check_ref_and_readonly_gate():
    require(os.getuid() == 1000 and REPO.is_dir() and
            (REPO / ".git").exists(), "wrong local operator or source checkout")
    require(git("cat-file", "-t", PINNED_SCHEMA_REF) == "commit",
            "reviewed PR54 remote ref missing; fetch without checkout")
    for path, expected in SOURCE.items():
        require(git("rev-parse", PINNED_SCHEMA_REF + ":" + path) == expected,
                "canonical source Git blob changed: " + path)
    require(READONLY_GATE.is_file() and not READONLY_GATE.is_symlink(),
            "previous verified read-only gate unavailable")
    require(READONLY_GATE.stat().st_uid == os.getuid() and
            READONLY_GATE.stat().st_mode & 0o022 == 0,
            "previous read-only gate owner or mode changed")
    require(git("hash-object", str(READONLY_GATE)) == READONLY_BLOB,
            "previous read-only gate does not match verified Git blob")
    # This existing v1 gate itself calls the owner's previously verified v2
    # scoped-role helper, which audits all FIVE clusters, old web/media,
    # expected empty fifth DB, positive/negative SCRAM, and ACL.
    spec = importlib.util.spec_from_file_location("cafe_p1_original_readonly_gate",
                                                  READONLY_GATE)
    require(spec is not None and spec.loader is not None, "cannot import prior gate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.check()
    print("P1 CANONICAL RAILS BLOBS + ORIGINAL FOUR PG/MEDIA AUDIT PASS", flush=True)

def check_fifth_docker_scope():
    network = docker_json("network", "inspect", NETWORK)
    require(len(network) == 1, "wrong number of private PG networks")
    net = network[0]
    require(net["Name"] == NETWORK and net["Internal"] is True,
            "fifth PG Docker network is not dedicated internal")
    members = {entry.get("Name") for entry in
               (net.get("Containers") or {}).values()}
    require(members == {PG}, "fifth network has unexpected members")
    pg = inspect_container(PG)
    require(pg["Name"].lstrip("/") == PG and
            pg["State"]["Status"] == "running" and
            pg["Config"]["Image"] == PG_IMAGE, "wrong synthetic PG identity/state")
    host = pg["HostConfig"]
    require(host["ReadonlyRootfs"] is True and
            host["Memory"] == 768 * 1024 * 1024 and
            host["PidsLimit"] == 256 and
            host["RestartPolicy"]["Name"] == "no",
            "fifth PG isolation/resource limits changed")
    require(not host.get("PortBindings") and
            set(pg["NetworkSettings"]["Networks"]) == {NETWORK},
            "host port or foreign network unexpectedly attached")
    require(not host.get("Binds") and
            set((host.get("Tmpfs") or {})) ==
            {"/var/lib/postgresql/data", "/var/run/postgresql", "/tmp"},
            "fifth PG mounts changed")
    mounts = pg["Mounts"]
    require(len(mounts) == 1 and mounts[0]["Type"] == "bind" and
            mounts[0]["Source"] == str(SECRET_PATH) and
            mounts[0]["Destination"] == "/run/secrets/cafe_synthetic_postgres" and
            mounts[0]["RW"] is False, "fifth PG private credential mount changed")
    env = pg["Config"]["Env"]
    require("POSTGRES_HOST_AUTH_METHOD=scram-sha-256" in env and
            "POSTGRES_INITDB_ARGS=--auth-local=peer --auth-host=scram-sha-256" in env and
            "POSTGRES_DB=" + PG_DB in env and
            not any(item.startswith("POSTGRES_PASSWORD=") for item in env),
            "fifth PG SCRAM/credential policy changed")
    # SQL is read-only and uses only local peer on the known fifth container.
    sql = "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';"
    result = run(["docker", "exec", "--user", "postgres", PG,
                  "psql", "-X", "-At", "-v", "ON_ERROR_STOP=1",
                  "-U", "postgres", "-d", PG_DB, "-c", sql], timeout=20)
    require(result.decode().strip() == "0", "fifth DB public schema not empty")
    print("P1 FIFTH CLUSTER RUNNING / INTERNAL / NO PORT / EMPTY SCHEMA PASS", flush=True)

def check_rails_runner_availability():
    # Image inspection only: never start Rails or attach to the fifth PG here.
    image = docker_json("image", "inspect", RAILS_IMAGE)
    require(len(image) == 1 and
            image[0].get("RepoTags") is not None and
            RAILS_IMAGE in image[0]["RepoTags"],
            "known legacy Rails image unavailable; no schema writer approved")
    original = inspect_container(ORIGINAL_WEB)
    require(original["State"]["Status"] == "running" and
            original["Config"]["Image"] == RAILS_IMAGE,
            "original isolated Rails source container changed")
    require(original["HostConfig"]["ReadonlyRootfs"] is True and
            not original["HostConfig"].get("PortBindings"),
            "original QA source isolation differs")
    require(all(m["Destination"] != "/app/db/schema.rb" or not m["RW"]
                for m in original["Mounts"]),
            "source schema mount is unexpectedly writable")
    print("P1 LEGACY RAILS IMAGE / SOURCE QA INSPECTION PASS", flush=True)

def check():
    check_ref_and_readonly_gate()
    check_fifth_docker_scope()
    check_rails_runner_availability()
    print("P1 LOCAL TARGET PREFLIGHT READ-ONLY PASS — NO WRITES", flush=True)
    print("NO SCHEMA LOAD / FIXTURES / RAILS ATTACHMENT AUTHORIZED", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", required=True, action="store_true")
    parser.parse_args()
    try:
        check()
    except Exception as exc:
        reason = str(exc)
        if not reason.startswith("CAFE P1 TARGET PREFLIGHT STOP:"):
            reason = "CAFE P1 TARGET PREFLIGHT STOP: internal audit failed"
        print(reason, file=sys.stderr)
        print("Do not alter Docker, Rails, schema, users, media, or branches.",
              file=sys.stderr)
        sys.exit(1)
