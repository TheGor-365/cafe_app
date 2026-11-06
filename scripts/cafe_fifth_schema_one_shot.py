#!/usr/bin/env python3
"""Fifth-only one-shot synthetic Rails schema loader; no fixtures or source changes.

--check       READ ONLY: owner P1/P1.1, protected four PG/media/web,
              empty fifth PostgreSQL, SCRAM, exact dependencies/target, no attempt.
--create-schema --confirm-target cafe_synthetic
              ONE-SHOT fifth-only DDL; records non-retry marker BEFORE Docker.
--verify-schema
              READ ONLY: independently inspect fifth schema and original four.

No destructive Rails database tasks, migrations, or fixture imports.
"""
from __future__ import annotations
import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import ipaddress
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
RUNTIME_HELPER=PRIVATE/"cafe_synthetic_p1_rails_probe_v6_20261105.py"
RUNTIME_BLOB="13ac9907b94d4beafe5b0be4707e197b4b24069a"
OLD_PG_HELPER=PRIVATE/"cafe_synthetic_pg_scram_v1_20261105.py"
OLD_PG_BLOB="153ffca0535e0c42921d18ea39943bb4a92795fd"
RUBY_GUARD_BLOB="e5dae1c3b740acf3298b5baf12747f69d4d2a721"
SOURCE="090b9d37419fcd9f393d8b686ac0f4563ef7b613"
PG="cafe-upload-security-synthetic-pg-20261105"
NETWORK="cafe-upload-security-synthetic-net-20261105"
DB="cafe_synthetic"
IMAGE="cafe-legacy-full:node14"
SECRET=PRIVATE/"synthetic_pg_scram_20261105/password"
MARKER=PRIVATE/"cafe_p12_fifth_schema_attempt_20261106.json"
OLD_SCHEMA_MARKER=PRIVATE/"cafe_p12_fifth_schema_attempt_20261105.json"
ROLES_HELPER=PRIVATE/"cafe_p12_fifth_scoped_roles_v1_20261106.py"
ROLES_BLOB="a02f23a9cd2c982309a1649ea0b314618f9da94a"
TABLES=("ar_internal_metadata","categories","order_item_modifiers",
        "order_items","orders","product_modifier_options","product_variants",
        "products","schema_migrations","users")
DATA_TABLES=("categories","products","product_variants",
             "product_modifier_options","orders","order_items",
             "order_item_modifiers","users")

def require(value,reason):
    if not value: raise RuntimeError("P1.2 SCHEMA STOP: "+reason)

def call(argv,timeout=35):
    try:
        r=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         check=False,timeout=timeout)
    except (OSError,subprocess.TimeoutExpired):
        raise RuntimeError("P1.2 SCHEMA STOP: controlled command unavailable/timeout")
    require(r.returncode==0,"read-only inspection failed")
    require(len(r.stdout)<120000,"unexpected inspection output size")
    return r.stdout

def git(*args):
    return call(["git","-C",str(REPO),*args]).decode().strip()

def load_pin(path,blob,name):
    require(path.is_file() and not path.is_symlink() and
            path.stat().st_uid==os.getuid() and path.stat().st_mode&0o022==0,
            "pinned local helper missing or writable by other users")
    require(git("hash-object",str(path))==blob,"pinned local helper SHA mismatch")
    spec=importlib.util.spec_from_file_location(name,path)
    require(spec is not None and spec.loader is not None,"helper loading blocked")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def docker_json(*args):
    return json.loads(call(["docker",*args]).decode())

def sql(query):
    require(query.lstrip().upper().startswith(("SELECT ","SHOW ")),
            "non-readonly SQL audit rejected")
    return call(["docker","exec","--user","postgres",PG,
                 "psql","-X","-At","-v","ON_ERROR_STOP=1",
                 "-U","postgres","-d",DB,"-c",query]).decode().strip()

