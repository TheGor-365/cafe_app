#!/usr/bin/env python3
"""Build a separate CarrierWave 2.2.7 bundle for legacy Gor's Coffee.

--check is read-only and checks the exact owner-confirmed local Gemfile/lock,
the isolated QA container and the existing immutable /bundle mount.
--build first runs the same preflight, then creates ONLY two NEW private host
directories outside the Git working tree and runs a disposable network-bridge
Docker builder with no database mounts, private app networks or secrets.

No live/QA Rails container is stopped, edited, recreated or restarted here.
No existing /bundle volume, PostgreSQL data, uploads or Git branch is changed.
The new bundle is NOT activated by this script.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT = Path.home() / "Рабочий стол/rails_projects/lite/cafe_app"
QA = "cafe-app-uploads-qa-avatar-20261103"
LIVE = "cafe-app-local-3001-web"
IMAGE = "cafe-legacy-full:node14"
BASE = Path.home() / ".local/share/cafe_app"
WORK = BASE / "security_bundle_build_20261104"
BUNDLE = BASE / "bundle_carrierwave_227_20261104"
BRANCH = "feature/cafe-integration-local-20261101"
EXPECTED = {
    "Gemfile": "c5fde478cd117c12",
    "Gemfile.lock": "99f86e38d68e203e",
}


def run(*args, capture=True):
    return subprocess.run(
        args, check=True, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None
    )


def out(*args):
    return run(*args).stdout.strip()


def insist(condition, message):
    if not condition:
        raise RuntimeError("STOP: " + message)


def digest(path):
    with path.open("rb") as handle:
        h = hashlib.sha256()
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inspected(name):
    return json.loads(out("docker", "inspect", name))[0]


def preflight():
    insist(PROJECT.is_dir(), "project directory missing")
    insist(out("git", "-C", str(PROJECT), "branch", "--show-current") == BRANCH,
           "unexpected working branch")
    insist(BASE.is_dir() and not BASE.is_symlink(), "private storage missing")

    for filename, sha_prefix in EXPECTED.items():
        source = PROJECT / filename
        insist(source.is_file() and not source.is_symlink(),
               filename + " not a regular file")
        actual = digest(source)
        insist(actual.startswith(sha_prefix),
               filename + " no longer matches verified baseline")
        print(filename + " SHA256:", actual[:16])

    gemfile = (PROJECT / "Gemfile").read_text(encoding="utf-8")
    lock = (PROJECT / "Gemfile.lock").read_text(encoding="utf-8")
    declare = re.compile(
        r"(?m)^gem[ \t]+(['\"])carrierwave\1[ \t]*(?:#.*)?$"
    )
    insist(len(list(declare.finditer(gemfile))) == 1,
           "CarrierWave declaration differs from verified unpinned form")
    insist("carrierwave (2.2.3)" in lock or "carrierwave (2.2.1)" in lock,
           "unexpected existing CarrierWave lock version")

    for filename, content in [("Gemfile", gemfile), ("Gemfile.lock", lock)]:
        secret = re.search(
            r"https?://[^\s/@]+:[^\s/@]+@|(?:ghp_|glpat-|sk-proj-)"
            r"|(?:access_token|password|secret)[ \t]*[=:]",
            content, re.IGNORECASE,
        )
        insist(secret is None, filename + " appears to contain embedded credentials")

    qa = inspected(QA)
    live = inspected(LIVE)
    insist(qa["State"]["Status"] == "running", "QA web stopped")
    insist(live["State"]["Status"] == "running", "live web stopped")
    insist(qa["Config"]["Image"] == IMAGE, "QA image differs")
    insist(qa["Config"]["User"] == "1000:1000", "QA user differs")
    insist(qa["HostConfig"]["ReadonlyRootfs"], "QA root is not readonly")

    mounts = {m["Destination"]: m for m in qa["Mounts"]}
    old = mounts.get("/bundle")
    insist(old is not None and old["Type"] == "volume"
           and old["Name"] == "cafe-legacy-bundle-20261101"
           and not old["RW"],
           "existing QA gem bundle mount changed")
    insist(mounts["/app"]["Type"] == "bind" and not mounts["/app"]["RW"],
           "existing app source bind changed")

    version = out("docker", "exec", QA, "bundle", "exec", "ruby", "-e",
                  "require 'carrierwave'; print Gem.loaded_specs.fetch('carrierwave').version")
    insist(version == "2.2.3", "installed QA CarrierWave changed: " + version)
    print("QA CARRIERWAVE:", version)
    print("QA LEGACY BUNDLE READONLY: YES")

    # This is informational only: the build uses the pinned _2.2.13_ command.
    print("BUILDER DEFAULT BUNDLER:",
          out("docker", "exec", QA, "bundle", "--version"))
    print("BUILDER RUBY:", out("docker", "exec", QA, "ruby", "--version"))

    # Read-only check: the image must already exist; never pull image implicitly.
    run("docker", "image", "inspect", IMAGE)
    print("PATCHED BUNDLE PREFLIGHT PASS")


def build():
    preflight()
    insist(not WORK.exists() and not WORK.is_symlink(),
           "staging workspace already exists; inspect it before retry")
    insist(not BUNDLE.exists() and not BUNDLE.is_symlink(),
           "dedicated patched bundle directory already exists")
    insist(os.getuid() == 1000 and os.getgid() == 1000,
           "expected local owner uid/gid 1000")

    text = (PROJECT / "Gemfile").read_text(encoding="utf-8")
    needle = re.compile(r"(?m)^gem[ \t]+(['\"])carrierwave\1[ \t]*(?:#.*)?$")
    match = needle.search(text)
    insist(match is not None, "CarrierWave declaration missing")
    replacement = "gem {}carrierwave{}, '= 2.2.7'".format(match.group(1),
                                                        match.group(1))
    patched = text[:match.start()] + replacement + text[match.end():]

    # These directories are private host paths outside Git and are only
    # touched if the entire read-only preflight has passed.
    os.mkdir(str(WORK), 0o700)
    os.mkdir(str(BUNDLE), 0o700)
    (WORK / "Gemfile").write_text(patched, encoding="utf-8")
    shutil.copyfile(str(PROJECT / "Gemfile.lock"), str(WORK / "Gemfile.lock"))
    os.chmod(str(WORK / "Gemfile"), 0o600)
    os.chmod(str(WORK / "Gemfile.lock"), 0o600)
    insist(digest(PROJECT / "Gemfile.lock").startswith(EXPECTED["Gemfile.lock"]),
           "original lockfile changed during copy")

    print("PRIVATE PATCHED STAGING READY", flush=True)
    print("ORIGINAL GEMFILES UNCHANGED", flush=True)

    # No /app mount, no PostgreSQL network, volume, secrets or app media. Only
    # the isolated writable staging and newly empty bundle bind directory.
    script = r"""
