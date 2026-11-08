#!/usr/bin/env python3
"""Owner-local guarded Cafe UI adapter for actual 06.11 dirty ERB source.

Modes: --check read-only; --apply separately staged 2-file UI patch;
--verify read-only after applying. No checkout, database, Docker or upload changes.
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
LAYOUT = Path("app/views/layouts/application.html.erb")
STYLE = Path("app/assets/stylesheets/zzzzz_cafe_unified_shell.scss")

# SHA is the actual modified owner ERB, checked against owner terminal output.
EXPECTED_LOCAL_LAYOUT = "1c5550e55e653cf204f0f6910b1251b2dc0e4320"
EXPECTED_PATCHED_LAYOUT = "85ab9031ec6fd13bdefb735588cf46f570daea11"
STYLE_COMMIT = "28e4c145d09e44cb34377fae0c36b60f9d563bcf"
EXPECTED_STYLE_BLOB = "e3c73d446bfc0126a58a644e5afb96fe5a36c173"

OLD_ACCOUNT = """          <div class="col-1">
            <% avatar_url = current_user&.avatar&.url(:thumb) %>
            <%= image_tag avatar_url, class: "rounded mt-2" if avatar_url.present? %>
          </div>
          <div class="col-1 p-2">
            <% if user_signed_in? %>
              <h6><%= button_to 'Sign out', destroy_user_session_path, method: :delete %></h6>
              <%= link_to edit_user_registration_path do %>
                <h6 class="text-white text-decoration-none">
                  <%= current_user.username %>
                </h6>
              <% end %>
            <% else %>
              <h6><%= link_to 'Sign in', new_user_session_path %></h6>
              <h6><%= link_to 'Sign up', new_user_registration_path %></h6>
            <% end %>
          </div>"""

NEW_ACCOUNT = """          <%# Shared account panel, with no empty guest avatar column. %>
          <nav class="cafe-account-widget" aria-label="Account">
            <% if user_signed_in? %>
              <% avatar_url = current_user&.avatar&.url(:thumb) if current_user.respond_to?(:avatar) %>
              <%= link_to edit_user_registration_path, class: 'cafe-account-widget__identity' do %>
                <% if avatar_url.present? %>
                  <%= image_tag avatar_url, alt: '', class: 'cafe-account-widget__avatar', width: 44, height: 44 %>
                <% end %>
                <span class="cafe-account-widget__username"><%= current_user.username.presence || 'My account' %></span>
              <% end %>
              <%= button_to 'Sign out', destroy_user_session_path, method: :delete, class: 'cafe-account-widget__signout' %>
            <% else %>
              <%= link_to 'Sign in', new_user_session_path, class: 'cafe-account-widget__link' %>
              <%= link_to 'Sign up', new_user_registration_path, class: 'cafe-account-widget__link cafe-account-widget__link--primary' %>
            <% end %>
          </nav>"""

REPLACEMENTS = (
    ('<div class="<%= @page %>-page">',
     '<div class="cafe-page <%= @page %>-page">'),
    ('          <div class="col-8">',
     '          <div class="col-8" role="main" id="cafe-main-content">'),
    (OLD_ACCOUNT, NEW_ACCOUNT),
)

def require(ok, message):
    if not ok:
        raise RuntimeError("CAFE UI ADAPTER STOP: " + message)

def blob(data):
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()

def git(*args):
    try:
        p = subprocess.run(["git", "-C", str(ROOT), *args],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("CAFE UI ADAPTER STOP: read-only Git inspection unavailable")
    require(p.returncode == 0, "read-only Git inspection failed")
    return p.stdout.decode("utf-8", errors="replace").strip()

def adapt(original):
    require(blob(original) == EXPECTED_LOCAL_LAYOUT,
            "owner ERB hash changed; preserve the original")
    value = original.decode("utf-8")
    for old, new in REPLACEMENTS:
        require(value.count(old) == 1, "targeted ERB source anchor not unique")
        value = value.replace(old, new, 1)
    final = value.encode("utf-8")
    require(blob(final) == EXPECTED_PATCHED_LAYOUT,
            "patch output differs from reviewed source")
    # Original integration assets, CDN, footer, avatar thumbnail, and DELETE
    # button are kept; unrelated dirty files are not touched.
    for token in ("jquery@3.5.1", "bootstrap@4.6.2",
                  "avatar&.url(:thumb)", "button_to 'Sign out'",
                  "stylesheet_pack_tag", "javascript_pack_tag",
                  "render 'layouts/footer'"):
        require(token in value, "expected owner dependency lost")
    return final

def private_check():
    require(PRIVATE.is_dir() and not PRIVATE.is_symlink(),
            "owner-private backing folder missing")
    p = PRIVATE.stat()
    require(p.st_uid == os.getuid() and (p.st_mode & 0o077) == 0,
            "backup folder must be owner-only 0700")

def check():
    require(os.getuid() == 1000, "owner UID differs from known machine")
    require(ROOT.is_dir() and not ROOT.is_symlink() and
            (ROOT / ".git").exists(), "reviewed cafe_app checkout missing")
    require(git("branch", "--show-current") == BRANCH,
            "current dirty branch changed; do not checkout or reset")
    path = ROOT / LAYOUT
    target = ROOT / STYLE
    require(path.is_file() and not path.is_symlink(),
            "source ERB missing or is a symlink")
    require(not target.exists() and not target.is_symlink(),
            "candidate stylesheet already exists; refuse overwrite/repeat")
    original = path.read_bytes()
    result = adapt(original)
    manifest = ROOT / "app/assets/stylesheets/application.scss"
    title = ROOT / "app/views/layouts/_title.html.erb"
    nav = ROOT / "app/views/layouts/_links.html.erb"
    require(manifest.is_file() and "require_tree ." in manifest.read_text(),
            "Sprockets stylesheet loading contract changed")
    require(nav.is_file() and "cafe-sidebar" in nav.read_text(),
            "side navigation source changed")
    require(title.is_file() and "cafe-brandbar" in title.read_text(),
            "header source changed")
    private_check()
    print("CAFE UI ACTUAL LOCAL ERB SHA / CDN / AVATAR THUMB / DELETE FORM PASS")
    print("CAFE UI TARGETED PATCH SHA PASS " + blob(result))
    print("CAFE UI NAV / TITLE / SPROCKETS / PRIVATE BACKUP PATH PASS")
    print("CAFE UI READ-ONLY --check PASS — NO FILES WRITTEN")
    return path, target, original, result

def remote_css():
    url = (
        "https://raw.githubusercontent.com/TheGor-365/cafe_app/" +
        STYLE_COMMIT + "/" + STYLE.as_posix()
    )
    req = urllib.request.Request(url, headers={
        "User-Agent": "cafe-ui-private-pinned-adapter/20261107"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            require(r.status == 200, "reviewed GitHub CSS fetch not HTTP 200")
            data = r.read(40000)
    except Exception:
        raise RuntimeError("CAFE UI ADAPTER STOP: pinned GitHub stylesheet unavailable")
    require(len(data) < 40000 and blob(data) == EXPECTED_STYLE_BLOB,
            "downloaded stylesheet SHA not reviewed Git blob")
    return data

def atomic_save(path, data, mode):
    fd, tempname = tempfile.mkstemp(prefix=".cafe-ui-", dir=path.parent)
    temp = Path(tempname)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()

def apply():
    path, target, original, output = check()
    css = remote_css()
    require(blob(path.read_bytes()) == EXPECTED_LOCAL_LAYOUT and
            not target.exists(), "source changed while preparing adapter")
    os.umask(0o077)
    backup = Path(tempfile.mkdtemp(prefix="cafe_ui_layout_backup_20261107_",
                                   dir=PRIVATE))
    os.chmod(backup, 0o700)
    original_backup = backup / "application.html.erb"
    with original_backup.open("xb") as f:
        f.write(original)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(original_backup, 0o600)
    evidence = backup / "manifest.json"
    with evidence.open("x", encoding="utf-8") as f:
        json.dump({"original_git_blob": EXPECTED_LOCAL_LAYOUT,
                   "expected_new_git_blob": EXPECTED_PATCHED_LAYOUT,
                   "css_git_blob": EXPECTED_STYLE_BLOB,
                   "reviewed_css_commit": STYLE_COMMIT,
                   "created_unix": int(time.time())}, f, sort_keys=True)
        f.write("\n")
    os.chmod(evidence, 0o600)

    # Add the new stylesheet via exclusive create; overwrite no existing file.
    # Do not remove it silently in a partial failure: preserve evidence.
    with target.open("xb") as f:
        f.write(css)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(target, 0o644)
    require(blob(path.read_bytes()) == EXPECTED_LOCAL_LAYOUT,
            "layout changed concurrently; backup and CSS preserved, no ERB replacement")
    atomic_save(path, output, stat.S_IMODE(path.stat().st_mode))
    require(blob(path.read_bytes()) == EXPECTED_PATCHED_LAYOUT and
            blob(target.read_bytes()) == EXPECTED_STYLE_BLOB,
            "post-apply file hash mismatch; preserve private backup")
    print("CAFE UI EXACT OWNER ERB PATCH + ONE SCSS APPLIED")
    print("CAFE UI ORIGINAL PRIVATE BACKUP: " + str(backup))
    print("CAFE UI TWO FILE HASH POSTFLIGHT PASS; NO CONTAINER RESTART")
    print("Validate asset serving/Chrome separately; protected DB/media untouched.")

def verify():
    require(git("branch", "--show-current") == BRANCH,
            "dirty branch changed during postflight")
    path, target = ROOT / LAYOUT, ROOT / STYLE
    require(path.is_file() and target.is_file() and
            not path.is_symlink() and not target.is_symlink(),
            "expected UI files missing")
    require(blob(path.read_bytes()) == EXPECTED_PATCHED_LAYOUT and
            blob(target.read_bytes()) == EXPECTED_STYLE_BLOB,
            "postflight source file SHA mismatch")
    print("CAFE UI INDEPENDENT LOCAL FILE HASH VERIFY PASS")
    print("CAFE UI BROWSER/DOCKER RENDER UNVERIFIED; NO WRITES")

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    modes = ap.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    try:
        if a.check:
            check()
        elif a.apply:
            apply()
        else:
            verify()
    except Exception as exc:
        msg = str(exc)
        if not msg.startswith("CAFE UI ADAPTER STOP:"):
            msg = "CAFE UI ADAPTER STOP: unexpected preflight/write failure; preserve state"
        print(msg, file=sys.stderr, flush=True)
        print("No checkout, reset, blind retry, Docker or database changes.", file=sys.stderr)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
