#!/usr/bin/env python3
"""Stage a FOURTH, separately networked, private Cafe PostgreSQL 16 test clone.

--check          : read-only preflight; snapshot SHA, owner sandbox and empty targets
--create         : create NEW internal Docker network and NEW PG container, NOT started
--verify-created : read-only inspect of these new resources
--restore        : start ONLY the new DB and restore private SHA-verified QA dump
--verify-running : read-only four PG system IDs / catalog / network / old services

No live/QA/sandbox DB mutations. Never remove or restart anything. No SQL or
media content, emails, credentials, archive paths or cluster IDs are printed.
A new QA web must be independently reviewed before joining this network.
"""
import argparse
import hashlib
from http.client import HTTPConnection
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import time

BASE = Path.home() / ".local/share/cafe_app"
PREFLIGHT = BASE / "cafe_header_audit_v3_20261104.py"
PREFLIGHT_BLOB = "0f1da472340e94a6216941bd5165cc11f2627f18"
SNAP = Path.home() / "Backups/cafe_app/private_runtime/qa_security_snapshot_20261104_sqwulocr"
WEB = "cafe-upload-security-headers-mountfix-20261104"
NETWORK = "cafe-upload-security-e2e-net-20261105"
DATABASE = "cafe-upload-security-e2e-pg-20261105"
ALIAS = "cafe-e2e-postgres"
IMAGE = "postgres:16"
MAX_DUMP_BYTES = 256 * 1024 * 1024

def require(condition, reason):
    if not condition:
        raise RuntimeError("CAFE PRIVATE E2E PG BLOCKED: " + reason)


