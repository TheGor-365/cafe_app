#!/usr/bin/env python3
"""Audit and back up isolated cafe QA PostgreSQL and BOTH QA uploads trees.

--check: read-only prerequisites, including current patched QA port 3002.
--snapshot: preflight, create NEW private timestamped directory, pg_dump custom
            format, archive both current and previous QA media, verify database
            archive/table entries, all file SHA256, and source inventory unchanged.

No SQL writes, Git operations, production backups, Docker restarts, container
changes, uploads, internet, secret output or file restores are performed.
This is a QA consistency checkpoint, not an automated rollback implementation.
"""
import argparse
import hashlib
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

HOME = Path.home()
BACKUP_BASE = HOME / "Backups/cafe_app/private_runtime"
OLD_UPLOADS = HOME / ".local/share/cafe_app/uploads_qa_20261103"
PATCHED_UPLOADS = HOME / ".local/share/cafe_app/uploads_patched_qa_20261104"
OLD_WEB = "cafe-app-uploads-qa-avatar-20261103"
PATCHED_WEB = "cafe-app-patched-qa-candidate-20261104"
OLD_PROXY = "cafe-upload-qa-proxy-avatar-20261103"
PATCHED_PROXY = "cafe-upload-qa-proxy-patched-20261104"
QA_DB = "cafe-upload-qa-pg-20261103"
LIVE_DB = "cafe-app-db"
LIVE_WEB = "cafe-app-local-3001-web"
QA_NET = "cafe-upload-qa-net-20261103"
ACCESS_NET = "cafe-upload-qa-access-20261103"


def run(*args, capture=True, stdin=None, stdout=None):
    return subprocess.run(
        args, check=True, stdin=stdin,
        stdout=(stdout if stdout is not None else
                (subprocess.PIPE if capture else subprocess.DEVNULL)),
        stderr=subprocess.PIPE,
    )


def docker(*args, capture=True, stdin=None, stdout=None):
    return run("docker", *args, capture=capture, stdin=stdin, stdout=stdout)


def inspect(name):
    return json.loads(docker("inspect", name).stdout.decode())[0]


def require(condition, message):
    if not condition:
        raise RuntimeError("SNAPSHOT BLOCKED: " + message)


def sql(db, statement):
    return docker(
        "exec", "--user", "postgres", db,
        "psql", "-X", "-At", "-U", "postgres", "-d", "cafe", "-c", statement,
    ).stdout.decode().strip()


def http(port, path):
    conn = HTTPConnection("127.0.0.1", port, timeout=8)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        response.read()
        return response.status
    finally:
        conn.close()


def sha256_stream(f):
    h = hashlib.sha256()
    for block in iter(lambda: f.read(128 * 1024), b""):
        h.update(block)
    return h.hexdigest()


def sha256_file(path):
    with Path(path).open("rb") as f:
        return sha256_stream(f)


def inventory(root):
    require(root.is_dir() and not root.is_symlink(),
            "QA uploads directory missing/symlinked: " + str(root))
    result = {"": ("dir",)}
    for item in sorted(root.rglob("*")):
        require(not item.is_symlink(), "symlink in QA media: " + str(item))
        name = item.relative_to(root).as_posix()
        if item.is_dir():
            result[name] = ("dir",)
        elif item.is_file():
            result[name] = ("file", item.stat().st_size, sha256_file(item))
        else:
            raise RuntimeError("Unsupported QA media entry " + str(item))
    return result


def footprint(manifest):
    return sum(v[1] for v in manifest.values() if v[0] == "file")