def target():
    n=docker_json("network","inspect",NETWORK)
    require(len(n)==1 and n[0]["Name"]==NETWORK and n[0]["Internal"] is True,
            "fifth-only network unavailable")
    members={x.get("Name") for x in (n[0].get("Containers") or {}).values()}
    require(members=={PG},"fifth network contains unexpected member")
    values=docker_json("inspect","--type=container",PG)
    require(len(values)==1,"fifth PostgreSQL object unavailable")
    pg=values[0]
    host=pg["HostConfig"]
    require(pg["Name"].lstrip("/")==PG and
            pg["State"]["Status"]=="running" and
            pg["Config"]["Image"]=="postgres:16" and
            host["ReadonlyRootfs"] is True and
            host["Memory"]==768*1024*1024 and
            host["PidsLimit"]==256 and
            host["RestartPolicy"]["Name"]=="no" and
            not host.get("PortBindings") and
            set(pg["NetworkSettings"]["Networks"])=={NETWORK},
            "wrong fifth PostgreSQL identity or isolation")
    mounts=pg["Mounts"]
    require(len(mounts)==1 and mounts[0]["Type"]=="bind" and
            mounts[0]["Source"]==str(SECRET) and
            mounts[0]["Destination"]=="/run/secrets/cafe_synthetic_postgres" and
            mounts[0]["RW"] is False,"fifth database credential mount differs")
    ip=pg["NetworkSettings"]["Networks"][NETWORK].get("IPAddress","")
    try: address=ipaddress.ip_address(ip)
    except ValueError: raise RuntimeError("P1.2 SCHEMA STOP: invalid fifth PG IP")
    require(address.version==4 and address.is_private,"unexpected fifth PG network IP")
    require(sql("SHOW server_version_num;").startswith("16"),
            "unexpected PostgreSQL major version")
    identifier=sql("SELECT system_identifier::text FROM pg_control_system();")
    require(identifier.isdigit() and len(identifier)>12,"fifth cluster ID invalid")
    return str(address),identifier

def secret_audit():
    parent=SECRET.parent
    require(parent.is_dir() and not parent.is_symlink() and
            parent.stat().st_uid==os.getuid() and parent.stat().st_mode&0o077==0,
            "fifth credential directory permissions differ")
    require(SECRET.is_file() and not SECRET.is_symlink() and
            SECRET.stat().st_uid==os.getuid() and SECRET.stat().st_mode&0o022==0,
            "fifth credential file permissions differ")
    require(re.fullmatch(rb"[A-Za-z0-9_-]{48,128}",SECRET.read_bytes()) is not None,
            "fifth SCRAM credential content format differs")

def canonical_versions():
    names=git("ls-tree","-r","--name-only",SOURCE,"--","db/migrate").splitlines()
    versions=[]
    for name in names:
        m=re.fullmatch(r"db/migrate/([0-9]+)_[A-Za-z0-9_]+\.rb",name)
        if m: versions.append(m.group(1))
    require(versions and len(set(versions))==len(versions) and
            "20261102000100" in versions,"canonical migration set missing")
    return sorted(versions)

def runtime():
    require(os.getuid()==1000 and REPO.is_dir() and
            (REPO/".git").exists(),"wrong user/repository")
    require(git("cat-file","-t",SOURCE)=="commit","original reviewed source not fetched")
    probe=load_pin(RUNTIME_HELPER,RUNTIME_BLOB,"p12_reviewed_runtime")
    # The original probe.probe() calls a gate that expects ZERO login roles.
    # After PR63, the pinned role helper verifies the recovered role state.
    # Genuine Rails boot and mounts are checked by offline_runner_mount_probe.
    mounts=probe.allowed_gem_mounts()
    require(len(mounts)==3 and
            any("target=/bundle,readonly" in m for m in mounts) and
            any("target=/app/Gemfile,readonly" in m for m in mounts) and
            any("target=/app/Gemfile.lock,readonly" in m for m in mounts),
            "reviewed Linux Ruby dependency mounts differ")
    return probe,mounts

