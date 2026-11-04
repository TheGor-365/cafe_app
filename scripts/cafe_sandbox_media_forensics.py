#!/usr/bin/env python3
"""Read-only forensic comparison after sandbox-only multipart test cleanup failure.

Compares verified PRIVATE QA snapshot media archive with current SANDBOX media.
Outputs only aggregate counts, categories, sizes and opaque hashed path IDs
(no personal filenames, emails, uploaded image content or secrets).
Queries aggregate counts on the sandbox PostgreSQL ONLY.

Does not create, alter or remove any file, container, volume or database row.
Do not upload private media archives or DB dumps to GitHub/Drive/chat.
"""
import hashlib
import json
from collections import Counter
from http.client import HTTPConnection
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile

HOME = Path.home()
SNAPSHOT = HOME / "Backups/cafe_app/private_runtime/qa_security_snapshot_20261104_sqwulocr"
MEDIA = HOME / ".local/share/cafe_app/uploads_security_sandbox_20261104"
PROJECT = HOME / "Рабочий стол/rails_projects/lite/cafe_app"
SANDBOX_WEB = "cafe-upload-security-sandbox-rails-20261104"
SANDBOX_DB = "cafe-upload-security-sandbox-pg-20261104"
SANDBOX_NET = "cafe-upload-security-sandbox-20261104"
QA_DB = "cafe-upload-qa-pg-20261103"
LIVE_DB = "cafe-app-db"
PREFIX = "patched_qa_uploads"


def verify(condition, message):
    if not condition:
        raise RuntimeError("READ-ONLY FORENSICS BLOCKED: " + message)


def shasum_stream(reader):
    digest = hashlib.sha256()
    size = 0
    for chunk in iter(lambda: reader.read(128 * 1024), b""):
        digest.update(chunk)
        size += len(chunk)
    return size, digest.hexdigest()


def shasum(path):
    with path.open("rb") as reader:
        return shasum_stream(reader)


def docker(*args):
    return subprocess.check_output(
        ("docker",) + args,
        stderr=subprocess.DEVNULL
    ).decode().strip()


def inspect(name):
    return json.loads(docker("inspect", name))[0]


def sql(container, statement):
    return docker(
        "exec", "--user", "postgres", container,
        "psql", "-X", "-At", "-U", "postgres", "-d", "cafe", "-c", statement
    )


def http_status(port, route):
    connection = HTTPConnection("127.0.0.1", port, timeout=8)
    try:
        connection.request("GET", route)
        response = connection.getresponse()
        response.read()
        return response.status
    finally:
        connection.close()


def verify_environment():
    verify(PROJECT.is_dir(), "project directory not found")
    verify(SNAPSHOT.is_dir() and not SNAPSHOT.is_symlink(),
           "private snapshot directory missing or symbolic link")
    verify(MEDIA.is_dir() and not MEDIA.is_symlink(),
           "sandbox media directory missing or symbolic link")

    web = inspect(SANDBOX_WEB)
    db = inspect(SANDBOX_DB)
    verify(web["State"]["Status"] == "running", "sandbox Rails not running")
    verify(db["State"]["Status"] == "running", "sandbox PostgreSQL not running")
    verify(set(web["NetworkSettings"]["Networks"]) == {SANDBOX_NET},
           "sandbox Rails network differs")
    verify(set(db["NetworkSettings"]["Networks"]) == {SANDBOX_NET},
           "sandbox PostgreSQL network differs")
    network = json.loads(docker("network", "inspect", SANDBOX_NET))[0]
    verify(network["Internal"] is True,
           "sandbox network is not internal")
    verify(not web["HostConfig"]["PortBindings"] and
           not db["HostConfig"]["PortBindings"],
           "sandbox Docker container publishes host ports")
    verify(web["HostConfig"]["ReadonlyRootfs"],
           "sandbox Rails root unexpectedly writable")
    mounts = {mount["Destination"]: mount for mount in web["Mounts"]}
    sandbox_mount = mounts.get("/app/public/uploads", {})
    verify(sandbox_mount.get("Source") == str(MEDIA) and
           sandbox_mount.get("RW") is True,
           "sandbox web uploads directory no longer private")
    verify(mounts["/app"]["RW"] is False,
           "sandbox Rails project source writable")
    verify("/run/secrets/cafe_pg_password" not in mounts,
           "sandbox web unexpectedly has secret bind")
    env = dict(item.split("=", 1) for item in web["Config"]["Env"])
    verify(env.get("DATABASE_URL") ==
           "postgresql://postgres@cafe-app-db:5432/cafe",
           "sandbox database URL unexpected")
    ids = [
        sql(dbname, "SELECT system_identifier::text FROM pg_control_system();")
        for dbname in (SANDBOX_DB, QA_DB, LIVE_DB)
    ]
    verify(all(value.isdigit() for value in ids) and len(set(ids)) == 3,
           "sandbox, QA and live PostgreSQL identities not distinct")
    verify(http_status(3001, "/info") == 200 and
           http_status(3002, "/menu") == 200,
           "existing production or QA HTTP check failed")
    print("SANDBOX/LIVE ISOLATION STILL VERIFIED")
    print("HOST 3001/3002 HTTP 200")