def preflight():
    require(BACKUP_BASE.is_dir() and not BACKUP_BASE.is_symlink(),
            "private backup base is unavailable")
    # Snapshot subdirectory is always mode 0700 even if parent exists as 0755.

    names = [OLD_WEB, PATCHED_WEB, OLD_PROXY, PATCHED_PROXY,
             QA_DB, LIVE_DB, LIVE_WEB]
    info = {n: inspect(n) for n in names}
    for n in (OLD_WEB, PATCHED_WEB, PATCHED_PROXY, QA_DB, LIVE_DB, LIVE_WEB):
        require(info[n]["State"]["Status"] == "running",
                n + " must be running")
    require(info[OLD_PROXY]["State"]["Status"] == "exited",
            "old rollback QA proxy should be stopped")

    net = lambda x: set(x["NetworkSettings"]["Networks"])
    require(net(info[OLD_WEB]) == {QA_NET}, "old QA web network changed")
    require(net(info[PATCHED_WEB]) == {QA_NET}, "patched QA web network changed")
    require(net(info[QA_DB]) == {QA_NET}, "QA PostgreSQL network changed")
    require(net(info[PATCHED_PROXY]) == {QA_NET, ACCESS_NET},
            "new QA proxy network changed")
    require(QA_NET not in net(info[LIVE_WEB]) and
            QA_NET not in net(info[LIVE_DB]), "live container on QA network")

    proxy = info[PATCHED_PROXY]
    mapping = proxy["HostConfig"]["PortBindings"]["3002/tcp"]
    require(len(mapping) == 1 and mapping[0]["HostIp"] == "127.0.0.1"
            and mapping[0]["HostPort"] == "3002",
            "QA proxy no longer loopback-only")
    require(PATCHED_WEB in " ".join(proxy["Config"].get("Cmd") or []),
            "QA proxy does not point to patched Rails")

    mounted_old = {m["Destination"]: m for m in info[OLD_WEB]["Mounts"]}
    mounted_new = {m["Destination"]: m for m in info[PATCHED_WEB]["Mounts"]}
    for web, mounts, expected_media in [
        (OLD_WEB, mounted_old, OLD_UPLOADS),
        (PATCHED_WEB, mounted_new, PATCHED_UPLOADS),
    ]:
        require(info[web]["HostConfig"]["ReadonlyRootfs"],
                web + " root not readonly")
        require(not mounts["/app"]["RW"], web + " /app source unexpectedly writable")
        require(mounts["/app/public/uploads"]["RW"] and
                mounts["/app/public/uploads"]["Source"] == str(expected_media),
                web + " QA uploads mount unexpected")

    qa_id = sql(QA_DB, "SELECT system_identifier::text FROM pg_control_system();")
    live_id = sql(LIVE_DB, "SELECT system_identifier::text FROM pg_control_system();")
    require(qa_id.isdigit() and live_id.isdigit() and qa_id != live_id,
            "QA PostgreSQL not distinct from production")
    counts = sql(QA_DB,
        "SELECT COUNT(*), COUNT(*) FILTER (WHERE id = 21) FROM products;")
    require(counts == "20|0", "QA product counts differ from accepted baseline")
    require(http(3001, "/info") == 200 and http(3002, "/menu") == 200,
            "live/QA HTTP not healthy")

    version = docker(
        "exec", PATCHED_WEB, "bundle", "exec", "ruby", "-e",
        "require 'carrierwave'; print Gem.loaded_specs.fetch('carrierwave').version"
    ).stdout.decode().strip()
    require(version == "2.2.7", "patched QA runtime not CarrierWave 2.2.7")

    a = inventory(OLD_UPLOADS)
    b = inventory(PATCHED_UPLOADS)
    total = footprint(a) + footprint(b)
    free = shutil.disk_usage(str(BACKUP_BASE)).free
    require(free > total * 3 + 50 * 1024 * 1024,
            "not enough disk space for a verified private snapshot")

    print("QA PATCHED PROXY & DATABASE ISOLATION PASS", flush=True)
    print("QA PATCHED CARRIERWAVE 2.2.7 PASS", flush=True)
    print("QA PRODUCTS: 20; ID 21: ABSENT", flush=True)
    print("MEDIA FILES OLD:", sum(x[0] == "file" for x in a.values()), flush=True)
    print("MEDIA FILES PATCHED:", sum(x[0] == "file" for x in b.values()), flush=True)
    print("QA SNAPSHOT PREFLIGHT PASS", flush=True)
    return a, b