def role_recovery_verified():
    roles=load_pin(ROLES_HELPER,ROLES_BLOB,"p12_scoped_roles_recovered")
    require(roles.PG==PG and roles.DB==DB and roles.NETWORK==NETWORK and
            roles.MARKER.is_file(),"recovered role source or marker differs")
    with redirect_stdout(io.StringIO()):
        roles.verify()  # READ ONLY, includes SCRAM and original four protection
    return roles

def check():
    require(not MARKER.exists() and not MARKER.is_symlink() and
            not OLD_SCHEMA_MARKER.exists() and not OLD_SCHEMA_MARKER.is_symlink(),
            "old/new one-shot schema attempt marker exists; never retry")
    role_recovery_verified()
    probe,mounts=runtime()
    secret_audit()
    ip,ident=target()
    require(ident not in protected_four(),
            "fifth PG ID overlaps original four or postflight baseline unavailable")
    require(sql("SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';")=="0",
            "fifth public schema not empty")
    require(sql("SELECT COUNT(*) FROM pg_sequences WHERE schemaname='public';")=="0",
            "fifth public sequences not empty")
    require(sql("SELECT has_schema_privilege('cafe_synth_owner','public','CREATE');")=="t",
            "non-login owner schema CREATE missing")
    require(sql("SELECT has_schema_privilege('cafe_synth_app','public','CREATE');")=="f",
            "application schema DDL unexpectedly permitted")
    canonical_versions()
    require(git("cat-file","-t",RUBY_GUARD_BLOB)=="blob",
            "reviewed fifth-only Ruby guard Git blob missing")
    offline_runner_mount_probe(probe,mounts,ip)
    live_sql_connection_preflight(probe,mounts,ip,ident)
    print("P1.2 PROTECTED FOUR PG / MEDIA / HTTP 3001-3002 PASS",flush=True)
    print("P1.2 FIFTH SCRAM POSTGRES / ISOLATED NETWORK / EMPTY SCHEMA PASS",flush=True)
    print("P1.2 REVIEWED RAILS / READONLY BUNDLE / SOURCE CONTRACT PASS",flush=True)
    print("P1.2 FIFTH-ONLY ONE-SHOT PREFLIGHT PASS — NO WRITES",flush=True)
    return probe,mounts,ip,ident

def build_source(probe,stage):
    source=Path(stage)/"source"
    source.mkdir(mode=0o700)
    probe.archive_into(source)
    for folder in ("log","tmp"):
        (source/folder).mkdir(exist_ok=True,mode=0o700)
    guard=source/"qa/security/cafe_fifth_schema_target_guard.rb"
    require(not guard.exists() and not guard.is_symlink(),
            "runtime Ruby target guard overwrite blocked")
    guard.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with guard.open("xb") as output:
        output.write(call(["git","-C",str(REPO),"cat-file","blob",RUBY_GUARD_BLOB]))
    require(git("hash-object",str(guard))==RUBY_GUARD_BLOB,
            "runtime Ruby guard content differs")
    return source

def docker_writer(source,mounts,ip):
    argv=["docker","run","--rm","--pull=never","--network="+NETWORK,
          "--user=1000:1000","--workdir=/app","--read-only",
          "--memory=1024m","--pids-limit=256","--cap-drop=ALL",
          "--security-opt=no-new-privileges",
          "--tmpfs=/tmp:rw,nosuid,nodev,size=128m,uid=1000,gid=1000",
          "--tmpfs=/app/tmp:rw,nosuid,nodev,size=64m,uid=1000,gid=1000",
          "--tmpfs=/app/log:rw,nosuid,nodev,size=16m,uid=1000,gid=1000",
          "--env=HOME=/tmp","--env=RAILS_ENV=test","--env=RUBYOPT=-rlogger",
          "--env=BUNDLE_GEMFILE=/app/Gemfile","--env=BUNDLE_PATH=/bundle",
          "--env=BUNDLE_FROZEN=true","--env=PGSSLMODE=disable",
          "--env=CAFE_P12_TARGET="+DB,"--env=CAFE_P12_SERVER_IP="+ip,
          "--env=PGOPTIONS=-c role=cafe_synth_owner -c search_path=public",
          "--mount=type=bind,source={},target=/app,readonly".format(source),
          "--mount=type=bind,source={},target=/tmp/cafe_p12_secret,readonly".format(SECRET)]
    argv+=["--mount="+mount for mount in mounts]
    # Password is read at runtime INSIDE the ephemeral container from an
    # existing verified read-only file. No Docker Config.Env/argv password.
    shell=('set -eu; '
           'password="$(cat /tmp/cafe_p12_secret)"; '
           'export DATABASE_URL="postgresql://postgres:$password@cafe-synthetic-postgres:5432/cafe_synthetic"; '
           'unset password; '
           'bundle exec ruby qa/security/cafe_fifth_schema_target_guard.rb pre; '
           'bundle exec rails db:schema:load; '
           'bundle exec ruby qa/security/cafe_fifth_schema_target_guard.rb post')
    argv+=["--entrypoint=sh",IMAGE,"-c",shell]
    return argv

