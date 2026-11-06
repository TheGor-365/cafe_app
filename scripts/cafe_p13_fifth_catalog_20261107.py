#!/usr/bin/env python3
"""P1.3 FIFTH-only synthetic Cafe catalog: --check, --import, --verify.

--check is READ ONLY against PostgreSQL (disposable offline Rails mount probe).
--import --confirm-target cafe_synthetic is a SEPARATELY authorized, one-shot
catalog write; creates an exclusive private marker BEFORE the reviewed Rails
seed runner. DO NOT retry after failure or timeout.
--verify is read-only and independently checks 8/20/18/30 and zero real users,
orders, cart items or uploaded product images.
No destructive SQL, original four PG, original owner dirty checkout, media or
Docker persistent container/volume writes.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

HOME=Path.home()
REPO=HOME/"Рабочий стол/rails_projects/lite/cafe_app"
PRIVATE=HOME/".local/share/cafe_app"
SCHEMA=PRIVATE/"cafe_fifth_schema_cluster_scoped_20261107.py"
SCHEMA_BLOB="a0d2ac4546f19ab8d6c92b5b0f465269fbd4e08f"
SEEDS_BLOB="dae2eed43c78ff79a14e3bf3e83d59a649803cd4"
SOURCE="090b9d37419fcd9f393d8b686ac0f4563ef7b613"
DB="cafe_synthetic"
MARKER=PRIVATE/"cafe_p13_fifth_catalog_attempt_20261107.json"
COUNTS={"categories":8,"products":20,"product_variants":18,
        "product_modifier_options":30,"orders":0,"order_items":0,
        "order_item_modifiers":0,"users":0}

def require(value,reason):
    if not value:
        raise RuntimeError("P1.3 CATALOG STOP: "+reason)

def load_schema():
    require(os.getuid()==1000 and REPO.is_dir() and (REPO/".git").is_dir(),
            "unexpected operator or repository")
    require(SCHEMA.is_file() and not SCHEMA.is_symlink() and
            SCHEMA.stat().st_uid==os.getuid() and SCHEMA.stat().st_mode&0o077==0,
            "original pinned P1.2 private helper missing/unsafe")
    result=subprocess.run(["git","-C",str(REPO),"hash-object",str(SCHEMA)],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          check=False,timeout=20)
    require(result.returncode==0 and result.stdout.decode().strip()==SCHEMA_BLOB,
            "original private P1.2 schema helper SHA differs")
    spec=importlib.util.spec_from_file_location("p13_pinned_schema",SCHEMA)
    require(spec is not None and spec.loader is not None,
            "reviewed schema helper cannot be imported")
    schema=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(schema)
    require(schema.DB==DB and schema.SOURCE==SOURCE and
            schema.MARKER.name=="cafe_p12_fifth_schema_attempt_20261106.json" and
            schema.RUBY_GUARD_BLOB=="a95f8d95a9a4af9853f418756ffa517f99f6efe4",
            "fifth SQL identity/role/cluster guard pins differ")
    require(schema.git("rev-parse",SOURCE+":db/seeds.rb")==SEEDS_BLOB,
            "reviewed synthetic seed Git blob differs")
    return schema

def preflight():
    require(not MARKER.exists() and not MARKER.is_symlink(),
            "fixture one-shot marker already exists; NEVER retry")
    schema=load_schema()
    schema.verify_schema()  # confirmed owner P1.2: 10 tables, 8 FK,
                            # all data empty, roles, four PG/media/web protected
    ip,cluster=schema.target()
    require(cluster not in schema.protected_four(),
            "fifth PG overlaps four protected PostgreSQL instances")
    probe,mounts=schema.runtime()
    schema.offline_runner_mount_probe(probe,mounts,ip,cluster)
    print("P1.3 REVIEWED SYNTHETIC SEEDS SOURCE SHA PASS",flush=True)
    print("P1.3 FIFTH SCHEMA/ROLES + ORIGINAL FOUR PG/MEDIA/WEB PASS",flush=True)
    print("P1.3 FIFTH FIXTURE PREFLIGHT PASS — READ ONLY; NO WRITES",flush=True)
    return schema,probe,mounts,ip,cluster

def fixture_command(schema,source,mounts,ip,cluster):
    argv=schema.docker_writer(source,mounts,ip,cluster)
    old=argv[-1]
    prefix_end="; bundle exec ruby qa/security/cafe_fifth_schema_cluster_guard_20261107.rb pre; "
    required_tail=("bundle exec rails db:schema:load; "
                   "bundle exec ruby qa/security/cafe_fifth_schema_cluster_guard_20261107.rb post")
    require(old.count(prefix_end)==1 and old.endswith(prefix_end+required_tail),
            "original reviewed fifth-only runner shell differs")
    prefix=old.split(prefix_end,1)[0]
    require(prefix.startswith('set -eu; password="$(cat /tmp/cafe_p12_secret)"; ') and
            prefix.endswith("unset password"),
            "original fifth-only password isolation changed")
    # Before importing, run the original Ruby guard in post-schema/pre-fixtures
    # mode to prove expected fifth cluster and exact zero-data schema.
    shell=(prefix+
           "; bundle exec ruby qa/security/cafe_fifth_schema_cluster_guard_20261107.rb post"+
           "; bundle exec rails runner 'Rails.application.load_seed'")
    require(not any(x in shell for x in (
            "db:schema:load","db:seed","db:migrate","db:drop","db:reset",
            "db:prepare","cafe_fifth_schema_cluster_guard_20261107.rb pre")),
            "unreviewed SQL/seed command or pre-schema guard present")
    for flag in ("--rm","--read-only","--pull=never",
                 "--cap-drop=ALL","--user=1000:1000",
                 "--network="+schema.NETWORK,"--env=RAILS_ENV=test",
                 "--env=CAFE_P12_EXPECTED_CLUSTER_ID="+cluster):
        require(flag in argv,"Docker fifth-only runner safety flag missing")
    argv[-1]=shell
    return argv

def import_once(ack):
    require(ack==DB,"explicit --confirm-target cafe_synthetic required")
    schema,probe,mounts,ip,cluster=preflight()
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="cafe-p13-fifth-fixtures-") as stage:
        source=schema.build_source(probe,stage)
        seeds=source/"db/seeds.rb"
        require(seeds.is_file() and not seeds.is_symlink() and
                schema.git("hash-object",str(seeds))==SEEDS_BLOB,
                "staged immutable Rails demo seeds SHA differs")
        argv=fixture_command(schema,source,mounts,ip,cluster)
        require(schema.target()==(ip,cluster) and
                schema.sql("SELECT count(*) FROM public.products;")=="0" and
                schema.sql("SELECT count(*) FROM public.users;")=="0",
                "fifth PG target or empty source data changed")
        record={"operation":"fifth-only immutable demo catalog once",
                "database":DB,"cluster":cluster,"source":SOURCE,
                "schema_blob":SCHEMA_BLOB,"seeds_blob":SEEDS_BLOB,
                "started":int(time.time())}
        flags=os.O_CREAT|os.O_EXCL|os.O_WRONLY
        if hasattr(os,"O_NOFOLLOW"):flags|=os.O_NOFOLLOW
        fd=os.open(str(MARKER),flags,0o600)
        with os.fdopen(fd,"w",encoding="utf-8") as out:
            json.dump(record,out,sort_keys=True)
            out.write("\n")
        print("P1.3 FIFTH FIXTURE ONE-SHOT MARKER RECORDED",flush=True)
        print("P1.3 APPLYING REVIEWED SYNTHETIC SEEDS — NO USERS/ORDERS",flush=True)
        try:
            run=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                               check=False,timeout=240)
        except (OSError,subprocess.TimeoutExpired):
            raise RuntimeError("P1.3 CATALOG STOP: one-shot runner timeout/unavailable")
        require(run.returncode==0 and
                b"20 curated products" in run.stdout and
                b"Demo drinks configurable: 6" in run.stdout,
                "one-shot seed runner failed or returned incomplete proof")
    print("P1.3 REVIEWED FIFTH-ONLY SEED RUNNER PASS",flush=True)
    print("P1.3 INDEPENDENT --verify REQUIRED BEFORE E2E",flush=True)

def verify():
    schema=load_schema()
    require(MARKER.is_file() and not MARKER.is_symlink(),
            "fifth fixture one-shot marker missing")
    st=MARKER.stat()
    require(st.st_uid==os.getuid() and st.st_mode&0o077==0 and
            st.st_size<2048,"fixture marker mode/owner/size differs")
    record=json.loads(MARKER.read_text(encoding="utf-8"))
    require(record.get("operation")=="fifth-only immutable demo catalog once" and
            record.get("database")==DB and record.get("source")==SOURCE and
            record.get("schema_blob")==SCHEMA_BLOB and
            record.get("seeds_blob")==SEEDS_BLOB,
            "fixture one-shot marker identity differs")
    require(schema.MARKER.is_file() and not schema.MARKER.is_symlink(),
            "verified P1.2 schema marker absent")
    schema_mark=json.loads(schema.MARKER.read_text(encoding="utf-8"))
    ip,cluster=schema.target()
    require(record.get("cluster")==cluster and
            schema_mark.get("cluster")==cluster,
            "fifth schema/fixture markers refer to different PG clusters")
    first=schema.protected_four()
    require(cluster not in first,"fifth PG overlaps protected four")
    require(schema.sql("SELECT string_agg(tablename,',' ORDER BY tablename) FROM pg_tables WHERE schemaname='public';")==",".join(schema.TABLES),
            "unexpected fifth public schema tables")
    require(schema.sql("SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner='cafe_synth_owner';")=="10" and
            schema.sql("SELECT count(*) FROM pg_sequences WHERE schemaname='public' AND sequenceowner='cafe_synth_owner';")=="8",
            "fifth table/sequence ownership differs")
    require(schema.sql("SELECT count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' AND c.contype='f';")=="8",
            "fifth FK count differs")
    require(schema.sql("SELECT string_agg(version,',' ORDER BY version) FROM public.schema_migrations;")==",".join(schema.canonical_versions()),
            "fifth reviewed migration set differs")
    for table,count in COUNTS.items():
        require(schema.sql("SELECT count(*) FROM public."+table+";")==str(count),
                "fixture exact table count differs: "+table)
    require(schema.sql("SELECT count(DISTINCT heading) FROM public.categories;")=="8" and
            schema.sql("SELECT count(DISTINCT name) FROM public.products;")=="20",
            "duplicate catalog business keys found")
    require(schema.sql("SELECT count(*) FROM public.products WHERE category_id IS NULL OR price<=0 OR available IS DISTINCT FROM TRUE OR image IS NOT NULL;")=="0",
            "product/price/image safety differs")
    require(schema.sql("SELECT count(*) FROM (SELECT product_id,count(*) n,count(DISTINCT code) c FROM public.product_variants GROUP BY product_id) x WHERE n=3 AND c=3;")=="6",
            "expected 6 configurable drinks, 3 unique variants each")
    require(schema.sql("SELECT count(*) FROM (SELECT product_id,count(*) n,count(DISTINCT group_code||':'||code) c FROM public.product_modifier_options GROUP BY product_id) x WHERE n=5 AND c=5;")=="6",
            "expected 6 configurable drinks, 5 unique options each")
    require(schema.sql("SELECT count(*) FROM public.product_variantS WHERE price_cents<0 OR available IS DISTINCT FROM TRUE;".replace("product_variantS","product_variants"))=="0",
            "variant price/availability differs")
    require(schema.sql("SELECT count(*) FROM public.product_modifier_options WHERE group_code NOT IN ('milk','syrup','shot') OR price_cents<0 OR available IS DISTINCT FROM TRUE;")=="0",
            "option group/price/availability differs")
    for group,count in (("milk","12"),("syrup","12"),("shot","6")):
        require(schema.sql("SELECT count(*) FROM public.product_modifier_options WHERE group_code='"+group+"';")==count,
                "modifier group distribution differs")
    for table in schema.DATA_TABLES:
        for action in ("SELECT","INSERT","UPDATE","DELETE"):
            require(schema.sql("SELECT has_table_privilege('cafe_synth_app','public."+table+"','"+action+"');")=="t",
                    "application CRUD grant differs")
    require(schema.sql("SELECT has_schema_privilege('cafe_synth_app','public','CREATE');")=="f",
            "application role unexpectedly gained DDL privilege")
    require(schema.protected_four()==first,
            "protected four PG identities or baseline changed")
    print("P1.3 FIFTH SCHEMA/ACL/MIGRATIONS + FOUR PROTECTED PG PASS",flush=True)
    print("P1.3 EXACT 8 CATEGORIES / 20 PRODUCTS / 18 VARIANTS / 30 OPTIONS PASS",flush=True)
    print("P1.3 ZERO USERS / ORDERS / CARTS / PRODUCT IMAGES PASS",flush=True)
    print("P1.3 SIX CONFIGURABLE DRINKS / UNIQUE KEYS / NO APP DDL PASS",flush=True)
    print("P1.3 INDEPENDENT CATALOG VERIFY PASS — NO WRITES",flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check",action="store_true")
    mode.add_argument("--import",dest="one_shot",action="store_true")
    mode.add_argument("--verify",action="store_true")
    parser.add_argument("--confirm-target")
    opts=parser.parse_args()
    try:
        if opts.check:
            require(opts.confirm_target is None,"read-only check rejects write confirmation")
            preflight()
        elif opts.one_shot:
            import_once(opts.confirm_target)
        else:
            require(opts.confirm_target is None,"read-only verify rejects write confirmation")
            verify()
    except Exception as exc:
        msg=str(exc)
        if not msg.startswith("P1.3 CATALOG STOP:"):
            msg="P1.3 CATALOG STOP: internal integrity / SQL / runtime failure"
        print(msg,file=sys.stderr,flush=True)
        print("Preserve fifth DB and both attempt markers. Never retry one-shot fixture import.",file=sys.stderr,flush=True)
        raise SystemExit(1)

if __name__=="__main__":
    main()
