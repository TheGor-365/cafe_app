#!/usr/bin/env python3
"""Read-only preflight of owner's isolated cafe QA before dependency changes.

Never creates, edits, stops, restarts or deletes Docker containers/volumes,
PostgreSQL rows or project files. Does not expose SQL data or secrets.
"""
import hashlib
import http.client
import json
from pathlib import Path
import subprocess

PROJECT = Path.home() / "Рабочий стол/rails_projects/lite/cafe_app"
QA = "cafe-app-uploads-qa-avatar-20261103"
QA_DB = "cafe-upload-qa-pg-20261103"
LIVE = "cafe-app-local-3001-web"
LIVE_DB = "cafe-app-db"
NETWORK = "cafe-upload-qa-net-20261103"
UPLOADS = Path.home() / ".local/share/cafe_app/uploads_qa_20261103"
TARGETS = [
    "Gemfile", "Gemfile.lock",
    "app/uploaders/avatar_uploader.rb",
    "app/uploaders/image_uploader.rb",
    "app/models/user.rb",
    "app/views/layouts/application.html.erb",
    "app/assets/stylesheets/zzzz_cafe_account_corner.scss",
]


def output(*command):
    return subprocess.check_output(command, text=True,
                                   stderr=subprocess.DEVNULL).strip()


def inspect(name):
    return json.loads(output("docker", "inspect", name))[0]


def assert_true(condition, message):
    if not condition:
        raise RuntimeError("PREFLIGHT BLOCKED: " + message)


def sql(name, query):
    return output("docker", "exec", "--user", "postgres", name,
                  "psql", "-X", "-At", "-U", "postgres", "-d", "cafe",
                  "-c", query)


def status(port, path):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=8)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        response.read()
        return response.status
    finally:
        connection.close()


def main():
    assert_true(PROJECT.is_dir(), "local project directory missing")

    qa, qa_db, live, live_db = (
        inspect(QA), inspect(QA_DB), inspect(LIVE), inspect(LIVE_DB)
    )
    for name, item in [(QA, qa), (QA_DB, qa_db), (LIVE, live), (LIVE_DB, live_db)]:
        assert_true(item["State"]["Status"] == "running", name + " is not running")

    def networks(item):
        return set(item["NetworkSettings"]["Networks"])

    assert_true(networks(qa) == {NETWORK}, "QA web network changed")
    assert_true(networks(qa_db) == {NETWORK}, "QA DB network changed")
    assert_true(NETWORK not in networks(live), "production web touches QA network")
    assert_true(NETWORK not in networks(live_db), "production DB touches QA network")
    assert_true(qa["HostConfig"]["ReadonlyRootfs"], "QA filesystem not readonly")

    mounts = {m["Destination"]: m for m in qa["Mounts"]}
    assert_true(not mounts["/app"]["RW"], "QA app bind unexpectedly writable")
    assert_true(mounts["/app/public/uploads"]["RW"],
                "QA media mount not writable")
    assert_true(mounts["/app/public/uploads"]["Source"] == str(UPLOADS),
                "QA media mount changed")

    env = dict(item.split("=", 1) for item in qa["Config"]["Env"])
    assert_true(env.get("DATABASE_URL") ==
                "postgresql://postgres@cafe-app-db:5432/cafe",
                "QA DB URL no longer matches isolated DB alias")

    qa_id = sql(QA_DB, "SELECT system_identifier::text FROM pg_control_system();")
    live_id = sql(LIVE_DB, "SELECT system_identifier::text FROM pg_control_system();")
    assert_true(qa_id.isdigit() and live_id.isdigit() and qa_id != live_id,
                "QA and live PostgreSQL cluster identity mismatch")

    count, temporary = sql(
        QA_DB,
        "SELECT COUNT(*), COUNT(*) FILTER (WHERE id=21) FROM products;"
    ).split("|")
    assert_true(count.isdigit() and temporary.isdigit(), "unexpected SQL output")
    print("QA PRODUCT COUNT:", count)
    print("DISPOSABLE PRODUCT ID 21:", temporary)

    for port, path in [(3001, "/info"), (3002, "/menu")]:
        code = status(port, path)
        print("HTTP {} {}: {}".format(port, path, code))
        assert_true(code == 200, "HTTP smoke failed on port " + str(port))

    print("=== LOCAL SOURCE SHA256 (READ-ONLY) ===")
    for name in TARGETS:
        path = PROJECT / name
        if path.is_file() and not path.is_symlink():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            print(name, digest)
        else:
            print(name, "MISSING_OR_SYMLINK")

    version = output(
        "docker", "exec", QA, "bundle", "exec", "ruby", "-e",
        "require 'carrierwave'; print Gem.loaded_specs.fetch('carrierwave').version"
    )
    print("QA INSTALLED CARRIERWAVE:", version)
    if version != "2.2.7":
        print("PUBLIC UPLOADS BLOCKED: local QA has not been upgraded to 2.2.7")

    assert_true(count == "20" and temporary == "0",
                "QA product deletion not yet confirmed; do not claim CRUD SQL pass")

    print("READ-ONLY SECURITY PREFLIGHT PASS")
    print("NO DOCKER/DB/PROJECT CHANGES MADE")


if __name__ == "__main__":
    main()