def offline_runner_mount_probe(probe,mounts,ip):
    """No-network disposable probe of the exact DDL runner mount hierarchy.

    Uses a fixed FAKE placeholder instead of the private PostgreSQL secret.
    There is no database address reachable and no SQL or Rails data task.
    """
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="cafe-p12-offline-mount-") as stage:
        source=build_source(probe,stage)
        sentinel=Path(stage)/"fake_noncredential_file"
        with sentinel.open("x",encoding="ascii") as out:
            out.write("not-a-secret\n")
        sentinel.chmod(0o600)
        argv=docker_writer(source,mounts,ip)
        expected_secret="--mount=type=bind,source={},target=/tmp/cafe_p12_secret,readonly".format(SECRET)
        fake_secret="--mount=type=bind,source={},target=/tmp/cafe_p12_secret,readonly".format(sentinel)
        require(argv.count(expected_secret)==1,"test secret mount contract differs")
        argv[argv.index(expected_secret)]=fake_secret
        exact_network="--network="+NETWORK
        require(argv.count(exact_network)==1,"isolated network contract differs")
        argv[argv.index(exact_network)]="--network=none"
        argv[-1]="set -eu; test -r /tmp/cafe_p12_secret; bundle exec rails -v"
        # The temporary process receives NO original database credential.
        try:
            result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                  check=False,timeout=150)
        except (OSError,subprocess.TimeoutExpired):
            raise RuntimeError("P1.2 SCHEMA STOP: isolated offline mount test unavailable")
        require(result.returncode==0 and b"Rails 6.0." in result.stdout,
                "offline Rails/secret-target/tmpfs mount compatibility failed")
    print("P1.2 ISOLATED NO-NETWORK / FAKE-SECRET / RAILS MOUNT PROBE PASS",
          flush=True)

def live_sql_connection_preflight(probe,mounts,ip,identifier):
    """Run ONLY the fixed Ruby 'pre' SELECT audit against the fifth PG.

    This is a read-only database connection test in an ephemeral Docker
    container. It creates NO schema, data, attempt marker or Docker volume.
    Password stays inside the disposable shell and is never printed.
    """
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="cafe-p12-fifth-sql-readonly-") as stage:
        source=build_source(probe,stage)
        argv=docker_writer(source,mounts,ip)
        fixed_marker="; bundle exec rails db:schema:load;"
        require(argv[-1].count(fixed_marker)==1,
                "canonical writer shell marker unexpectedly changed")
        # Exact same connection/credentials/owner role as the later writer,
        # stopping immediately after the independent target/pre-schema audit.
        argv[-1]=argv[-1].split(fixed_marker,1)[0]
        require(argv[-1].endswith(
            "bundle exec ruby qa/security/cafe_fifth_schema_target_guard.rb pre"),
            "readonly fifth SQL preflight command differs")
        need=(b"P1.2 EXACT FIFTH DB/TCP IP/OWNER/APP ROLE CHECK PASS",
              b"P1.2 FIFTH SCHEMA EMPTY PRE-WRITE PASS")
        try:
            result=subprocess.run(argv,stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,check=False,
                                  timeout=150)
        except (OSError,subprocess.TimeoutExpired):
            raise RuntimeError("P1.2 SCHEMA STOP: fifth readonly SQL probe timeout/unavailable")
        require(result.returncode==0 and all(x in result.stdout for x in need),
                "fifth-only TCP/role/SCRAM Ruby readonly SQL preflight failed")
    require(target()==(ip,identifier),
            "fifth PG target changed after read-only connection test")
    require(sql("SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';")=="0",
            "fifth schema unexpectedly populated after SQL preflight")
    print("P1.2 FIFTH-ONLY SCRAM TCP / OWNER ROLE / RUBY PRE-SCHEMA SQL PASS",
          flush=True)