def run(*args, input_data=None, timeout=35):
    try:
        return subprocess.run(args, input=input_data, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=False, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError("CAFE PRIVATE E2E PG BLOCKED: command timed out")


def docker(*args, timeout=35):
    return run("docker", *args, timeout=timeout)


def inspect(name):
    result = docker("inspect", name, timeout=20)
    require(result.returncode == 0, "expected private Docker object missing")
    return json.loads(result.stdout)[0]


def exists(kind, name):
    if kind == "network":
        args = ("network", "inspect", name)
    else:
        args = ("container", "inspect", name)
    return docker(*args, timeout=15).returncode == 0


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(128 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sql(database, statement):
    p = docker("exec", "--user", "postgres", database,
               "psql", "-X", "-At", "-v", "ON_ERROR_STOP=1",
               "-U", "postgres", "-d", "cafe", "-c", statement, timeout=20)
    require(p.returncode == 0, "private PG SQL audit failed")
    result = p.stdout.decode("utf-8", errors="replace").strip()
    require(bool(re.fullmatch(r"[0-9|]+", result)),
            "unexpected SQL aggregate result")
    return result


def owner_preflight():
    require(PREFLIGHT.is_file() and not PREFLIGHT.is_symlink(),
            "owner SHA-reviewed original preflight missing")
    digest = run("git", "hash-object", str(PREFLIGHT), timeout=15)
    require(digest.returncode == 0 and
            digest.stdout.decode(errors="replace").strip() == PREFLIGHT_BLOB,
            "owner preflight Git blob differs")
    spec = importlib.util.spec_from_file_location("cafe_approved_preflight", PREFLIGHT)
    parent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parent)
    _p, launcher, cluster, original_web = parent.required_runtime()
    require(original_web["State"]["Status"] == "running",
            "original sandbox web not running")
    current = inspect(WEB)
    require(current["State"]["Status"] == "running",
            "headers/magick QA candidate not running")
    require(current["HostConfig"]["ReadonlyRootfs"],
            "headers QA root unexpectedly writable")
    require(not current["HostConfig"]["PortBindings"],
            "headers QA publishes host ports")
    require(set(current["NetworkSettings"]["Networks"]) ==
            {"cafe-upload-security-sandbox-20261104"},
            "headers QA network changed")
    environment = dict(e.split("=", 1) for e in current["Config"]["Env"])
    require(environment.get("PGOPTIONS") ==
            "-c default_transaction_read_only=on",
            "headers QA read-only DB protection missing")
    require(launcher.pgid(launcher.SANDBOX_DB) == cluster,
            "original sandbox PG identity changed")
    return launcher


def validated_dump():
    require(SNAP.is_dir() and not SNAP.is_symlink(),
            "owner private snapshot directory unavailable")
    manifest_file = SNAP / "manifest.json"
    require(manifest_file.is_file() and not manifest_file.is_symlink(),
            "snapshot manifest absent")
    meta = json.loads(manifest_file.read_text(encoding="utf-8"))
    require(meta.get("verified") is True,
            "private backup has no verified marker")
    require(meta.get("qa_product_count") == 20 and
            meta.get("deleted_test_product_21") is True,
            "private DB dump metadata does not match previous QA")
    record = meta.get("database", {})
    require(record.get("archive") == "qa_cafe.dump",
            "unexpected private dump name")
    dump = SNAP / "qa_cafe.dump"
    require(dump.is_file() and not dump.is_symlink() and
            0 < dump.stat().st_size <= MAX_DUMP_BYTES,
            "private database snapshot missing or exceeds cap")
    require(bool(re.fullmatch(r"[0-9a-f]{64}", record.get("sha256", ""))),
            "private snapshot checksum malformed")
    require(sha(dump) == record["sha256"],
            "private snapshot content SHA256 mismatch")
    return dump


def inspect_new(created=True):
    require(exists("network", NETWORK), "new network absent")
    net_result = docker("network", "inspect", NETWORK, timeout=20)
    require(net_result.returncode == 0, "network audit failed")
    network = json.loads(net_result.stdout)[0]
    require(network["Internal"] is True, "test network is not internal-only")
    require(exists("container", DATABASE), "new PG container absent")
    db = inspect(DATABASE)
    require(db["Config"]["Image"] == IMAGE,
            "wrong clone PostgreSQL image")
    require(not db["HostConfig"]["PortBindings"],
            "new PostgreSQL has a host port")
    require(set(db["NetworkSettings"]["Networks"]) == {NETWORK},
            "new PostgreSQL unexpectedly shares QA/live network")
    require(db["HostConfig"]["RestartPolicy"]["Name"] == "no",
            "new PostgreSQL restart policy is not disabled")
    require(db["HostConfig"]["Memory"] == 768 * 1024 * 1024,
            "new PostgreSQL memory cap differs")
    require(db["HostConfig"]["PidsLimit"] == 256,
            "new PostgreSQL PID cap differs")
    tmp = db["HostConfig"].get("Tmpfs") or {}
    require("/var/lib/postgresql/data" in tmp and
            "/var/run/postgresql" in tmp,
            "new PostgreSQL is not tmpfs-only")
    require(not db.get("Mounts"), "private DB has unexpected host binds/volumes")
    require(db["Config"]["Env"].count("POSTGRES_HOST_AUTH_METHOD=trust") == 1,
            "isolated QA DB host authorization differs")
    # Never allow any other container to attach to this network at this stage.
    members = network.get("Containers") or {}
    require(len(members) == 1 and
            next(iter(members.values())).get("Name") == DATABASE,
            "unknown Docker container joined new private PG network")
    if created:
        require(db["State"]["Status"] == "created",
                "new DB is not in created-only state")
    else:
        require(db["State"]["Status"] == "running",
                "new private test PG is not running")
    return db


def check():
    owner_preflight()
    validated_dump()
    require(not exists("network", NETWORK),
            "new private E2E network already exists; do not recreate")
    require(not exists("container", DATABASE),
            "new private E2E PostgreSQL already exists; do not recreate")
    print("FOURTH PRIVATE POSTGRES BASELINE/SNAPSHOT SHA256 PASS", flush=True)
    print("NEW NETWORK/DB TARGETS AVAILABLE — NO CHANGES", flush=True)
    print("PRIVATE E2E POSTGRES CHECK READ-ONLY COMPLETE", flush=True)


def create():
    check()
    p = docker("network", "create", "--internal", NETWORK, timeout=35)
    require(p.returncode == 0, "new isolated Docker network creation failed")
    network = json.loads(docker("network", "inspect", NETWORK).stdout)[0]
    require(network["Internal"] is True and
            not (network.get("Containers") or {}),
            "new test network is not empty and internal")
    result = docker(
        "create", "--name", DATABASE,
        "--network", NETWORK, "--network-alias", ALIAS,
        "--memory", "768m", "--pids-limit", "256",
        "--restart", "no",
        "--tmpfs", "/var/lib/postgresql/data:rw,size=512m,mode=700",
        "--tmpfs", "/var/run/postgresql:rw,size=16m,mode=3775",
        "--env", "POSTGRES_HOST_AUTH_METHOD=trust",
        "--env", "POSTGRES_DB=cafe",
        IMAGE, timeout=55,
    )
    require(result.returncode == 0,
            "new private PG create failed; preserve partial resources")
    inspect_new(created=True)
    owner_preflight()
    print("FOURTH PRIVATE POSTGRES CONTAINER CREATED — NOT STARTED", flush=True)
    print("NEW INTERNAL-ONLY NETWORK / NO HOST PORT / TMPFS ONLY", flush=True)
    print("ORIGINAL THREE POSTGRES + QA/LIVE SERVICES UNCHANGED", flush=True)


def verify_created():
    launcher = owner_preflight()
    validated_dump()
    inspect_new(created=True)
    ids = [launcher.pgid(n) for n in
           (launcher.LIVE_DB, launcher.QA_DB, launcher.SANDBOX_DB)]
    require(len(set(ids)) == 3, "original 3 PostgreSQL identifiers not unique")
    print("FOURTH PRIVATE POSTGRES CREATED-ONLY SECURITY PASS", flush=True)
    print("EXISTING THREE PG IDENTIFIERS AND PRIVATE BACKUP PASS", flush=True)
    print("NO DATABASE OR DOCKER CHANGES", flush=True)


def verify_running():
    launcher = owner_preflight()
    validated_dump()
    inspect_new(created=False)
    original = [launcher.pgid(n) for n in
                (launcher.LIVE_DB, launcher.QA_DB, launcher.SANDBOX_DB)]
    clone = sql(DATABASE, "SELECT system_identifier::text FROM pg_control_system();")
    require(clone.isdigit() and len(set(original + [clone])) == 4,
            "fourth PG not distinct from existing databases")
    require(sql(DATABASE, """
        SELECT COUNT(*), COUNT(*) FILTER (WHERE id=21)
        FROM products;
    """) == "20|0", "new restored product catalog mismatch")
    require(sql(DATABASE, "SELECT COUNT(*) FROM users;") == "2",
            "new restored user baseline mismatch")
    tables = sql(DATABASE, """
        SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';
    """)
    require(tables.isdigit() and int(tables) >= 10,
            "new restored private PG schema incomplete")
    print("FOURTH PRIVATE POSTGRES DISTINCT CLUSTER / CATALOG PASS", flush=True)
    print("QA BACKUP RESTORE: 20 PRODUCTS, 2 USERS, TEST ID21 ABSENT", flush=True)
    print("INTERNAL-ONLY NETWORK / NO HOST PORT / ORIGINAL PG UNCHANGED", flush=True)


def restore():
    verify_created()
    start = docker("start", DATABASE, timeout=45)
    require(start.returncode == 0,
            "new private PG container start failed; preserve evidence")
    require(inspect(DATABASE)["State"]["Status"] == "running",
            "new private PostgreSQL not running after startup")
    ready = False
    for _ in range(50):
        reply = docker("exec", "--user", "postgres", DATABASE,
                       "pg_isready", "-U", "postgres", "-d", "cafe", timeout=12)
        if reply.returncode == 0:
            ready = True
            break
        time.sleep(1)
    require(ready, "new PostgreSQL not ready")
    dump = validated_dump()
    # Read-only access to the private backup on host. Only child database writes.
    with dump.open("rb") as source:
        try:
            proc = subprocess.run(
                ["docker", "exec", "-i", "--user", "postgres",
                 DATABASE, "pg_restore", "--username=postgres",
                 "--dbname=cafe", "--no-owner", "--no-acl",
                 "--exit-on-error", "--single-transaction"],
                stdin=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                check=False, timeout=240,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "CAFE PRIVATE E2E PG BLOCKED: restore timed out; do not retry"
            )
    require(proc.returncode == 0,
            "new private snapshot restore failed; preserve evidence")
    verify_running()
    print("FOURTH PRIVATE POSTGRES RESTORE SUCCESS — ISOLATED", flush=True)
    print("DO NOT ENABLE PUBLIC ACCESS OR CONNECT ORIGINAL RAILS", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    for name in ("check", "create", "verify-created", "restore", "verify-running"):
        modes.add_argument("--" + name, action="store_true")
    options = parser.parse_args()
    try:
        if options.check:
            check()
        elif options.create:
            create()
        elif options.verify_created:
            verify_created()
        elif options.restore:
            restore()
        else:
            verify_running()
    except Exception as exc:
        text = str(exc)
        if not text.startswith("CAFE PRIVATE E2E PG BLOCKED: "):
            text = "CAFE PRIVATE E2E PG BLOCKED: internal verification error"
        print(text, file=sys.stderr, flush=True)
        print("Do not retry create or restore blindly. Preserve isolated evidence.",
              file=sys.stderr, flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
