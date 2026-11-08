#!/usr/bin/env python3
"""Owner-local guarded adoption of the mobile dock from Cafe Draft PR #69.

--check: metadata / Git SHA / layout anchor only; never writes.
--apply: separately requested owner action; private backup + two new files
         + one exact insertion into the owner's existing dirty layout.
--verify: independent read-only source / asset SHA and patch reversibility.

No checkout, reset, migration, seed, Docker, database, server or upload actions.
Never import the PR layout wholesale; the owner's local customized ERB is kept.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request

HOME = Path.home()
ROOT = HOME / "Рабочий стол/rails_projects/lite/cafe_app"
PRIVATE = HOME / ".local/share/cafe_app"
BRANCH = "feature/cafe-integration-local-20261101"
ASSET_COMMIT = "c415e32eb2ce8288087f5b1d652424fe1c6f51bf"
LAYOUT = Path("app/views/layouts/application.html.erb")
PARTIAL = Path("app/views/layouts/_mobile_dock.html.erb")
CSS = Path("app/assets/stylesheets/zzzzzzz_cafe_mobile_dock.scss")
LINKS = Path("app/views/layouts/_links.html.erb")
ACCOUNT_CSS = Path("app/assets/stylesheets/zzzzz_cafe_unified_shell.scss")
HEADER_CSS = Path("app/assets/stylesheets/zzzzzz_cafe_sticky_top_lock.scss")
OLD_LAYOUT_SHA = "85ab9031ec6fd13bdefb735588cf46f570daea11"
PARTIAL_SHA = "8f9d4ce95d96595bdc2c94877b72c69fbe371361"
CSS_SHA = "4d7465592951e87b99944e67b831705326eb4780"
LINKS_SHA = "1d1e0e96eef02161bffbcf634dac39e1764c9557"
ACCOUNT_CSS_SHA = "e3c73d446bfc0126a58a644e5afb96fe5a36c173"
HEADER_CSS_SHA = "64fcaa6462b3e60580f4548df9448d04ca9e493f"
INSERT = b"  <%= render 'layouts/mobile_dock' %>\n"
ANCHOR = b"  </body>"
BACKUP_PREFIX = "cafe_mobile_dock_layout_backup_20261107_"
MAX_SOURCE_BYTES = 60000


def require(ok, message):
    if not ok:
        raise RuntimeError("CAFE MOBILE DOCK STOP: " + message)


def git_blob(data):
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def command(*args):
    try:
        process = subprocess.run(
            ["git", "-C", str(ROOT), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("CAFE MOBILE DOCK STOP: Git inspection unavailable")
    require(process.returncode == 0, "Git inspection failed")
    return process.stdout.decode("utf-8", errors="replace").strip()


def source_file(relative, expected):
    file = ROOT / relative
    require(file.is_file() and not file.is_symlink(),
            "required reviewed source missing or symlinked: " + str(relative))
    data = file.read_bytes()
    require(0 < len(data) <= MAX_SOURCE_BYTES and git_blob(data) == expected,
            "reviewed local file SHA differs: " + str(relative))
    return data


def private_folder():
    require(PRIVATE.is_dir() and not PRIVATE.is_symlink(),
            "private backup folder is missing")
    metadata = PRIVATE.stat()
    require(metadata.st_uid == os.getuid() and metadata.st_mode & 0o077 == 0,
            "private backup folder must be owner-only")


def patched_layout(source):
    require(git_blob(source) == OLD_LAYOUT_SHA,
            "owner-local dirty layout changed; no automatic merge")
    require(source.count(ANCHOR) == 1, "layout </body> insertion anchor not unique")
    require(b"layouts/mobile_dock" not in source, "dock already inserted")
    for marker in (b"cafe-page", b"cafe-main-content", b"cafe-account-widget",
                   b"jquery@3.5.1", b"bootstrap@4.6.2",
                   b"avatar&.url(:thumb)", b"button_to 'Sign out'",
                   b"stylesheet_pack_tag", b"javascript_pack_tag",
                   b"render 'layouts/footer'"):
        require(marker in source, "owner layout anchor contract changed")
    return source.replace(ANCHOR, INSERT + ANCHOR, 1)


def check():
    require(os.getuid() == 1000, "local machine UID differs")
    require(ROOT.is_dir() and not ROOT.is_symlink() and (ROOT / ".git").exists(),
            "reviewed local cafe_app checkout missing")
    require(command("branch", "--show-current") == BRANCH,
            "owner-local dirty branch changed; no checkout/reset permitted")
    layout = source_file(LAYOUT, OLD_LAYOUT_SHA)
    source_file(LINKS, LINKS_SHA)
    source_file(ACCOUNT_CSS, ACCOUNT_CSS_SHA)
    source_file(HEADER_CSS, HEADER_CSS_SHA)
    manifest = ROOT / "app/assets/stylesheets/application.scss"
    require(manifest.is_file() and not manifest.is_symlink()
            and "require_tree ." in manifest.read_text(encoding="utf-8"),
            "expected Sprockets require_tree contract absent")
    for relative in (PARTIAL, CSS):
        file = ROOT / relative
        require(not file.exists() and not file.is_symlink(),
                "new mobile dock target already exists; refuse overwrite")
    private_folder()
    result = patched_layout(layout)
    print("CAFE MOBILE DOCK LOCAL BRANCH / FOUR SOURCE SHA PASS", flush=True)
    print("CAFE MOBILE DOCK TWO NEW FILE TARGETS ABSENT PASS", flush=True)
    print("CAFE MOBILE DOCK EXACT LAYOUT INSERTION SHA=" + git_blob(result),
          flush=True)
    print("CAFE MOBILE DOCK READ-ONLY CHECK PASS — NO FILES WRITTEN", flush=True)
    return layout, result


def pinned_asset(relative, expected):
    url = ("https://raw.githubusercontent.com/TheGor-365/cafe_app/" +
           ASSET_COMMIT + "/" + relative.as_posix())
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "cafe-owner-local-dock-gate/20261107"})
        with urllib.request.urlopen(req, timeout=30) as response:
            require(response.status == 200, "pinned asset HTTP status not 200")
            data = response.read(MAX_SOURCE_BYTES + 1)
    except RuntimeError:
        raise
    except Exception:
        raise RuntimeError("CAFE MOBILE DOCK STOP: pinned asset fetch unavailable")
    require(0 < len(data) <= MAX_SOURCE_BYTES and git_blob(data) == expected,
            "downloaded asset does not match reviewed Git blob")
    return data


def exclusive_save(path, data, mode):
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(path, mode)


def atomic_save(path, data, mode):
    fd, name = tempfile.mkstemp(prefix=".cafe-dock-", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def apply():
    before, after = check()
    partial = pinned_asset(PARTIAL, PARTIAL_SHA)
    css = pinned_asset(CSS, CSS_SHA)
    layout_path = ROOT / LAYOUT
    partial_path, css_path = ROOT / PARTIAL, ROOT / CSS
    # Re-check immediately before any writes.
    require(git_blob(layout_path.read_bytes()) == OLD_LAYOUT_SHA
            and not layout_path.is_symlink()
            and not partial_path.exists() and not partial_path.is_symlink()
            and not css_path.exists() and not css_path.is_symlink(),
            "local files changed during staging; refuse write")
    os.umask(0o077)
    backup = Path(tempfile.mkdtemp(prefix=BACKUP_PREFIX, dir=PRIVATE))
    os.chmod(backup, 0o700)
    exclusive_save(backup / "application.html.erb", before, 0o600)
    manifest = {
        "original_layout_sha": OLD_LAYOUT_SHA,
        "expected_layout_sha": git_blob(after),
        "new_partial_sha": PARTIAL_SHA,
        "new_css_sha": CSS_SHA,
        "pinned_asset_commit": ASSET_COMMIT,
        "created_unix": int(time.time()),
    }
    exclusive_save(backup / "manifest.json",
                   (json.dumps(manifest, sort_keys=True) + "\n").encode("utf-8"),
                   0o600)
    # Never overwrite existing user files; preserve backup on any failure.
    exclusive_save(partial_path, partial, 0o644)
    exclusive_save(css_path, css, 0o644)
    require(git_blob(layout_path.read_bytes()) == OLD_LAYOUT_SHA
            and not layout_path.is_symlink(),
            "owner layout changed concurrently; leave backup/new assets intact")
    atomic_save(layout_path, after, stat.S_IMODE(layout_path.stat().st_mode))
    require(git_blob(layout_path.read_bytes()) == git_blob(after)
            and git_blob(partial_path.read_bytes()) == PARTIAL_SHA
            and git_blob(css_path.read_bytes()) == CSS_SHA,
            "post-apply SHA failed, original preserved in private backup")
    print("CAFE MOBILE DOCK TWO PINNED ASSETS + ONE LAYOUT INSERTION APPLIED")
    print("CAFE MOBILE DOCK ORIGINAL PRIVATE BACKUP: " + str(backup))
    print("CAFE MOBILE DOCK POST-APPLY SHA PASS — NO CHECKOUT/DOCKER/DB ACTION")
    print("LOCAL CHROME MOBILE/DESKTOP VISUAL ACCEPTANCE NOT YET TESTED")


def verify():
    require(command("branch", "--show-current") == BRANCH,
            "local branch changed")
    source_file(LINKS, LINKS_SHA)
    source_file(ACCOUNT_CSS, ACCOUNT_CSS_SHA)
    source_file(HEADER_CSS, HEADER_CSS_SHA)
    source_file(PARTIAL, PARTIAL_SHA)
    source_file(CSS, CSS_SHA)
    path = ROOT / LAYOUT
    require(path.is_file() and not path.is_symlink(),
            "resulting layout missing or symlinked")
    after = path.read_bytes()
    require(after.count(INSERT) == 1,
            "dock insertion missing or duplicated")
    original = after.replace(INSERT, b"", 1)
    require(git_blob(original) == OLD_LAYOUT_SHA and
            patched_layout(original) == after,
            "existing owner layout was not preserved exactly")
    print("CAFE MOBILE DOCK LOCAL LAYOUT ONLY EXPECTED INSERTION PASS")
    print("CAFE MOBILE DOCK BOTH NEW ASSET GIT BLOBS PASS")
    print("CAFE MOBILE DOCK INDEPENDENT POSTFLIGHT PASS — NO WRITES")
    print("CHROME BROWSER VISUAL/INTERACTION ACCEPTANCE NOT TESTED")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        if args.check:
            check()
        elif args.apply:
            apply()
        else:
            verify()
    except Exception as error:
        message = str(error)
        if not message.startswith("CAFE MOBILE DOCK STOP:"):
            message = "CAFE MOBILE DOCK STOP: failed preflight/apply/verify; preserve state"
        print(message, file=sys.stderr, flush=True)
        print("Do not force checkout, remove data, replay schema/seeds, or restart Docker.",
              file=sys.stderr, flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
