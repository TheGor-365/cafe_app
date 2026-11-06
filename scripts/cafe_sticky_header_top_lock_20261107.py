#!/usr/bin/env python3
"""Guarded local install for the 2026-11-07 sticky header top-only CSS correction.

--check: entirely read-only, checks known owner UI application state.
--apply: creates ONE new SCSS file exclusively after SHA verification.
--verify: independent read-only postflight. Never touches DB, Rails, Docker,
Git branch/history, existing source files, media, private markers or secrets.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path.home() / "Рабочий стол/rails_projects/lite/cafe_app"
BRANCH = "feature/cafe-integration-local-20261101"
LAYOUT = ROOT / "app/views/layouts/application.html.erb"
BASE_STYLE = ROOT / "app/assets/stylesheets/zzzzz_cafe_unified_shell.scss"
NEW_STYLE = ROOT / "app/assets/stylesheets/zzzzzz_cafe_sticky_top_lock.scss"
EXPECTED_LAYOUT = "85ab9031ec6fd13bdefb735588cf46f570daea11"
EXPECTED_BASE_CSS = "e3c73d446bfc0126a58a644e5afb96fe5a36c173"
EXPECTED_NEW_CSS = "64fcaa6462b3e60580f4548df9448d04ca9e493f"
SOURCE_COMMIT = "dd31cd7244fd786ba654bcf1e037454b81f37873"

def stop(condition, reason):
    if not condition:
        raise RuntimeError("CAFE HEADER LOCK STOP: " + reason)

def sha(data):
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()

def branch():
    try:
        p = subprocess.run(["git","-C",str(ROOT),"branch","--show-current"],
                           capture_output=True, timeout=15, check=False)
    except (OSError,subprocess.TimeoutExpired):
        raise RuntimeError("CAFE HEADER LOCK STOP: Git read-only inspection failed")
    stop(p.returncode == 0 and p.stdout.decode().strip() == BRANCH,
         "unexpected owner dirty branch; never checkout/reset")

def state_check():
    stop(os.getuid() == 1000, "expected owner UID differs")
    stop(ROOT.is_dir() and not ROOT.is_symlink() and (ROOT/".git").exists(),
         "owner cafe_app working tree missing")
    branch()
    for path,pin in ((LAYOUT,EXPECTED_LAYOUT),(BASE_STYLE,EXPECTED_BASE_CSS)):
        stop(path.is_file() and not path.is_symlink(),
             "reviewed owner UI file missing or symlink")
        stop(sha(path.read_bytes()) == pin,
             "existing patched UI source differs; refuse to modify")
    title = ROOT/"app/views/layouts/_title.html.erb"
    manifest = ROOT/"app/assets/stylesheets/application.scss"
    stop(title.is_file() and "cafe-brandbar" in title.read_text(),
         "brand header partial changed")
    stop(manifest.is_file() and "require_tree ." in manifest.read_text(),
         "Sprockets load order contract changed")

def check():
    state_check()
    stop(not NEW_STYLE.exists() and not NEW_STYLE.is_symlink(),
         "new top-lock stylesheet already exists; use --verify, not --apply")
    print("CAFE HEADER OLD UI ERB/CSS SHA AND BRANCH PASS")
    print("CAFE HEADER BRAND PARTIAL / SPROCKETS TREE PASS")
    print("CAFE HEADER TOP LOCK --check PASS — READ ONLY, NO FILES WRITTEN")

def fetch_css():
    url = ("https://raw.githubusercontent.com/TheGor-365/cafe_app/" +
           SOURCE_COMMIT + "/app/assets/stylesheets/" + NEW_STYLE.name)
    req = urllib.request.Request(url,headers={"User-Agent":"cafe-header-lock-sha-pin"})
    try:
        with urllib.request.urlopen(req,timeout=30) as response:
            stop(response.status == 200, "GitHub CSS HTTP response differs")
            data = response.read(16000)
    except Exception:
        raise RuntimeError("CAFE HEADER LOCK STOP: pinned stylesheet download failed")
    stop(len(data) < 16000 and sha(data) == EXPECTED_NEW_CSS,
         "pinned stylesheet Git blob mismatch")
    return data

def apply():
    check()
    data = fetch_css()
    state_check()
    stop(not NEW_STYLE.exists() and not NEW_STYLE.is_symlink(),
         "another stylesheet appeared during fetch; stop without overwrite")
    # The only write is an exclusive create; no existing source is replaced.
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os,"O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    old_umask = os.umask(0o022)
    try:
        fd=os.open(str(NEW_STYLE),flags,0o644)
        with os.fdopen(fd,"wb") as target:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
    finally:
        os.umask(old_umask)
    verify()
    print("CAFE HEADER TOP LOCK ONE NEW SCSS APPLIED; NO EXISTING FILES CHANGED")
    print("NO RAILS/DOCKER RESTART, DATABASE, MEDIA OR MARKER WRITES")

def verify():
    state_check()
    stop(NEW_STYLE.is_file() and not NEW_STYLE.is_symlink(),
         "new stylesheet absent or symlink")
    stop(sha(NEW_STYLE.read_bytes()) == EXPECTED_NEW_CSS,
         "installed CSS Git blob mismatch")
    print("CAFE HEADER TOP LOCK INDEPENDENT FILE HASH VERIFY PASS")
    print("BROWSER SCROLL/DEVICE RENDER STILL NEEDS OWNER CONFIRMATION")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check",action="store_true")
    mode.add_argument("--apply",action="store_true")
    mode.add_argument("--verify",action="store_true")
    a=p.parse_args()
    try:
        if a.check: check()
        elif a.apply: apply()
        else: verify()
    except Exception as e:
        msg=str(e)
        if not msg.startswith("CAFE HEADER LOCK STOP:"):
            msg="CAFE HEADER LOCK STOP: unexpected state; preserve files"
        print(msg,file=sys.stderr)
        print("Do not force, delete existing files or retry one-shot actions.",file=sys.stderr)
        raise SystemExit(1)
if __name__ == "__main__":
    main()
