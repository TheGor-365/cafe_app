#!/usr/bin/env python3
"""Remove exactly ONE confirmed 3-byte rejected-JPEG cache object in SANDBOX.

--check: read-only verify exact private snapshot, original file identities,
         sandbox Docker/PG isolation, single extra expected 3-byte file,
         SHA of opaque file path, and zero residual generated users.
--clean: repeat the exact same checks then unlink ONLY that sandbox cache file.
         No container restart, SQL write, production/QA media edit or rmtree.

If any fact differs, stop with no mutation. The private backup is preserved.
"""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

HOME = Path.home()
SCRIPT = HOME / ".local/share/cafe_app/cafe_sandbox_media_forensics_20261104.py"
EXPECTED_SCRIPT_BLOB = "250587d9fd767131b0afdaf2e9c2e14df0a6fcb8"
EXPECTED_OPAQUE_PATH_ID = "c7f26d5886cc"
JPEG_TRUNCATED_BYTES = b"\xff\xd8\xff"


def gate(state, message):
    if not state:
        raise RuntimeError("SCOPED CLEANUP BLOCKED: " + message)


def forensics():
    gate(SCRIPT.is_file() and not SCRIPT.is_symlink(),
         "read-only forensic script missing")
    p = subprocess.run(["git", "hash-object", str(SCRIPT)],
                       capture_output=True, text=True, check=True)
    gate(p.stdout.strip() == EXPECTED_SCRIPT_BLOB,
         "unexpected forensic script Git blob")
    spec = importlib.util.spec_from_file_location("cafe_readonly_forensics", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    gate(m.SANDBOX_WEB == "cafe-upload-security-sandbox-rails-20261104" and
         m.SANDBOX_DB == "cafe-upload-security-sandbox-pg-20261104" and
         m.SANDBOX_NET == "cafe-upload-security-sandbox-20261104",
         "forensic module sandbox target changed")
    return m


def verify():
    m = forensics()
    m.verify_environment()
    expected = m.verified_archive()
    actual = m.current_files()
    gate(len(expected) == 10 and len(actual) == 11,
         "expected restored ten files and precisely one extra")
    gate(not (set(expected) - set(actual)),
         "private baseline files went missing")
    gate(not any(actual[name] != expected[name] for name in expected),
         "protected baseline content was modified")

    added = set(actual) - set(expected)
    gate(len(added) == 1, "not exactly one extra sandbox object")
    name = next(iter(added))
    opaque = hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
    gate(opaque == EXPECTED_OPAQUE_PATH_ID,
         "unexpected extra file path; no deletion permitted")
    gate(m.category(name) == "temporary/cache",
         "extra file is not temporary/cache")
    gate("tmp" in (part.lower() for part in Path(name).parts),
         "expected temporary cache directory not present")

    path = m.MEDIA / name
    gate(path.is_file() and not path.is_symlink(),
         "cache residue must be a regular file")
    gate(path.resolve(strict=True).is_relative_to(m.MEDIA.resolve(strict=True)),
         "cache file path escapes sandbox")
    st = path.stat()
    gate(st.st_nlink == 1 and st.st_size == 3,
         "unexpected file link count or size")
    gate(path.read_bytes() == JPEG_TRUNCATED_BYTES,
         "3-byte cache does not match truncated JPEG fixture; do not remove")
    counts = m.sql(m.SANDBOX_DB, """
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE email LIKE 'accept-%@example.test'),
               COUNT(*) FILTER (WHERE email LIKE 'reject-%@example.test')
        FROM users;
    """).split("|")
    gate(counts == ["2", "0", "0"],
         "sandbox user counts no longer match confirmed forensic result")

    print("SINGLE TRUNCATED JPEG CACHE RESIDUE CONFIRMED", flush=True)
    print("ORIGINAL 10 MEDIA FILE SHA256 MATCH", flush=True)
    print("ZERO GENERATED USERS; SANDBOX/LIVE ISOLATION PASS", flush=True)
    return m, path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--clean", action="store_true")
    a = p.parse_args()

    m, target = verify()
    if a.check:
        print("SCOPED CACHE CHECK PASS — NO FILES CHANGED", flush=True)
        return

    # Refuse races: repeat exact bytes and inode link count directly
    # before unlinking ONLY the independently verified sandbox file.
    before = target.stat()
    gate(before.st_nlink == 1 and before.st_size == 3 and
         target.read_bytes() == JPEG_TRUNCATED_BYTES,
         "cache file altered before requested cleanup")
    target.unlink()
    gate(m.current_files() == m.verified_archive(),
         "sandbox media unexpectedly differs from original 10 after cleanup")
    gate(m.sql(m.SANDBOX_DB, "SELECT COUNT(*) FROM users;") == "2",
         "sandbox user records changed unexpectedly")
    gate(m.http_status(3001, "/info") == 200 and
         m.http_status(3002, "/menu") == 200,
         "active loopback site HTTP changed")
    print("EXACTLY ONE 3-BYTE SANDBOX TMP FILE REMOVED", flush=True)
    print("SANDBOX MEDIA BASELINE SHA256 RESTORED — 10 FILES", flush=True)
    print("NO USER, QA, LIVE OR DOCKER RESOURCE MODIFIED", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("SCOPED CLEANUP STOPPED:", type(e).__name__,
              str(e)[:350], file=sys.stderr, flush=True)
        print("Never retry blindly; original private snapshot is preserved.",
              file=sys.stderr, flush=True)
        raise SystemExit(1)
