#!/usr/bin/env python3
"""Import exact scoped Admin PR #27 files into an already-protected dirty local tree.

No checkout/rebase/merge, no database operation, no container restarts.
Use: python3 scripts/cafe_admin_local_import.py --check | --apply
"""
import argparse
import datetime
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

PROJECT = Path.home() / "Рабочий стол/rails_projects/lite/cafe_app"
REF = "origin/feature/cafe-admin-console-20261103"
EXPECTED_REF = "23ab6d53c0eb02232c5a35da7427e8b136429f1f"
LOCAL_BRANCH = "feature/cafe-integration-local-20261101"
BACKUP_BASE = Path.home() / "Backups/cafe_app/private_runtime"

# Verified through GitHub content SHAs from exact PR #26 base.
BEFORE = {
    "README.md": "8f29c92c8bb330d1d9cf8121f3220df8be882176",
    "app/controllers/categories_controller.rb": "6aeeed88fa2ea3f963fe2269641c39af499ecd6b",
    "app/controllers/products_controller.rb": "be5a75d3a9faac2168ecd3cddcf4468f38bce331",
    "app/views/categories/_form.html.erb": "32c65d0e83fe088c81e18aab21e959659194709c",
    "app/views/categories/edit.html.erb": "4654f9424227aec339fbf2cddd0abf14f88b81be",
    "app/views/categories/index.html.erb": "e27bd2122eb93be139526ca0e4f261b24059002b",
    "app/views/categories/new.html.erb": "7fb699f6b55b0fb726732db83da92027ef06f8c8",
    "app/views/products/_form.html.erb": "4e3a5bc9636826ff89a90913e5b66f10a4e55b2f",
    "app/views/products/edit.html.erb": "5676b8330f8b5373bc567518d3ce55f382e2a9c6",
    "app/views/products/index.html.erb": "a42d15077616147bf83fd6322949c224ac4214cb",
    "app/views/products/new.html.erb": "51c7073da38b77983e50b35349c1c0df95b8fff3",
    "test/integration/session_layout_isolation_test.rb": "c53c7d6555bdafe80e35a8c3a67c7279139bf294",
}
NEW = [
    ".github/workflows/coffee-admin-console.yml",
    "app/assets/stylesheets/zzz_cafe_admin.scss",
    "test/integration/coffee_admin_console_test.rb",
]
FILES = list(BEFORE) + NEW

# Owner's actual local tree (2026-11-04) lacks this historical integration
# test although it exists on the GitHub PR #26 base. Allow restoring ONLY
# this absent test from the reviewed PR #27; any symlink still aborts.
OPTIONAL_ABSENT_TEST = "test/integration/session_layout_isolation_test.rb"


def run(*args, capture=True):
    result = subprocess.run(args, cwd=str(PROJECT), check=True,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None)
    return result.stdout.decode("utf-8", errors="replace").strip() if capture else None


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def preflight():
    require(PROJECT.is_dir(), "Local project directory is missing")
    require(run("git", "branch", "--show-current") == LOCAL_BRANCH,
            "Unexpected local branch; no changes applied")
    require(run("git", "rev-parse", REF) == EXPECTED_REF,
            "PR #27 branch SHA differs. Fetch exact branch or re-review PR.")
    require(BACKUP_BASE.is_dir(), "Private backup base directory missing")

    mismatches = []
    restored_missing_test = False
    for rel, expected in BEFORE.items():
        path = PROJECT / rel
        if path.is_symlink():
            mismatches.append(rel + " (symlink: never overwrite)")
            continue
        if not path.exists():
            if rel == OPTIONAL_ABSENT_TEST:
                restored_missing_test = True
                continue
            mismatches.append(rel + " (missing)")
            continue
        if not path.is_file():
            mismatches.append(rel + " (not a regular file)")
            continue
        if run("git", "hash-object", "--", rel) != expected:
            mismatches.append(rel + " (local content differs)")

    for rel in NEW:
        path = PROJECT / rel
        if path.exists() or path.is_symlink():
            mismatches.append(rel + " (new file path already occupied)")

    if mismatches:
        raise RuntimeError(
            "PREFLIGHT BLOCKED: no files changed. Review these paths:\n  "
            + "\n  ".join(mismatches)
        )

    for rel in FILES:
        run("git", "cat-file", "-e", REF + ":" + rel)

    previous = 11 if restored_missing_test else 12
    added = 4 if restored_missing_test else 3
    print("ADMIN PREFLIGHT PASS: {} EXISTING + {} NEW FILES".format(previous, added), flush=True)
    if restored_missing_test:
        print("SAFE EXCEPTION: historical session test absent; will create it from PR #27", flush=True)
    print("PROTECTED: app/views/layouts/application.html.erb, user/uploader, DB, uploads", flush=True)


def save_backup():
    os.umask(0o077)
    directory = Path(tempfile.mkdtemp(
        prefix="pre_admin_pr27_", dir=str(BACKUP_BASE)
    ))
    (directory / "local_changes.patch").write_bytes(
        subprocess.check_output(["git", "diff", "--binary", "HEAD"],
                                cwd=str(PROJECT))
    )
    (directory / "file_status.txt").write_text(
        run("git", "status", "--porcelain=v1", "-uall") + "\n",
        encoding="utf-8"
    )
    absent = [rel for rel in BEFORE if not (PROJECT / rel).exists()]
    require(set(absent).issubset({OPTIONAL_ABSENT_TEST}),
            "Unexpected missing local files before backup")
    (directory / "absent_before_import.txt").write_text(
        "\n".join(absent) + ("\n" if absent else ""),
        encoding="utf-8"
    )
    with tarfile.open(directory / "affected_files.tar.gz", "w:gz") as tar:
        for rel in BEFORE:
            if rel not in absent:
                tar.add(PROJECT / rel, arcname=rel, recursive=False)
    with tarfile.open(directory / "affected_files.tar.gz", "r:gz") as tar:
        members = tar.getmembers()
        require(len(members) == len(BEFORE) - len(absent),
                "Backup archive is incomplete")
    print("ADMIN BACKUP VERIFIED:", directory, flush=True)
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    preflight()
    if args.check:
        print("ADMIN READY TO IMPORT — NO CHANGES MADE", flush=True)
        return

    backup = save_backup()
    try:
        subprocess.run(["git", "restore", "--source=" + REF,
                        "--worktree", "--", *FILES],
                       cwd=str(PROJECT), check=True)
        for rel in FILES:
            actual = run("git", "hash-object", "--", rel)
            expected = run("git", "rev-parse", REF + ":" + rel)
            require(actual == expected, "Import hash mismatch: " + rel)
    except Exception:
        print("IMPORT INTERRUPTED. Backup:", backup, file=sys.stderr)
        print("Do not retry or restore blindly; inspect tree first.", file=sys.stderr)
        raise

    print("ADMIN IMPORT VERIFIED: 15 FILES", flush=True)
    print("ORIGINAL APP LAYOUT/DB/USER/UPLOADS UNTOUCHED", flush=True)


if __name__ == "__main__":
    main()
