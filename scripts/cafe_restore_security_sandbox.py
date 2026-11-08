#!/usr/bin/env python3
"""Restore verified private QA snapshot to a NEW, isolated disposable sandbox.

--check: read-only verification of backup SHA256, tar member safety and Docker.
--restore: create separate private QA-media copy, internal Docker network and
           temporary PostgreSQL 16 with tmpfs data; restore and verify archives.

Never modifies the live/QA application, their databases, their uploads,
Docker volumes, Git working tree or QA proxy. Never removes existing objects.
No host ports are published. The restored DB contains copied test accounts:
never attach it to public networks or export it to shared services.
"""
import argparse
import hashlib
from http.client import HTTPConnection
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import time

HOME = Path.home()
SNAP = HOME / "Backups/cafe_app/private_runtime/qa_security_snapshot_20261104_sqwulocr"
MEDIA = HOME / ".local/share/cafe_app/uploads_security_sandbox_20261104"
NETWORK = "cafe-upload-security-sandbox-20261104"
DATABASE = "cafe-upload-security-sandbox-pg-20261104"
QA_DB = "cafe-upload-qa-pg-20261103"
LIVE_DB = "cafe-app-db"
QA_WEB = "cafe-app-patched-qa-candidate-20261104"
LIVE_WEB = "cafe-app-local-3001-web"
QA_PROXY = "cafe-upload-qa-proxy-patched-20261104"
PG_IMAGE = "postgres:16"
ARCHIVE_PREFIX = "patched_qa_uploads"
MAX_ENTRIES = 3000
MAX_UNCOMPRESSED = 250 * 1024 * 1024


def require(condition, reason):
    if not condition:
        raise RuntimeError("SANDBOX BLOCKED: " + reason)


def cmd(*args, stdin=None, stdout=subprocess.PIPE):
    return subprocess.run(args, check=True, stdin=stdin,
                          stdout=stdout, stderr=subprocess.PIPE)


def docker(*args, stdin=None, stdout=subprocess.PIPE):
    return cmd("docker", *args, stdin=stdin, stdout=stdout)


def out(*args):
    return cmd(*args).stdout.decode(errors="replace").strip()


def inspect(name):
    return json.loads(docker("inspect", name).stdout.decode())[0]