def tar_and_verify(path, prefix, target, expected):
    with tarfile.open(str(target), "w:gz") as archive:
        archive.add(str(path), arcname=prefix, recursive=False)
        for rel in sorted(expected):
            if rel:
                archive.add(str(path / rel),
                            arcname=prefix + "/" + rel, recursive=False)

    found = {}
    with tarfile.open(str(target), "r:gz") as archive:
        for member in archive:
            require(not member.issym() and not member.islnk(),
                    "archive unexpectedly contains link")
            rel = member.name[len(prefix):].lstrip("/")
            require(member.name == prefix or member.name.startswith(prefix + "/"),
                    "archive path outside expected prefix")
            require(rel not in found, "duplicate archive path")
            if member.isdir():
                found[rel] = ("dir",)
            elif member.isfile():
                src = archive.extractfile(member)
                require(src is not None, "archive file unreadable")
                with src:
                    found[rel] = ("file", member.size, sha256_stream(src))
            else:
                raise RuntimeError("unsupported archive entry type")
    require(found == expected, "archive content SHA256 differs from source")
    return sha256_file(target)


def snapshot():
    original_old, original_patched = preflight()
    os.umask(0o077)
    folder = Path(tempfile.mkdtemp(
        prefix="qa_security_snapshot_20261104_", dir=str(BACKUP_BASE)
    ))
    print("PRIVATE QA SNAPSHOT DIRECTORY:", folder, flush=True)

    dump = folder / "qa_cafe.dump"
    with dump.open("wb") as f:
        docker("exec", "--user", "postgres", QA_DB,
               "pg_dump", "-U", "postgres", "-d", "cafe",
               "--format=custom", "--compress=6",
               "--no-owner", "--no-acl", capture=False, stdout=f)
    require(dump.is_file() and dump.stat().st_size > 0,
            "PostgreSQL custom dump is empty")

    with dump.open("rb") as f:
        listing = docker("exec", "-i", "--user", "postgres", QA_DB,
                         "pg_restore", "--list", stdin=f).stdout.decode()
    require(" TABLE DATA " in listing and " TABLE " in listing,
            "pg_restore could not list schema and table data")
    print("QA POSTGRES CUSTOM DUMP VERIFIED", flush=True)

    old_tar = folder / "qa_uploads_previous.tar.gz"
    new_tar = folder / "qa_uploads_patched.tar.gz"
    old_sha = tar_and_verify(
        OLD_UPLOADS, "old_qa_uploads", old_tar, original_old
    )
    new_sha = tar_and_verify(
        PATCHED_UPLOADS, "patched_qa_uploads", new_tar, original_patched
    )
    print("BOTH QA MEDIA ARCHIVES SHA256 VERIFIED", flush=True)

    require(inventory(OLD_UPLOADS) == original_old,
            "old QA uploads changed during archive")
    require(inventory(PATCHED_UPLOADS) == original_patched,
            "patched QA uploads changed during archive")
    require(sql(QA_DB,
        "SELECT COUNT(*), COUNT(*) FILTER (WHERE id = 21) FROM products;") ==
            "20|0", "QA product counts changed during backup")

    meta = {
        "purpose": "private QA restore evidence (not an automatic rollback)",
        "database": {"archive": dump.name, "sha256": sha256_file(dump)},
        "old_uploads": {"archive": old_tar.name, "sha256": old_sha,
                        "files": sum(x[0] == "file" for x in original_old.values())},
        "patched_uploads": {"archive": new_tar.name, "sha256": new_sha,
                            "files": sum(x[0] == "file" for x in original_patched.values())},
        "qa_product_count": 20,
        "deleted_test_product_21": True,
        "verified": True,
    }
    metadata = folder / "manifest.json"
    metadata.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    metadata.chmod(0o600)
    for file in [dump, old_tar, new_tar]:
        file.chmod(0o600)

    require(http(3001, "/info") == 200 and http(3002, "/menu") == 200,
            "site HTTP changed during QA snapshot")
    print("PRODUCTION 3001 AND PATCHED QA 3002 HTTP 200", flush=True)
    print("QA DATABASE AND BOTH MEDIA SOURCES UNCHANGED", flush=True)
    print("QA SECURITY SNAPSHOT VERIFIED:", folder, flush=True)
    print("NO LIVE OR QA CONTAINERS RESTARTED", flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--snapshot", action="store_true")
    options = p.parse_args()
    try:
        if options.check:
            preflight()
            print("NO FILES OR CONTAINERS MODIFIED", flush=True)
        else:
            snapshot()
    except Exception as e:
        print("QA SNAPSHOT STOPPED:", type(e).__name__, str(e)[:350],
              file=sys.stderr)
        print("Do not overwrite or delete any partial snapshot; diagnose first.",
              file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
