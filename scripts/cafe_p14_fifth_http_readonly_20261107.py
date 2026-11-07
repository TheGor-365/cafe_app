#!/usr/bin/env python3
"""Owner-only P1.4 fifth synthetic PG READ-ONLY Rack HTTP guest smoke.

Only --probe is supported. Reuses the independently verified fifth P1.3
fixture marker/rows and P1.2 cluster source. Starts ONE disposable
--rm no-host-port Docker Rails runner on fifth-only internal Docker network.
Uses strictly SCRAM-authenticated cafe_synth_app + PGOPTIONS default_transaction_read_only=on;
Ruby executes GET only through Rails ActionDispatch in-process, checks guests,
catalog, account/admin access and database row counts. No fixture loading,
no rails test, seeds, migrations, schema writes, owner checkout changes,
existing media or persistent Docker container/volume changes.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HOME=Path.home()
REPO=HOME/"Рабочий стол/rails_projects/lite/cafe_app"
PRIVATE=HOME/".local/share/cafe_app"
P13=PRIVATE/"cafe_p13_fifth_catalog_20261107.py"
P13_BLOB="8dbf42b86a4c617fb69c986e9103fce631d3a49e"
RUBY=PRIVATE/"cafe_p14_fifth_http_readonly_20261107.rb"
RUBY_BLOB="299de6d74f55fe04c222875ca424b6c2c7443b5f"
DB="cafe_synthetic"
NET="cafe-upload-security-synthetic-net-20261105"
PG="cafe-upload-security-synthetic-pg-20261105"
EXPECTED_STDOUT=(
    b"P1.4 FIFTH APP SCRAM ROLE / PG16 / READ-ONLY SQL / 8-20-18-30 PASS",
    b"P1.4 GUEST HTTP HOME/MENU/SEARCH/CART/INFO/CATERING PASS",
    b"P1.4 PRODUCT DETAILS / DEVISE GUEST GET ROUTES PASS",
    b"P1.4 GUEST ACCOUNT / ADMIN GET ACCESS CONTROL PASS",
    b"P1.4 REAL RAILS RACK GET PROBE PASS",
)

def require(condition,reason):
    if not condition:
        raise RuntimeError("P1.4 HTTP READONLY STOP: "+reason)

def checked_private(path,git_blob,label):
    require(path.is_file() and not path.is_symlink(),
            "private "+label+" helper missing")
    st=path.stat()
    require(st.st_uid==os.getuid() and st.st_mode&0o077==0,
            "private "+label+" helper permissions differ")
    result=subprocess.run(["git","-C",str(REPO),"hash-object",str(path)],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          check=False,timeout=25)
    require(result.returncode==0 and
            result.stdout.decode("ascii").strip()==git_blob,
            "private "+label+" reviewed SHA differs")

def pinned_module():
    require(os.getuid()==1000 and REPO.is_dir() and (REPO/".git").is_dir(),
            "unexpected Linux user/repository")
    checked_private(P13,P13_BLOB,"P1.3")
    checked_private(RUBY,RUBY_BLOB,"HTTP Ruby")
    spec=importlib.util.spec_from_file_location("p14_pinned_p13_fixtures",P13)
    require(spec is not None and spec.loader is not None,
            "private P1.3 helper import unavailable")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(module.DB==DB and
            module.SCHEMA_BLOB=="a0d2ac4546f19ab8d6c92b5b0f465269fbd4e08f" and
            module.SEEDS_BLOB=="dae2eed43c78ff79a14e3bf3e83d59a649803cd4" and
            module.MARKER.name=="cafe_p13_fifth_catalog_attempt_20261107.json",
            "reviewed fixture provenance or target differs")
    return module

def app_secret(schema,cluster):
    roles=schema.load_pin(schema.ROLES_HELPER,schema.ROLES_BLOB,"p14_fifth_roles")
    require(roles.PG==PG and roles.NETWORK==NET and roles.DB==DB and
            roles.APP=="cafe_synth_app",
            "fifth-only app role target differs")
    password=roles.secret_audit()   # Only private memory, never printed/passed argv.
    require(roles.MARKER.is_file() and not roles.MARKER.is_symlink(),
            "role attempt marker unavailable")
    record=json.loads(roles.MARKER.read_text(encoding="utf-8"))
    require(record.get("fifth_cluster")==cluster and
            record.get("operation")=="restore_fifth_scoped_roles_once" and
            record.get("app_secret_sha256")==hashlib.sha256(password).hexdigest() and
            record.get("sql_blob")==roles.SQL_BLOB,
            "original role marker/credential/cluster differs")
    return roles.APP_SECRET

def runner_command(schema,source,mounts,ip,cluster,app_file):
    argv=schema.docker_writer(source,mounts,ip,cluster)
    original=argv[-1]
    require(original.count("; bundle exec rails db:schema:load;")==1 and
            original.endswith("bundle exec ruby qa/security/cafe_fifth_schema_cluster_guard_20261107.rb post"),
            "original reviewed Docker writer shell contract differs")
    old_secret="--mount=type=bind,source={},target=/tmp/cafe_p12_secret,readonly".format(schema.SECRET)
    new_secret="--mount=type=bind,source={},target=/tmp/cafe_p12_secret,readonly".format(app_file)
    require(argv.count(old_secret)==1 and old_secret!=new_secret,
            "original admin secret mount identity differs")
    argv[argv.index(old_secret)]=new_secret
    old_options="--env=PGOPTIONS=-c role=cafe_synth_owner -c search_path=public"
    require(argv.count(old_options)==1,"superuser schema role contract differs")
    argv[argv.index(old_options)]="--env=PGOPTIONS=-c default_transaction_read_only=on -c search_path=public"
    shell=('set -eu; '
           'password="$(cat /tmp/cafe_p12_secret)"; '
           'export DATABASE_URL="postgresql://cafe_synth_app:$password@cafe-synthetic-postgres:5432/cafe_synthetic"; '
           'unset password; '
           'bundle exec rails runner qa/security/cafe_p14_fifth_http_readonly_20261107.rb')
    require(not any(x in shell for x in (
       "db:schema:load","db:seed","db:prepare","db:migrate","db:drop",
       "db:reset","cafe_fifth_schema_cluster_guard_20261107.rb")),
       "unreviewed Rails writer or old privileged guard present")
    require("--rm" in argv and "--pull=never" in argv and
            "--read-only" in argv and "--cap-drop=ALL" in argv and
            "--security-opt=no-new-privileges" in argv and
            "--network="+NET in argv and "--user=1000:1000" in argv and
            "--env=RAILS_ENV=test" in argv and
            "--env=CAFE_P12_TARGET="+DB in argv and
            "--env=CAFE_P12_EXPECTED_CLUSTER_ID="+cluster in argv and
            not any(x.startswith(("--publish","-p=","--network=host","--privileged")) for x in argv),
            "fifth-only isolated test network/runtime permissions differ")
    require(new_secret in argv and old_secret not in argv,
            "app SCRAM credential mount not isolated")
    argv[-1]=shell
    return argv

def probe():
    p13=pinned_module()
    p13.verify()     # READ ONLY: 8/20/18/30, zero users/orders, protected four
    schema=p13.load_schema()
    ip,cluster=schema.target()
    require(cluster not in schema.protected_four(),
            "fifth PG overlaps protected four")
    secret=app_secret(schema,cluster)
    probe,mounts=schema.runtime()
    # No original application/QA media mounts. Exact reviewed source snapshot.
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="cafe-p14-http-readonly-") as stage:
        source=schema.build_source(probe,stage)
        ruby=source/"qa/security/cafe_p14_fifth_http_readonly_20261107.rb"
        require(not ruby.exists() and not ruby.is_symlink(),
                "reviewed source already contains P1.4 path")
        with ruby.open("xb") as file:
            file.write(RUBY.read_bytes())
        require(schema.git("hash-object",str(ruby))==RUBY_BLOB,
                "staged HTTP Ruby checksum mismatch")
        argv=runner_command(schema,source,mounts,ip,cluster,secret)
        require(schema.target()==(ip,cluster),
                "fifth target changed before read-only Rack probe")
        print("P1.4 FIFTH CLUSTER/APP SECRET / READ-ONLY RAILS TARGET PASS",flush=True)
        try:
            result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                  check=False,timeout=180)
        except (OSError,subprocess.TimeoutExpired):
            raise RuntimeError("P1.4 HTTP READONLY STOP: ephemeral runner timeout/unavailable")
        # Do NOT expose raw stdout/stderr (may include Rails stack/DSN).
        require(result.returncode==0,
                "Rack guest GET failed; raw private logs suppressed")
        require(all(item in result.stdout for item in EXPECTED_STDOUT),
                "Ruby Rack GET proof missing expected exact marker")
    require(schema.target()==(ip,cluster),
            "fifth cluster changed after Rack probe")
    p13.verify()     # Independent database counts and original PG postflight
    print("P1.4 FIFTH APP-ROLE READ-ONLY RACK HTTP GUEST SMOKE PASS",flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe",action="store_true",required=True)
    args=parser.parse_args()
    try:
        if args.probe:
            probe()
    except Exception as exc:
        message=str(exc)
        if not message.startswith("P1.4 HTTP READONLY STOP:"):
            message="P1.4 HTTP READONLY STOP: guarded integrity/runner failure"
        print(message,file=sys.stderr,flush=True)
        print("No retest with alternate DB, destructive Rails test, marker deletion or Docker restart.",
              file=sys.stderr,flush=True)
        raise SystemExit(1)

if __name__=="__main__":main()