def exists_container(name):
    return subprocess.run(["docker", "container", "inspect", name],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def exists_network(name):
    return subprocess.run(["docker", "network", "inspect", name],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def sql(db, statement):
    return docker("exec", "--user", "postgres", db, "psql",
                  "-X", "-At", "-U", "postgres", "-d", "cafe",
                  "-c", statement).stdout.decode().strip()


def sha256(path):
    hash_value = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(128 * 1024), b""):
            hash_value.update(block)
    return hash_value.hexdigest()


def http_status(port, path):
    conn = HTTPConnection("127.0.0.1", port, timeout=8)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        response.read()
        return response.status
    finally:
        conn.close()


def load_manifest():
    require(SNAP.is_dir() and not SNAP.is_symlink(),
            "private verified snapshot directory unavailable")
    manifest_file = SNAP / "manifest.json"
    require(manifest_file.is_file() and not manifest_file.is_symlink(),
            "snapshot manifest missing")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    require(manifest.get("verified") is True, "snapshot was not verified")
    require(manifest.get("qa_product_count") == 20 and
            manifest.get("deleted_test_product_21") is True,
            "snapshot catalog differs")
    files = {}
    for field in ("database", "old_uploads", "patched_uploads"):
        record = manifest.get(field, {})
        name = record.get("archive", "")
        require(isinstance(name, str) and name in (
            "qa_cafe.dump", "qa_uploads_previous.tar.gz",
            "qa_uploads_patched.tar.gz"),
            "unexpected snapshot archive filename")
        path = SNAP / name
        require(path.is_file() and not path.is_symlink(),
                "missing snapshot archive " + name)
        actual = sha256(path)
        require(actual == record.get("sha256"),
                "snapshot SHA256 mismatch for " + name)
        files[field] = path
    require(files["database"].name == "qa_cafe.dump" and
            files["patched_uploads"].name == "qa_uploads_patched.tar.gz",
            "snapshot manifest archive labels differ")
    return manifest, files


def archive_manifest(path, prefix=ARCHIVE_PREFIX):
    """Validate every tar name, type, payload digest, size and collision."""
    result = {}
    size = 0
    with tarfile.open(path, "r:gz") as tar:
        for member in tar:
            raw = member.name
            require(raw == prefix or raw.startswith(prefix + "/"),
                    "archive entry outside expected root")
            rel = raw[len(prefix):].lstrip("/")
            name = PurePosixPath(rel)
            require((not rel or
                     (not name.is_absolute() and
                      all(part not in ("", ".", "..") for part in name.parts))),
                    "invalid archive path")
            require(rel not in result, "duplicate archive entry")
            require(len(result) < MAX_ENTRIES, "archive has too many entries")
            if member.isdir():
                result[rel] = ("dir",)
            elif member.isfile():
                require(member.size >= 0 and member.size <= MAX_UNCOMPRESSED,
                        "archive file size unsafe")
                size += member.size
                require(size <= MAX_UNCOMPRESSED, "media archive too large")
                stream = tar.extractfile(member)
                require(stream is not None, "archive file unreadable")
                with stream:
                    h = hashlib.sha256()
                    total = 0
                    for block in iter(lambda: stream.read(128 * 1024), b""):
                        h.update(block)
                        total += len(block)
                    require(total == member.size,
                            "truncated file in media archive")
                result[rel] = ("file", member.size, h.hexdigest())
            else:
                raise RuntimeError("SANDBOX BLOCKED: unsupported archive entry type")
    require(result.get("") == ("dir",), "archive root missing")
    return result


def disk_inventory(root):
    result = {"": ("dir",)}
    for item in sorted(root.rglob("*")):
        require(not item.is_symlink(), "media contains a symlink")
        rel = item.relative_to(root).as_posix()
        if item.is_dir():
            result[rel] = ("dir",)
        elif item.is_file():
            result[rel] = ("file", item.stat().st_size, sha256(item))
        else:
            raise RuntimeError("SANDBOX BLOCKED: unsupported media entry")
    return result


def extract_media(archive_path, target, expected):
    require(not target.exists() and not target.is_symlink(),
            "sandbox media directory already exists")
    target.mkdir(mode=0o700)
    with tarfile.open(archive_path, "r:gz") as tar:
        for item in tar:
            rel = item.name[len(ARCHIVE_PREFIX):].lstrip("/")
            require(rel in expected, "unexpected archive entry at extraction")
            dest = target / rel
            if item.isdir():
                dest.mkdir(parents=True, exist_ok=True, mode=0o700)
                dest.chmod(0o700)
            else:
                require(item.isfile(), "unsafe non-regular media entry")
                dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                require(not dest.exists() and not dest.is_symlink(),
                        "sandbox filename already occupied")
                stream = tar.extractfile(item)
                require(stream is not None, "archive file unavailable")
                with stream, dest.open("xb") as output:
                    shutil.copyfileobj(stream, output, length=128 * 1024)
                dest.chmod(0o600)
    require(disk_inventory(target) == expected,
            "restored media SHA256 inventory mismatch")
    return sum(v[0] == "file" for v in expected.values())


def verify_live():
    for container in (LIVE_DB, QA_DB, LIVE_WEB, QA_WEB, QA_PROXY):
        require(inspect(container)["State"]["Status"] == "running",
                "existing site/DB unexpectedly stopped: " + container)
    qa = inspect(QA_WEB)
    qa_proxy = inspect(QA_PROXY)
    require(set(qa["NetworkSettings"]["Networks"]) ==
            {"cafe-upload-qa-net-20261103"}, "QA web network changed")
    require(set(qa_proxy["NetworkSettings"]["Networks"]) ==
            {"cafe-upload-qa-net-20261103",
             "cafe-upload-qa-access-20261103"},
            "QA proxy network changed")
    require(NETWORK not in inspect(LIVE_WEB)["NetworkSettings"]["Networks"],
            "production connected to sandbox")
    require(http_status(3001, "/info") == 200 and
            http_status(3002, "/menu") == 200,
            "main or patched QA HTTP unhealthy")
    qa_id = sql(QA_DB, "SELECT system_identifier::text FROM pg_control_system();")
    live_id = sql(LIVE_DB, "SELECT system_identifier::text FROM pg_control_system();")
    require(qa_id.isdigit() and live_id.isdigit() and qa_id != live_id,
            "QA and production database identity not distinct")
    return qa_id, live_id


def preflight():
    manifest, files = load_manifest()
    expected = archive_manifest(files["patched_uploads"])
    require(sum(x[0] == "file" for x in expected.values()) ==
            manifest["patched_uploads"]["files"],
            "patched media archive file count differs")
    previous = archive_manifest(files["old_uploads"], "old_qa_uploads")
    require(sum(x[0] == "file" for x in previous.values()) ==
            manifest["old_uploads"]["files"],
            "previous media archive count differs")
    qa_id, live_id = verify_live()
    require(not MEDIA.exists() and not MEDIA.is_symlink(),
            "sandbox media already exists; do not overwrite")
    require(not exists_network(NETWORK), "sandbox network already exists")
    require(not exists_container(DATABASE), "sandbox DB container already exists")
    docker("image", "inspect", PG_IMAGE)
    free = shutil.disk_usage(str(MEDIA.parent)).free
    media_bytes = sum(x[1] for x in expected.values() if x[0] == "file")
    require(free > media_bytes * 3 + 100 * 1024 * 1024,
            "insufficient free space for private media clone")
    # Read listing, not data; without restoring any active DB.
    with files["database"].open("rb") as f:
        listing = docker("exec", "-i", "--user", "postgres", QA_DB,
                         "pg_restore", "--list", stdin=f).stdout.decode()
    require(" TABLE DATA " in listing and " TABLE " in listing,
            "PostgreSQL backup listing invalid")
    print("QA/LIVE POSTGRESQL CLUSTERS DISTINCT", flush=True)
    print("BACKUP DATABASE + BOTH MEDIA ARCHIVES SHA256 VERIFIED", flush=True)
    print("PATCHED MEDIA ARCHIVE FILES:",
          sum(v[0] == "file" for v in expected.values()), flush=True)
    print("LOCALHOST 3001 & 3002 HTTP 200", flush=True)
    print("ISOLATED RESTORE PREFLIGHT PASS", flush=True)
    return files, expected, qa_id, live_id


def restore():
    files, expected, qa_id, live_id = preflight()
    os.umask(0o077)
    copied = extract_media(files["patched_uploads"], MEDIA, expected)
    print("SANDBOX MEDIA RESTORED & SHA256 MATCH:", copied, flush=True)

    docker("network", "create", "--internal", NETWORK)
    network_info = json.loads(docker("network", "inspect", NETWORK).stdout.decode())[0]
    require(network_info["Internal"] is True, "new sandbox network not internal")

    docker(
        "run", "-d", "--name", DATABASE, "--network", NETWORK,
        "--network-alias", "cafe-app-db",
        "--memory", "768m", "--pids-limit", "256",
        "--restart", "no",
        "--tmpfs", "/var/lib/postgresql/data:rw,size=512m,mode=700",
        "--tmpfs", "/var/run/postgresql:rw,size=16m,mode=3775",
        "--env", "POSTGRES_HOST_AUTH_METHOD=trust",
        "--env", "POSTGRES_DB=cafe",
        PG_IMAGE,
    )
    instance = inspect(DATABASE)
    require(instance["State"]["Status"] == "running", "sandbox DB failed to start")
    require(set(instance["NetworkSettings"]["Networks"]) == {NETWORK},
            "sandbox DB connected outside isolated network")
    require(not instance["HostConfig"]["PortBindings"],
            "sandbox DB exposes a host port")

    ready = False
    for _ in range(50):
        status = subprocess.run(
            ["docker", "exec", "--user", "postgres", DATABASE,
             "pg_isready", "-U", "postgres", "-d", "cafe"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if status.returncode == 0:
            ready = True
            break
        time.sleep(1)
    require(ready, "sandbox PostgreSQL readiness timeout")

    with files["database"].open("rb") as f:
        docker("exec", "-i", "--user", "postgres", DATABASE,
               "pg_restore", "--username=postgres", "--dbname=cafe",
               "--no-owner", "--no-acl", "--exit-on-error",
               "--single-transaction", stdin=f)
    print("SANDBOX POSTGRES RESTORE COMPLETED", flush=True)

    new_id = sql(DATABASE,
        "SELECT system_identifier::text FROM pg_control_system();")
    require(new_id.isdigit() and new_id not in (qa_id, live_id),
            "restored sandbox cluster is not distinct")

    count = sql(DATABASE,
        "SELECT COUNT(*), COUNT(*) FILTER (WHERE id=21) FROM products;")
    require(count == "20|0", "sandbox product catalog mismatch")
    tables = sql(DATABASE,
        "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';")
    require(tables.isdigit() and int(tables) >= 10,
            "restored sandbox schema incomplete")
    require(disk_inventory(MEDIA) == expected, "sandbox media changed")

    verify_live()
    print("SANDBOX POSTGRES ISOLATED / 20 PRODUCTS / ID21 ABSENT", flush=True)
    print("PRODUCTION 3001 & PATCHED QA 3002 UNCHANGED", flush=True)
    print("ISOLATED QA DATABASE + MEDIA RESTORE VERIFIED", flush=True)
    print("SANDBOX RESTORE COMPLETE — NO HTTP UPLOADS PERFORMED", flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--restore", action="store_true")
    args = p.parse_args()
    try:
        if args.check:
            preflight()
            print("NO SANDBOX OBJECTS CREATED", flush=True)
        else:
            restore()
    except Exception as e:
        print("SANDBOX RESTORE STOPPED:", type(e).__name__, str(e)[:350],
              file=sys.stderr, flush=True)
        print("Do not retry, remove or overwrite partially created sandbox "
              "resources. Diagnose them separately.", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