set -eu
bundle _2.2.13_ --version
bundle _2.2.13_ lock --add-platform x86_64-linux
bundle _2.2.13_ update carrierwave --conservative
grep -Fq 'carrierwave (2.2.7)' /work/Gemfile.lock
echo 'CARRIERWAVE 2.2.7 LOCKED'
bundle _2.2.13_ install --jobs 2 --retry 2
bundle _2.2.13_ exec ruby -e \
  "require 'carrierwave'; v=Gem.loaded_specs.fetch('carrierwave').version.to_s; abort('Wrong installed gem') unless v=='2.2.7'; puts 'PATCHED CARRIERWAVE GEM PASS'"
"""
    docker = [
        "docker", "run", "--rm", "--network", "bridge",
        "--read-only", "--user", "1000:1000",
        "--cap-drop", "ALL", "--pids-limit", "128",
        "--memory", "2048m",
        "--security-opt", "no-new-privileges",
        "--tmpfs", "/tmp:rw,size=512m,mode=1777",
        "--env", "HOME=/tmp",
        "--env", "BUNDLE_GEMFILE=/work/Gemfile",
        "--env", "BUNDLE_PATH=/bundle",
        "--env", "BUNDLE_APP_CONFIG=/work/.bundle",
        "--env", "BUNDLE_FROZEN=false",
        "--env", "RUBYOPT=-rlogger",
        "--mount", "type=bind,source={},target=/work".format(WORK),
        "--mount", "type=bind,source={},target=/bundle".format(BUNDLE),
        "--workdir", "/work", "--entrypoint", "sh",
        IMAGE, "-c", script
    ]
    print("STARTING ISOLATED DEPENDENCY RESOLUTION", flush=True)
    subprocess.run(docker, check=True)

    insist(digest(PROJECT / "Gemfile").startswith(EXPECTED["Gemfile"]),
           "protected original Gemfile changed after build")
    insist(digest(PROJECT / "Gemfile.lock").startswith(EXPECTED["Gemfile.lock"]),
           "protected original Gemfile.lock changed after build")
    insist("carrierwave (2.2.7)" in (WORK / "Gemfile.lock").read_text(),
           "staged lockfile is not patched")
    insist(inspected(QA)["State"]["Status"] == "running", "QA container unexpectedly stopped")
    insist(inspected(LIVE)["State"]["Status"] == "running", "live container unexpectedly stopped")
    print("ISOLATED PATCHED BUNDLE VERIFIED", flush=True)
    print("NO EXISTING APP CONTAINER OR BUNDLE SWITCHED", flush=True)
    print("CANDIDATE STAGING:", WORK, flush=True)
    print("CANDIDATE BUNDLE:", BUNDLE, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--check", action="store_true",
                         help="inspect only; no writes")
    options.add_argument("--build", action="store_true",
                         help="create separate patched bundle outside project")
    args = parser.parse_args()
    try:
        if args.check:
            preflight()
        else:
            build()
    except Exception as exc:
        print("PATCHED BUNDLE BLOCKED:", type(exc).__name__,
              str(exc)[:350], file=sys.stderr)
        print("No existing Docker container, DB, upload directory or project "
              "file was intentionally modified.", file=sys.stderr)
        print("If staging already exists, inspect it; do not blindly retry.",
              file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