def create_schema(confirmation):
    require(confirmation==DB,"explicit --confirm-target cafe_synthetic required")
    probe,mounts,ip,ident=check()
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="cafe-p12-fifth-rails-") as stage:
        source=build_source(probe,stage)
        argv=docker_writer(source,mounts,ip)
        require(target()==(ip,ident),"fifth PG changed immediately before writer")
        require(sql("SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';")=="0",
                "fifth schema became occupied before writer")
        record={"pg":PG,"database":DB,"cluster":ident,"source":SOURCE,
                "ruby_guard_blob":RUBY_GUARD_BLOB,"started":int(time.time()),
                "operation":"fifth-only schema:load after scoped roles, no seeds"}
        flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
        if hasattr(os,"O_NOFOLLOW"): flags|=os.O_NOFOLLOW
        fd=os.open(str(MARKER),flags,0o600)
        with os.fdopen(fd,"w",encoding="utf-8") as output:
            json.dump(record,output,sort_keys=True)
            output.write("\n")
        print("P1.2 ONE-SHOT FIFTH-ONLY ATTEMPT RECORDED",flush=True)
        print("P1.2 EXECUTING CANONICAL SCHEMA LOAD — NO SEEDS",flush=True)
        # Docker stdout/stderr may contain confidential DSN/stack details.
        # Never copy raw command output to the user's terminal or remote CI.
        try:
            result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                  check=False,timeout=300)
        except (OSError,subprocess.TimeoutExpired):
            raise RuntimeError("P1.2 SCHEMA STOP: one-shot Docker unavailable/timeout")
        require(result.returncode==0,
                "one-shot writer failed; preserve attempt marker and inspect DB")
        for marker in (
            b"P1.2 FIFTH SCHEMA EMPTY PRE-WRITE PASS",
            b"P1.2 EXACT MIGRATION VERSIONS / ZERO DATA / APP CRUD ACL PASS"):
            require(marker in result.stdout,"writer missing independent Rails/SQL proof")
    print("P1.2 CANONICAL SCHEMA LOADED INTO FIFTH POSTGRES PASS",flush=True)
    print("P1.2 INDEPENDENT --verify-schema REQUIRED BEFORE SEEDS",flush=True)

def protected_four():
    helper=load_pin(OLD_PG_HELPER,OLD_PG_BLOB,"p12_four_originals")
    with redirect_stdout(io.StringIO()):
        identities=helper.source_baseline()
    require(len(identities)==4 and len(set(identities))==4,
            "four protected PG identities differ")
    return set(identities)

