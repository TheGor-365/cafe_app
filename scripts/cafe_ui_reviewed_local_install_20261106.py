#!/usr/bin/env python3
"""Guarded local Cafe UI handoff. --check is read-only; --apply changes ONLY two UI files.

Never checks out, rebases, resets, cleans or restarts Docker. No database,
upload, one-shot marker or old CSS modification. Refuses unfamiliar dirty
layout rather than overwriting the owner's work.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request

ROOT = Path.home() / "Рабочий стол/rails_projects/lite/cafe_app"
PRIVATE = Path.home() / ".local/share/cafe_app"
BRANCH = "feature/cafe-integration-local-20261101"
PINNED_UI_COMMIT = "10cf64a63c51c146a0389ebc99376e20f659d10c"
LAYOUT = Path("app/views/layouts/application.html.erb")
STYLE = Path("app/assets/stylesheets/zzzzz_cafe_unified_shell.scss")
EXPECTED_LOCAL_LAYOUT = "c8921be1b02d06b3f30f7ab4b0166e13d20b3be8"
EXPECTED_REMOTE_LAYOUT = "cfab73051bd1ddd5f8f6824ea69ece3be7fccc52"
EXPECTED_REMOTE_STYLE = "ffe52c0f1cba6a1dd19bd20f91bd7a7435322fba"

def require(ok, message):
    if not ok:
        raise RuntimeError("CAFE UI LOCAL STOP: " + message)

def blob_bytes(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def git(*args):
    p = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,
                       timeout=18, check=False)
    require(p.returncode == 0, "Git read-only inspection failed")
    return p.stdout.decode("utf-8", errors="replace").strip()

def preflight():
    require(os.getuid() == 1000, "unexpected local user")
    require(ROOT.is_dir() and not ROOT.is_symlink() and (ROOT / ".git").exists(),
            "expected cafe_app repository not found")
    require(git("branch", "--show-current") == BRANCH,
            "active dirty branch changed; no checkout allowed")
    original = ROOT / LAYOUT
    candidate = ROOT / STYLE
    require(original.is_file() and not original.is_symlink(),
            "original application layout missing or symlink")
    require(not candidate.exists() and not candidate.is_symlink(),
            "new stylesheet already exists; do not overwrite or apply twice")
    actual = blob_bytes(original.read_bytes())
    require(actual == EXPECTED_LOCAL_LAYOUT,
            "layout differs from reviewed GitHub version (found " + actual +
            "); no overwrite, compare owner edits first")
    styles = ROOT / "app/assets/stylesheets/application.scss"
    links = ROOT / "app/views/layouts/_links.html.erb"
    title = ROOT / "app/views/layouts/_title.html.erb"
    require(styles.is_file() and "require_tree ." in styles.read_text(),
            "legacy Sprockets manifest changed")
    require(links.is_file() and 'cafe-sidebar' in links.read_text(),
            "left navigation markup changed")
    require(title.is_file() and 'cafe-brandbar' in title.read_text(),
            "header markup changed")
    require(PRIVATE.is_dir() and not PRIVATE.is_symlink() and
            PRIVATE.stat().st_uid == os.getuid() and
            PRIVATE.stat().st_mode & 0o077 == 0,
            "private backup parent not owner-only 0700")
    print("CAFE UI ORIGINAL DIRTY BRANCH PRESERVED")
    print("CAFE UI LOCAL LAYOUT MATCHES REVIEWED SOURCE " + actual)
    print("CAFE UI NEW STYLE ABSENT / NAV + HEADER / SPROCKETS PASS")
    print("CAFE UI --check PASS — READ ONLY, NO FILES WRITTEN")
    return original, candidate

def fetch(relative_path, expected_blob):
    url = ("https://raw.githubusercontent.com/TheGor-365/cafe_app/" +
           PINNED_UI_COMMIT + "/" + relative_path.as_posix())
    request = urllib.request.Request(url, headers={"User-Agent": "cafe-ui-pinned-review/1"})
    with urllib.request.urlopen(request, timeout=25) as res:
        require(res.status == 200, "GitHub pinned source fetch failed")
        data = res.read(80_000)
    require(len(data) < 80_000 and blob_bytes(data) == expected_blob,
            "fetched UI source does not match pinned Git blob")
    return data

def install():
    original, candidate = preflight()
    new_layout = fetch(LAYOUT, EXPECTED_REMOTE_LAYOUT)
    new_style = fetch(STYLE, EXPECTED_REMOTE_STYLE)
    require(blob_bytes(original.read_bytes()) == EXPECTED_LOCAL_LAYOUT and
            not candidate.exists(), "local UI files changed during download")
    backup_dir = Path(tempfile.mkdtemp(prefix="cafe_ui_before_20261106_", dir=PRIVATE))
    os.chmod(backup_dir, 0o700)
    backup = backup_dir / "application.html.erb"
    with backup.open("xb") as out:
        out.write(original.read_bytes())
    os.chmod(backup, 0o600)

    # Write the new cascade layer first; replace layout only after CSS is ready.
    tmp_layout = None
    try:
        with candidate.open("xb") as out:
            out.write(new_style)
        os.chmod(candidate, 0o644)
        fd, tmp_name = tempfile.mkstemp(prefix=".cafe_layout_", dir=original.parent)
        tmp_layout = Path(tmp_name)
        with os.fdopen(fd, "wb") as out:
            out.write(new_layout)
        os.chmod(tmp_layout, stat.S_IMODE(original.stat().st_mode))
        require(blob_bytes(original.read_bytes()) == EXPECTED_LOCAL_LAYOUT,
                "layout changed concurrently; stop before replacement")
        os.replace(tmp_layout, original)
        tmp_layout = None
        require(blob_bytes(original.read_bytes()) == EXPECTED_REMOTE_LAYOUT and
                blob_bytes(candidate.read_bytes()) == EXPECTED_REMOTE_STYLE,
                "post-write hash mismatch")
    except Exception:
        if tmp_layout is not None:
            tmp_layout.unlink(missing_ok=True)
        # Preserve backup and new style for diagnosis; no silent destructive cleanup.
        raise
    print("CAFE UI APPLIED TWO PINNED FILES; ORIGINAL BACKUP SECURED")
    print("CAFE UI BACKUP DIRECTORY: " + str(backup_dir))
    print("CAFE UI NO GIT CHECKOUT / DOCKER RESTART / DB / UPLOAD / MARKER WRITES")
    print("Open localhost:3001/info with a hard refresh and verify actual rendering.")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--apply", action="store_true")
    opts = parser.parse_args()
    try:
        if opts.check:
            preflight()
        else:
            install()
    except Exception as exc:
        msg = str(exc)
        if not msg.startswith("CAFE UI LOCAL STOP: "):
            msg = "CAFE UI LOCAL STOP: inspected source/application unavailable; preserve all files"
        print(msg, file=sys.stderr)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
