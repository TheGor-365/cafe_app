#!/usr/bin/env python3
"""Read-only audit before any schema/fixture load into fifth synthetic PostgreSQL.

--check only. No DDL, DML, Docker mutations, secret output, file writes,
Git branch switches, migrations, seeds, or Rails process launch.
This script is a GATE, not a schema loader.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys

REPO = Path.home() / "Рабочий стол/rails_projects/lite/cafe_app"
REF = "refs/remotes/origin/feature/cafe-synthetic-schema-readonly-gate-20261105"
ROLE_SCRIPT = Path.home() / ".local/share/cafe_app/cafe_synthetic_pg_roles_v2_20261105.py"
ROLE_SHA256 = "ecab358e7edcbc7828621e339ee7211077380ffba39d2046011baea556b8bdea"
EXPECTED_BLOBS = {
    "db/schema.rb": "2506954d1ea3e6368eb219956863b2acb91441c8",
    "db/seeds.rb": "dae2eed43c78ff79a14e3bf3e83d59a649803cd4",
    "db/migrate/20261102000100_create_cafe_drink_options.rb":
        "1d0ebdd9f4d7b5d70fb13868da97f76dd722f65e",
}
EXPECTED_TABLES = {
    "categories", "products", "product_variants", "product_modifier_options",
    "orders", "order_items", "order_item_modifiers", "users",
}


def require(condition, reason):
    if not condition:
        raise RuntimeError("CAFE SYNTHETIC SCHEMA BLOCKED: " + reason)


def git(*args):
    result = subprocess.run(["git", "-C", str(REPO), *args],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=18, check=False)
    require(result.returncode == 0, "protected Git object lookup failed")
    return result.stdout


def blob_content(relpath, expected):
    object_id = git("rev-parse", REF + ":" + relpath).decode().strip()
    require(object_id == expected,
            "reviewed Git blob for " + relpath + " changed")
    return git("cat-file", "blob", object_id)


def role_audit():
    require(os.getuid() == 1000, "expected private QA operator UID 1000")
    require(ROLE_SCRIPT.is_file() and not ROLE_SCRIPT.is_symlink(),
            "SHA-pinned v2 synthetic role helper is missing")
    require(ROLE_SCRIPT.stat().st_uid == os.getuid() and
            ROLE_SCRIPT.stat().st_mode & 0o022 == 0,
            "synthetic role helper owner or permissions changed")
    require(hashlib.sha256(ROLE_SCRIPT.read_bytes()).hexdigest() == ROLE_SHA256,
            "SHA-pinned v2 synthetic role helper differs")
    spec = importlib.util.spec_from_file_location("cafe_synth_roles_verified",
                                                  ROLE_SCRIPT)
    require(spec is not None and spec.loader is not None,
            "unable to load v2 role gate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Complete, read-only: existing four PG identities + fifth PG, SCRAM,
    # role privileges, incorrect/correct authentication and zero tables.
    module.verify()


def check():
    require(REPO.is_dir() and (REPO / ".git").exists(),
            "expected original cafe_app checkout missing")
    require(git("cat-file", "-t", REF).decode().strip() == "commit",
            "expected synthetic-schema remote ref missing")
    source = {}
    for path, sha in EXPECTED_BLOBS.items():
        source[path] = blob_content(path, sha)

    schema = source["db/schema.rb"].decode("utf-8")
    seed = source["db/seeds.rb"].decode("utf-8")
    migration = source["db/migrate/20261102000100_create_cafe_drink_options.rb"].decode("utf-8")

    require(schema.startswith("ActiveRecord::Schema.define(version: 2026_11_02_000100) do\n"),
            "reviewed Rails schema version differs")
    tables = re.findall(r'^  create_table "([^"]+)"', schema, re.M)
    require(len(tables) == len(EXPECTED_TABLES) and
            set(tables) == EXPECTED_TABLES,
            "expected eight Rails application tables changed")
    foreign_keys = re.findall(r'^  add_foreign_key "([^"]+)", "([^"]+)"', schema, re.M)
    require(len(foreign_keys) == 8, "expected eight Rails foreign keys changed")
    require('create_table "users"' in schema and
            't.string "encrypted_password"' in schema,
            "tracked Devise schema fields changed")
    require("unless Rails.env.development? || Rails.env.test?" in seed and
            'demo_items = [' in seed and
            'configurable_drinks =' in seed,
            "synthetic demo seeds missing safety guards")
    require(not re.search(r"\b(?:User|AdminUser)\.(?:create|create!|find_or_create_by|first_or_create)\b",
                          seed),
            "reviewed seeds unexpectedly create user accounts")
    require("class CreateCafeDrinkOptions < ActiveRecord::Migration[6.0]" in migration,
            "tracked drink options migration contract differs")
    role_audit()
    print("CANONICAL RAILS SCHEMA / DEMO SEEDS / MIGRATION GIT BLOBS PASS",
          flush=True)
    print("EIGHT APP TABLES / EIGHT FKS / NO REAL OR SYNTHETIC USER IMPORT PASS",
          flush=True)
    print("FIFTH SCRAM DB EMPTY / SCOPED ROLES / FOUR SOURCE DB ISOLATION PASS",
          flush=True)
    print("SYNTHETIC RAILS SCHEMA READ-ONLY PREFLIGHT COMPLETE — NO CHANGES",
          flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", required=True, action="store_true")
    parser.parse_args()
    try:
        check()
    except Exception as exc:
        msg = str(exc)
        if not msg.startswith("CAFE SYNTHETIC SCHEMA BLOCKED:"):
            msg = "CAFE SYNTHETIC SCHEMA BLOCKED: internal audit failed"
        print(msg, file=sys.stderr)
        print("Do not load schema, run migrations, restore data or alter Docker.",
              file=sys.stderr)
        sys.exit(1)