def verify_schema():
    require(MARKER.is_file() and not MARKER.is_symlink(),
            "one-shot schema attempt was not recorded")
    record=json.loads(MARKER.read_text(encoding="utf-8"))
    require(record.get("pg")==PG and record.get("database")==DB and
            record.get("source")==SOURCE and
            record.get("operation")=="fifth-only schema:load after scoped roles, no seeds" and
            record.get("ruby_guard_blob")==RUBY_GUARD_BLOB,
            "attempt record identity differs")
    previous=protected_four()
    _ip,ident=target()
    require(ident==record["cluster"] and ident not in previous,
            "fifth PG cluster changed / overlaps protected cluster")
    roles=load_pin(ROLES_HELPER,ROLES_BLOB,"p12_roles_post_schema")
    require(roles.MARKER.is_file() and not roles.MARKER.is_symlink(),
            "scoped role recovery marker missing after schema load")
    role_record=json.loads(roles.MARKER.read_text(encoding="utf-8"))
    require(role_record.get("fifth_cluster")==ident and
            role_record.get("operation")=="restore_fifth_scoped_roles_once" and
            role_record.get("sql_blob")==roles.SQL_BLOB,
            "scoped role recovery marker differs after schema load")
    require(sql("SELECT count(*) FROM pg_roles WHERE rolname='cafe_synth_owner' AND NOT rolcanlogin AND NOT rolsuper;")=="1",
            "scoped schema owner role changed")
    require(sql("SELECT count(*) FROM pg_roles WHERE rolname='cafe_synth_app' AND rolcanlogin AND NOT rolsuper;")=="1",
            "scoped application role changed")
    tables=sql("SELECT string_agg(tablename,',' ORDER BY tablename) "
               "FROM pg_tables WHERE schemaname='public';")
    require(tables==",".join(TABLES),"fifth expected table list differs")
    require(sql("SELECT COUNT(*) FROM pg_constraint c JOIN pg_namespace n "
                "ON n.oid=c.connamespace WHERE n.nspname='public' AND c.contype='f';")=="8",
            "fifth FK count differs")
    require(sql("SELECT COUNT(*) FROM pg_tables WHERE schemaname='public' "
                "AND tableowner='cafe_synth_owner';")=="10",
            "fifth owner table count differs")
    require(sql("SELECT COUNT(*) FROM pg_sequences WHERE schemaname='public' "
                "AND sequenceowner='cafe_synth_owner';")=="8",
            "fifth owner sequence count differs")
    require(sql("SELECT string_agg(version,',' ORDER BY version) "
                "FROM public.schema_migrations;")==",".join(canonical_versions()),
            "fifth Rails migration versions differ")
    for table in DATA_TABLES:
        require(sql("SELECT COUNT(*) FROM public."+table+";")=="0",
                "fifth table unexpectedly contains data: "+table)
        for action in ("SELECT","INSERT","UPDATE","DELETE"):
            require(sql("SELECT has_table_privilege('cafe_synth_app',"
                        "'public."+table+"','"+action+"');")=="t",
                    "fifth app table CRUD privilege differs")
    require(sql("SELECT has_schema_privilege('cafe_synth_app','public','CREATE');")=="f",
            "fifth app role gained DDL")
    require(protected_four()==previous,"protected four PG changed")
    print("P1.2 FOUR PROTECTED PG/MEDIA/WEB AND FIFTH PG ISOLATION PASS",flush=True)
    print("P1.2 FIFTH TEN TABLES / EIGHT FK / OWNER / APP ACL PASS",flush=True)
    print("P1.2 FIFTH MIGRATION SET / ALL APP TABLES EMPTY PASS",flush=True)
    print("P1.2 INDEPENDENT SCHEMA VERIFY PASS — NO SEEDS",flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check",action="store_true")
    mode.add_argument("--create-schema",action="store_true")
    mode.add_argument("--verify-schema",action="store_true")
    parser.add_argument("--confirm-target")
    args=parser.parse_args()
    try:
        if args.check:
            require(args.confirm_target is None,"check does not accept write acknowledgement")
            check()
        elif args.create_schema:
            create_schema(args.confirm_target)
        else:
            require(args.confirm_target is None,"verify cannot accept write acknowledgement")
            verify_schema()
    except Exception as exc:
        reason=str(exc)
        if not reason.startswith("P1.2 SCHEMA STOP:"):
            reason="P1.2 SCHEMA STOP: internal safety/compatibility audit failure"
        print(reason,file=sys.stderr)
        print("Never retry failed write, reset a DB or modify protected services.",
              file=sys.stderr)
        sys.exit(1)

if __name__=="__main__":
    main()