def verified_archive():
    manifest_path = SNAPSHOT / "manifest.json"
    verify(manifest_path.is_file() and not manifest_path.is_symlink(),
           "snapshot checksum manifest missing")
    metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
    verify(metadata.get("verified") is True,
           "snapshot manifest did not verify itself")
    record = metadata["patched_uploads"]
    verify(record["archive"] == "qa_uploads_patched.tar.gz" and
           record["files"] == 10, "snapshot media archive metadata changed")
    archive = SNAPSHOT / record["archive"]
    verify(archive.is_file() and not archive.is_symlink(),
           "snapshot private media archive missing")
    size, sha = shasum(archive)
    verify(size > 0 and sha == record["sha256"],
           "snapshot media archive SHA-256 does not match manifest")
    expected = {}
    with tarfile.open(archive, "r:gz") as handle:
        for member in handle:
            verify(member.name == PREFIX or
                   member.name.startswith(PREFIX + "/"),
                   "snapshot archive member outside root")
            relative = member.name[len(PREFIX):].lstrip("/")
            path = PurePosixPath(relative)
            verify(not path.is_absolute() and
                   all(piece not in ("..",) for piece in path.parts),
                   "unsafe archive pathname")
            if member.isdir():
                continue
            verify(member.isfile(), "snapshot archive has non-regular file")
            verify(relative not in expected, "duplicate archived file")
            reader = handle.extractfile(member)
            verify(reader is not None, "archive content missing")
            with reader:
                file_size, file_sha = shasum_stream(reader)
            verify(file_size == member.size, "archived file truncated")
            expected[relative] = (file_size, file_sha)
    verify(len(expected) == 10, "snapshot does not contain ten files")
    print("PRIVATE SNAPSHOT MEDIA SHA256 VERIFIED; 10 ORIGINAL FILES")
    return expected


def current_files():
    found = {}
    for path in MEDIA.rglob("*"):
        verify(not path.is_symlink(), "sandbox media contains symlink")
        if path.is_dir():
            continue
        verify(path.is_file(), "sandbox media has special file")
        name = path.relative_to(MEDIA).as_posix()
        found[name] = shasum(path)
    return found


def category(name):
    parts = PurePosixPath(name).parts
    if any(p.lower() in ("tmp", "cache", "cached", "temp") for p in parts):
        return "temporary/cache"
    if "avatar" in (p.lower() for p in parts):
        return "avatar/or-thumbnail"
    return "other"


def render_delta(label, records):
    if not records:
        print(label + ": 0")
        return
    counts = Counter(category(name) for name in records)
    print(label + ": " + str(len(records)))
    for kind, count in sorted(counts.items()):
        print("  " + kind + ": " + str(count))
    for name, stats in list(sorted(records.items()))[:12]:
        opaque = hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
        print("  opaque_path_id=" + opaque + " category=" + category(name) +
              " size_bytes=" + str(stats[0]))
    if len(records) > 12:
        print("  plus " + str(len(records) - 12) + " additional entries")


def main():
    verify_environment()
    baseline = verified_archive()
    actual = current_files()
    added_names = set(actual) - set(baseline)
    missing_names = set(baseline) - set(actual)
    modified_names = {
        name for name in (set(baseline) & set(actual))
        if baseline[name] != actual[name]
    }
    print("SANDBOX CURRENT FILE COUNT:", len(actual))
    render_delta("ADDED FILES", {name: actual[name] for name in added_names})
    render_delta("MISSING BASELINE FILES",
                 {name: baseline[name] for name in missing_names})
    render_delta("CHANGED BASELINE FILES",
                 {name: actual[name] for name in modified_names})

    counts = sql(SANDBOX_DB, """
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE email LIKE 'accept-%@example.test'),
               COUNT(*) FILTER (WHERE email LIKE 'reject-%@example.test')
        FROM users;
    """)
    fields = counts.split("|")
    verify(len(fields) == 3 and all(value.isdigit() for value in fields),
           "unexpected aggregate sandbox user count")
    print("SANDBOX USERS TOTAL:", fields[0])
    print("RESIDUAL GENERATED ACCEPT-USERS:", fields[1])
    print("RESIDUAL GENERATED REJECT-USERS:", fields[2])
    print("FORENSICS READ-ONLY COMPLETE; NO MEDIA OR DATABASE MUTATIONS")
    if added_names or missing_names or modified_names:
        print("SANDBOX MEDIA BASELINE MISMATCH CONFIRMED")
    else:
        print("SANDBOX MEDIA NOW MATCHES PRIVATE BASELINE")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FORENSICS STOPPED:", type(exc).__name__, str(exc)[:350],
              file=sys.stderr)
        raise SystemExit(1)
