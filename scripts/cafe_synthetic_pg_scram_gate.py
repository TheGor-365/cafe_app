#!/usr/bin/env python3
"""Fifth, EMPTY/synthetic-only Cafe PostgreSQL security gate (owner-local).

--check           READ ONLY: owner E2E protection, unique targets, disk/memory
--create          create NEW private secret, NEW internal network, NEW stopped PG
--verify-created  READ ONLY: exact container/network/secret security audit
--bootstrap       start ONLY new fifth PG; verify SCRAM and EMPTY schema
--verify-running  READ ONLY: repeat isolation, 5 distinct PG identities, empty DB

NO dump restore, QA user copy, app attach, DDL/schema load or public ports.
NO writes to existing PG, Rails, original app/media, or project files.
Never retry partial creation or bootstrap; preserve objects for diagnosis.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
import shutil

BASE = Path.home() / ".local/share/cafe_app"
WEB_HELPER = BASE / "cafe_private_e2e_web_recovery_v2_20261105.py"
WEB_HELPER_BLOB = "62e52015dfe7dd5ca15b1c3eabe380a38e7eca0a"
DB_HELPER = BASE / "cafe_private_e2e_postgres_v1_20261105.py"
DB_HELPER_BLOB = "068ac1ac8625c0993cfdc2bc33f4e8d688738e47"
STAGE = BASE / "synthetic_pg_scram_20261105"
SECRET = STAGE / "password"
NETWORK = "cafe-upload-security-synthetic-net-20261105"
PG = "cafe-upload-security-synthetic-pg-20261105"
PGDB = "cafe_synthetic"
PG_IMAGE = "postgres:16"
SECRET_DEST = "/run/secrets/cafe_synthetic_postgres"
PASSWORD_FILE = "POSTGRES_PASSWORD_FILE=" + SECRET_DEST
NETWORK_ALIAS = "cafe-synthetic-postgres"

def require(ok, reason):
    if not ok:
        raise RuntimeError("CAFE SYNTHETIC PG BLOCKED: " + reason)


def run(*args, timeout=35):
    try:
        return subprocess.run(args, capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError("CAFE SYNTHETIC PG BLOCKED: command timeout")


def docker(*args, timeout=35):
    return run("docker", *args, timeout=timeout)


def docker_resource(kind, name):
    command = ["docker", "network" if kind == "network" else "container",
               "inspect", name]
    return run(*command, timeout=15).returncode == 0


def inspect(name):
    result = docker("inspect", name, timeout=20)
    require(result.returncode == 0, "expected Docker resource missing")
    return json.loads(result.stdout)[0]


def net_inspect():
    p = docker("network", "inspect", NETWORK, timeout=20)
    require(p.returncode == 0, "new private network missing")
    return json.loads(p.stdout)[0]


def load_pin(path, expected_blob, symbol):
    require(path.is_file() and not path.is_symlink(),
            "SHA-reviewed existing helper absent")
    x = run("git", "hash-object", str(path), timeout=15)
    require(x.returncode == 0 and
            x.stdout.decode(errors="replace").strip() == expected_blob,
            "SHA-reviewed helper Git blob differs")
    spec = importlib.util.spec_from_file_location(symbol, path)
    require(spec is not None and spec.loader is not None,
            "private helper loading failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_baseline():
    require(os.getuid() == 1000, "owner UID 1000 expected for private QA")
    web = load_pin(WEB_HELPER, WEB_HELPER_BLOB, "reviewed_e2e_rails")
    db = load_pin(DB_HELPER, DB_HELPER_BLOB, "reviewed_fourth_pg")
    fourth, headers, launcher, _source, manifest = web.preflight()
    web.inspect_web(headers, launcher, manifest, "running")
    require(db.validated_dump().is_file(), "protected owner snapshot unavailable")
    original = [
        launcher.pgid(launcher.LIVE_DB),
        launcher.pgid(launcher.QA_DB),
        launcher.pgid(launcher.SANDBOX_DB),
        db.sql(db.DATABASE, "SELECT system_identifier::text FROM pg_control_system();"),
    ]
    require(len(set(original)) == 4 and all(v.isdigit() for v in original),
            "four existing PostgreSQL identities changed")
    require(db.sql(db.DATABASE, "SELECT COUNT(*) FROM products;") == "20",
            "fourth restored QA catalog changed")
    require(db.sql(db.DATABASE, "SELECT COUNT(*) FROM users;") == "2",
            "fourth restored users count changed")
    require(db.sql(db.DATABASE, "SELECT COUNT(*) FROM products WHERE id=21;") == "0",
            "fourth QA deleted test product unexpectedly present")
    return original


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def secret_audit():
    require(STAGE.is_dir() and not STAGE.is_symlink() and
            SECRET.is_file() and not SECRET.is_symlink(),
            "private synthetic credential stage missing")
    require(STAGE.stat().st_uid == 1000 and SECRET.stat().st_uid == 1000,
            "synthetic credential stage owner differs")
    require(STAGE.stat().st_mode & 0o077 == 0,
            "credential parent directory exposes secret to other users")
    require(SECRET.stat().st_mode & 0o022 == 0,
            "credential file is modifiable by other users")
    require(SECRET.stat().st_mode & 0o004 == 0o004,
            "Postgres UID needs read access to read-only mounted secret")
    require(SECRET.stat().st_size in range(48, 129),
            "synthetic password length outside expected range")
    content = SECRET.read_bytes()
    require(b"\n" not in content and b"\r" not in content and
            re.fullmatch(rb"[A-Za-z0-9_-]+", content) is not None,
            "synthetic password format changed")
    return sha(SECRET)


def check_new(expected_status):
    net = net_inspect()
    require(net["Internal"] is True, "new network not Docker internal-only")
    members = {member.get("Name") for member in
               (net.get("Containers") or {}).values()}
    require(members.issubset({PG}),
            "unexpected container attached to new synthetic PG network")
    pg = inspect(PG)
    require(pg["State"]["Status"] == expected_status,
            "synthetic PostgreSQL state differs")
    require(pg["Config"]["Image"] == PG_IMAGE, "synthetic PG image differs")
    require(pg["HostConfig"]["RestartPolicy"]["Name"] == "no",
            "synthetic PG restart policy differs")
    require(pg["HostConfig"]["Memory"] == 768 * 1024 * 1024 and
            pg["HostConfig"]["PidsLimit"] == 256,
            "synthetic PG resource caps differ")
    require(pg["HostConfig"]["ReadonlyRootfs"],
            "synthetic PG rootfs unexpectedly writable")
    require(not pg["HostConfig"]["PortBindings"],
            "synthetic PG publishes a host port")
    require(set(pg["NetworkSettings"]["Networks"]) == {NETWORK},
            "synthetic PG joined a protected network")
    require(not pg["HostConfig"].get("Binds"),
            "synthetic PostgreSQL uses an unmanaged legacy bind")
    tmp = pg["HostConfig"]["Tmpfs"] or {}
    require(set(tmp) == {"/var/lib/postgresql/data",
                         "/var/run/postgresql", "/tmp"},
            "synthetic PG tempfiles are not isolated")
    mounts = pg.get("Mounts") or []
    require(len(mounts) == 1 and
            mounts[0]["Destination"] == SECRET_DEST and
            mounts[0]["Type"] == "bind" and
            mounts[0]["Source"] == str(SECRET) and
            mounts[0]["RW"] is False,
            "unexpected PostgreSQL host path/volume mount")
    env = pg["Config"]["Env"]
    require(len(env) == len(set(x.split("=", 1)[0] for x in env)),
            "duplicate synthetic PG environment keys")
    require(PASSWORD_FILE in env and
            "POSTGRES_HOST_AUTH_METHOD=scram-sha-256" in env and
            "POSTGRES_INITDB_ARGS=--auth-local=peer --auth-host=scram-sha-256" in env and
            "POSTGRES_DB=" + PGDB in env,
            "private synthetic PG initialization policy differs")
    require(not any(e.startswith("POSTGRES_PASSWORD=") for e in env),
            "plain PostgreSQL password leaked in Docker inspect")
    require(not any(m["Destination"].startswith("/app") for m in mounts),
            "protected Rails source unexpectedly mounted")
    secret_audit()
    if expected_status == "running":
        require(members == {PG}, "running synthetic PG must be sole member")
    return pg


def check():
    source_baseline()
    require(not docker_resource("network", NETWORK),
            "synthetic PG network exists; no recreate")
    require(not docker_resource("container", PG),
            "synthetic PG container exists; no recreate")
    require(not STAGE.exists() and not STAGE.is_symlink(),
            "synthetic PG credentials stage exists; no overwrite")
    require(shutil.disk_usage(str(BASE)).free > 50 * 1024 * 1024,
            "insufficient private local staging disk space")
    require(run("docker", "image", "inspect", PG_IMAGE, timeout=20).returncode == 0,
            "reviewed postgres:16 image unavailable locally; no implicit pull")
    print("FIFTH SYNTHETIC PG OWNER SOURCE/FOURTH QA ISOLATION PASS", flush=True)
    print("NEW SCRAM NETWORK/PG/PRIVATE SECRET TARGETS AVAILABLE", flush=True)
    print("SYNTHETIC PG READ-ONLY PREFLIGHT COMPLETE — NO CHANGES", flush=True)


def create():
    check()
    os.umask(0o077)
    STAGE.mkdir(mode=0o700)
    password = secrets.token_urlsafe(48)
    with SECRET.open("xb") as f:
        f.write(password.encode("ascii"))
    # Parent 0700 prevents other HOST users from reaching this host-side file.
    # Inside the isolated database container PostgreSQL runs as UID 999 and
    # needs to read this file for *_FILE initialisation. Only PG container
    # receives the readonly bind, and no other network membership is allowed.
    SECRET.chmod(0o644)
    secret_audit()
    n = docker("network", "create", "--internal", NETWORK, timeout=40)
    require(n.returncode == 0, "synthetic PG Docker network creation failed")
    network = net_inspect()
    require(network["Internal"] is True and
            not (network.get("Containers") or {}),
            "new synthetic PG network not empty/internal")
    r = docker(
        "create", "--name", PG,
        "--network", NETWORK, "--network-alias", NETWORK_ALIAS,
        "--read-only",
        "--memory", "768m", "--pids-limit", "256",
        "--restart", "no",
        "--security-opt", "no-new-privileges",
        "--tmpfs", "/var/lib/postgresql/data:rw,size=512m,mode=700",
        "--tmpfs", "/var/run/postgresql:rw,size=16m,mode=3775",
        "--tmpfs", "/tmp:rw,size=64m,mode=1777",
        "--mount", "type=bind,source={},target={},readonly".format(SECRET, SECRET_DEST),
        "--env", PASSWORD_FILE,
        "--env", "POSTGRES_HOST_AUTH_METHOD=scram-sha-256",
        "--env", "POSTGRES_INITDB_ARGS=--auth-local=peer --auth-host=scram-sha-256",
        "--env", "POSTGRES_DB=" + PGDB,
        PG_IMAGE, timeout=65,
    )
    require(r.returncode == 0, "synthetic PG Docker create failed; preserve all objects")
    check_new("created")
    source_baseline()
    print("FIFTH EMPTY SYNTHETIC POSTGRES CONTAINER CREATED — NOT STARTED", flush=True)
    print("SCRAM AUTH / PRIVATE FILE / INTERNAL NETWORK / NO HOST PORT PASS", flush=True)
    print("EXISTING FOUR POSTGRES AND 3001/3002 UNCHANGED", flush=True)


def verify_created():
    source_baseline()
    check_new("created")
    print("FIFTH SYNTHETIC PG CREATED-ONLY SECURITY PASS", flush=True)
    print("NO DATA RESTORE / NO ORIGINAL DOCKER OR DATABASE CHANGES", flush=True)


def q(sql):
    p = docker("exec", "--user", "postgres", PG, "psql", "-X", "-At",
               "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", PGDB,
               "-c", sql, timeout=20)
    require(p.returncode == 0, "synthetic PG SQL audit failed")
    result = p.stdout.decode(errors="replace").strip()
    require(re.fullmatch(r"[0-9]+|scram-sha-256", result) is not None,
            "unrecognized synthetic DB aggregate result")
    return result


def verify_running():
    identities = source_baseline()
    check_new("running")
    fifth = q("SELECT system_identifier::text FROM pg_control_system();")
    require(fifth.isdigit() and len(set(identities + [fifth])) == 5,
            "fifth PostgreSQL cluster not distinct")
    require(q("SHOW password_encryption;") == "scram-sha-256",
            "PostgreSQL passwords not using SCRAM")
    require(q("""SELECT COUNT(*) FROM pg_hba_file_rules
                WHERE type IN ('host','hostssl','hostnossl')
                  AND auth_method <> 'scram-sha-256';""") == "0",
            "unauthenticated synthetic PG TCP host rule")
    require(q("""SELECT COUNT(*) FROM pg_hba_file_rules
                WHERE type IN ('host','hostssl','hostnossl')
                  AND auth_method = 'scram-sha-256';""") != "0",
            "missing PostgreSQL SCRAM host rules")
    require(q("""SELECT COUNT(*) FROM pg_tables
                WHERE schemaname='public';""") == "0",
            "synthetic PostgreSQL unexpectedly has imported schema")
    require(q("""SELECT COUNT(*) FROM pg_roles
                WHERE rolcanlogin AND rolname <> 'postgres';""") == "0",
            "unexpected synthetic login role")
    print("FIFTH POSTGRES DISTINCT CLUSTER / ZERO DATA TABLES PASS", flush=True)
    print("POSTGRES16 SCRAM ONLY / INTERNAL NETWORK / NO PUBLIC PORT PASS", flush=True)
    print("ORIGINAL FOUR PG AND PRODUCTION/QA REMAIN UNCHANGED", flush=True)


def bootstrap():
    verify_created()
    p = docker("start", PG, timeout=45)
    require(p.returncode == 0,
            "synthetic PG Docker start failed; do not retry or cleanup")
    for _ in range(45):
        if docker("exec", "--user", "postgres", PG, "pg_isready", "-U",
                  "postgres", "-d", PGDB, timeout=8).returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError("CAFE SYNTHETIC PG BLOCKED: fifth PG never became ready")
    verify_running()
    print("FIFTH EMPTY SYNTHETIC POSTGRES BOOTSTRAP PASS", flush=True)
    print("DO NOT ATTACH RAILS OR LOAD SCHEMA UNTIL ROLE/PERMISSION REVIEW", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    for name in ("check", "create", "verify-created", "bootstrap", "verify-running"):
        modes.add_argument("--" + name, action="store_true")
    args = parser.parse_args()
    try:
        if args.check:
            check()
        elif args.create:
            create()
        elif args.verify_created:
            verify_created()
        elif args.bootstrap:
            bootstrap()
        else:
            verify_running()
    except Exception as e:
        message = str(e)
        if not message.startswith("CAFE SYNTHETIC PG BLOCKED:"):
            message = "CAFE SYNTHETIC PG BLOCKED: internal security audit failed"
        print(message, file=sys.stderr, flush=True)
        print("Do not retry failed create/bootstrap, remove or reset protected objects.",
              file=sys.stderr, flush=True)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
