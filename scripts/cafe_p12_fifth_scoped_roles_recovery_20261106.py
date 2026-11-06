#!/usr/bin/env python3
"""P1.2 fifth-only synthetic PostgreSQL scoped roles after tmpfs reboot.

--check: READ ONLY. Source/credential/cluster/empty-schema/preexisting marker.
--provision: separate ONE-SHOT owner-only action; create exclusive private
  attempt marker BEFORE SQL; atomic transaction targets ONLY fifth PG.
--verify: READ ONLY: independent role, ACL, SCRAM login, isolation checks.
No production/QA SQL writes, Docker creates, restarts, Rails schema/seed,
snapshot imports, checkout, secret printing or role credentials on argv.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time

HOME=Path.home()
BASE=HOME/".local/share/cafe_app"
REPO=HOME/"Рабочий стол/rails_projects/lite/cafe_app"
BOOT=BASE/"cafe_p12_fifth_scram_reboot_v1_20261106.py"
BOOT_BLOB="b9bd1df811d61e0e177e4c2f16f4d680248bb206"
SQL_BLOB="6c033b139ec9921c00c39e691010a44b55bf49bf"
CI_PASSWORD="CIOnlySyntheticRolePass_20261105"
STAGE=BASE/"cafe_p12_fifth_scoped_roles_20261106"
APP_SECRET=STAGE/"app_password"
MARKER=BASE/"cafe_p12_fifth_scoped_roles_attempt_20261106.json"
PG="cafe-upload-security-synthetic-pg-20261105"
DB="cafe_synthetic"
NETWORK="cafe-upload-security-synthetic-net-20261105"
OWNER="cafe_synth_owner"
APP="cafe_synth_app"
SQL_ARGS=("docker","exec","-i","--user","postgres",PG,
          "psql","-X","-v","ON_ERROR_STOP=1","-U","postgres","-d",DB,"-f","-")

def require(ok,reason):
    if not ok:raise RuntimeError("P1.2 FIFTH ROLES STOP: "+reason)

def call(args,stdin=None,timeout=35):
    try:
        return subprocess.run(list(args),input=stdin,stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,timeout=timeout,check=False)
    except (OSError,subprocess.TimeoutExpired):
        raise RuntimeError("P1.2 FIFTH ROLES STOP: controlled command unavailable/timeout")

def load_boot():
    require(os.getuid()==1000 and REPO.is_dir() and (REPO/".git").exists(),
            "wrong owner or local source repository")
    require(BOOT.is_file() and not BOOT.is_symlink(),"pinned SCRAM restart helper missing")
    st=BOOT.stat()
    require(st.st_uid==os.getuid() and st.st_mode&0o022==0,
            "SCRAM restart helper owner or permissions changed")
    r=call(("git","-C",str(REPO),"hash-object",str(BOOT)),timeout=18)
    require(r.returncode==0 and r.stdout.decode().strip()==BOOT_BLOB,
            "SCRAM restart helper Git blob differs")
    spec=importlib.util.spec_from_file_location("cafe_fifth_reviewed_reboot",BOOT)
    require(spec is not None and spec.loader is not None,
            "SCRAM restart helper loader failed")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    require(mod.PG==PG and mod.NETWORK==NETWORK and mod.DB==DB,
            "reviewed fifth target differs")
    return mod

def sql(query):
    require(query.lstrip().upper().startswith(("SELECT ","SHOW ")),
            "non-read-only SQL inspection rejected")
    cmd=("docker","exec","--user","postgres",PG,"psql","-X","-At",
         "-v","ON_ERROR_STOP=1","-U","postgres","-d",DB,"-c",query)
    p=call(cmd,timeout=25)
    require(p.returncode==0 and len(p.stdout)<500,
            "fifth-only read-only SQL audit failed")
    return p.stdout.decode(errors="replace").strip()

def eq(query,want,reason):
    require(sql(query)==want,reason)

def reviewed_sql():
    p=call(("git","-C",str(REPO),"cat-file","blob",SQL_BLOB),timeout=20)
    require(p.returncode==0 and len(p.stdout)<6000,
            "reviewed synthetic-only CI role SQL blob missing")
    value=p.stdout
    check=b"blob "+str(len(value)).encode()+b"\x00"+value
    require(hashlib.sha1(check).hexdigest()==SQL_BLOB,
            "synthetic SQL Git blob content not pinned")
    source=value.decode("ascii")
    require(source.count(CI_PASSWORD)==1 and
            source.count("CREATE ROLE cafe_synth_owner")==1 and
            source.count("CREATE ROLE cafe_synth_app")==1 and
            source.count("REVOKE ALL ON DATABASE cafe_synthetic FROM PUBLIC;")==1 and
            source.count("GRANT CONNECT ON DATABASE cafe_synthetic TO cafe_synth_app;")==1 and
            source.count("ALTER DEFAULT PRIVILEGES FOR ROLE cafe_synth_owner")==2 and
            source.count("BEGIN;")==1 and source.count("COMMIT;")==1,
            "reviewed scoped role DDL contract differs")
    return source

def old_marker(boot):
    obj=boot.MARKER
    require(obj.is_file() and not obj.is_symlink(),"fifth SCRAM boot marker missing")
    st=obj.stat()
    require(st.st_uid==os.getuid() and st.st_mode&0o077==0 and st.st_size<2048,
            "fifth SCRAM marker permissions/size differ")
    info=json.loads(obj.read_text(encoding="utf-8"))
    require(info.get("operation")=="reboot_existing_fifth_empty_scram_once" and
            info.get("pg")==PG and info.get("network")==NETWORK and
            info.get("source_blob")==boot.OLD_BLOB,
            "fifth SCRAM marker identity changed")
    require(not boot.SCHEMA_MARKER.exists() and
            not boot.SCHEMA_MARKER.is_symlink(),
            "historical fifth schema attempt marker exists")

def original():
    boot=load_boot()
    old_marker(boot)
    old=boot.owner_module(boot.OLD,boot.OLD_BLOB,"cafe_reviewed_fifth_original")
    old.secret_audit()
    baseline=old.source_baseline() # original four PG + fourth readonly Rails
    old.check_new("running")       # exact fifth PG image/tmpfs/net/secret
    ident=sql("SELECT system_identifier::text FROM pg_control_system();")
    require(ident.isdigit() and len(set(baseline+[ident]))==5,
            "fifth cluster is not distinct from protected original four")
    eq("SHOW password_encryption;","scram-sha-256","fifth SCRAM encryption changed")
    eq("SELECT COUNT(*) FROM pg_hba_file_rules WHERE type IN ('host','hostssl','hostnossl') AND auth_method <> 'scram-sha-256';",
       "0","fifth host auth no longer SCRAM-only")
    eq("SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';",
       "0","fifth unexpectedly contains application tables")
    eq("SELECT COUNT(*) FROM pg_sequences WHERE schemaname='public';",
       "0","fifth unexpectedly contains application sequences")
    reviewed_sql()
    return ident

def before():
    require(not MARKER.exists() and not MARKER.is_symlink(),
            "new role recovery attempt already exists; never repeat")
    require(not STAGE.exists() and not STAGE.is_symlink(),
            "new private role credentials stage already exists")
    ident=original()
    eq("SELECT COUNT(*) FROM pg_roles WHERE rolname IN ('cafe_synth_owner','cafe_synth_app');",
       "0","fifth synthetic roles already exist")
    eq("SELECT COUNT(*) FROM pg_roles WHERE rolcanlogin AND rolname <> 'postgres';",
       "0","fifth has unexpected login role")
    eq("SELECT COUNT(*) FROM pg_default_acl;",
       "0","fifth custom default ACL already exists")
    print("P1.2 ORIGINAL FOUR PG / MEDIA / FIFTH DISTINCT SCRAM PASS",flush=True)
    print("P1.2 FIFTH EMPTY SCHEMA / ZERO SCOPED ROLES / NO PRIOR ATTEMPT PASS",flush=True)
    print("P1.2 PINNED LEAST-PRIVILEGE ROLE DDL / SECRET TARGET AVAILABLE PASS",flush=True)
    print("P1.2 FIFTH ROLE RECOVERY CHECK PASS — NO WRITES",flush=True)
    return ident

def secret_audit():
    require(STAGE.is_dir() and not STAGE.is_symlink() and
            APP_SECRET.is_file() and not APP_SECRET.is_symlink(),
            "new role credential is missing")
    d,f=STAGE.stat(),APP_SECRET.stat()
    require(d.st_uid==os.getuid() and f.st_uid==os.getuid() and
            d.st_mode&0o077==0 and f.st_mode&0o077==0,
            "private role credential permissions changed")
    password=APP_SECRET.read_bytes()
    require(re.fullmatch(rb"[A-Za-z0-9_-]{48,128}",password) is not None,
            "private role password format changed")
    return password

def login_test(password):
    # Credential goes ONLY over Docker exec stdin to the fifth PostgreSQL.
    # Docker Config.Env, shell argv, stdout and GitHub contain no password.
    script=('IFS= read -r PGPASSWORD; export PGPASSWORD; '
            'exec psql -XAt -v ON_ERROR_STOP=1 -h 127.0.0.1 '
            '-U cafe_synth_app -d cafe_synthetic -c "SELECT current_user;"')
    p=call(("docker","exec","-i","--user","postgres",PG,
            "sh","-c",script),stdin=password+b"\n",timeout=18)
    return p.returncode==0 and p.stdout.strip()==APP.encode()

def verify():
    require(MARKER.is_file() and not MARKER.is_symlink(),
            "role recovery attempt marker missing")
    st=MARKER.stat()
    require(st.st_uid==os.getuid() and st.st_mode&0o077==0 and st.st_size<2048,
            "role attempt marker ownership/mode differs")
    info=json.loads(MARKER.read_text(encoding="utf-8"))
    require(info.get("operation")=="restore_fifth_scoped_roles_once" and
            info.get("pg")==PG and info.get("database")==DB and
            info.get("sql_blob")==SQL_BLOB,
            "role attempt marker targets changed")
    password=secret_audit()
    require(hashlib.sha256(password).hexdigest()==info.get("app_secret_sha256"),
            "role password hash mismatch")
    ident=original()
    require(info.get("fifth_cluster")==ident,
            "role recovery marker belongs to another fifth PostgreSQL cluster")
    eq("SELECT COUNT(*) FROM pg_roles WHERE rolname='cafe_synth_owner' AND NOT rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolinherit AND NOT rolreplication AND NOT rolbypassrls;",
       "1","scoped owner role attributes incorrect")
    eq("SELECT COUNT(*) FROM pg_roles WHERE rolname='cafe_synth_app' AND rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolinherit AND NOT rolreplication AND NOT rolbypassrls;",
       "1","scoped application role attributes incorrect")
    eq("SELECT COUNT(*) FROM pg_roles WHERE rolcanlogin AND rolname <> 'postgres';",
       "1","fifth contains unexpected login roles")
    eq("SELECT COUNT(*) FROM pg_roles WHERE rolname NOT LIKE 'pg_%' AND rolname NOT IN ('postgres','cafe_synth_owner','cafe_synth_app');",
       "0","fifth contains unreviewed custom roles")
    eq("SELECT COUNT(*) FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname='cafe_synth_app');",
       "0","app inherited unapproved role membership")
    eq("SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='public';",
       OWNER,"fifth public schema wrong owner")
    for query,value,label in (
       ("SELECT has_database_privilege('cafe_synth_app','cafe_synthetic','CONNECT');","t","app CONNECT"),
       ("SELECT has_database_privilege('cafe_synth_app','cafe_synthetic','CREATE');","f","app database CREATE"),
       ("SELECT has_database_privilege('cafe_synth_app','cafe_synthetic','TEMPORARY');","f","app TEMP"),
       ("SELECT has_schema_privilege('cafe_synth_app','public','USAGE');","t","app USAGE"),
       ("SELECT has_schema_privilege('cafe_synth_app','public','CREATE');","f","app schema CREATE"),
       ("SELECT has_database_privilege('cafe_synth_app','postgres','CONNECT');","f","other postgres DB"),
       ("SELECT has_database_privilege('cafe_synth_app','template1','CONNECT');","f","other template1 DB"),
       ("SELECT has_schema_privilege('cafe_synth_owner','public','CREATE');","t","owner CREATE"),
    ):eq(query,value,"scoped ACL incorrect: "+label)
    eq("SELECT count(DISTINCT a.privilege_type) FROM pg_default_acl d CROSS JOIN LATERAL aclexplode(d.defaclacl) a WHERE d.defaclrole=(SELECT oid FROM pg_roles WHERE rolname='cafe_synth_owner') AND d.defaclnamespace='public'::regnamespace AND d.defaclobjtype='r' AND a.grantee=(SELECT oid FROM pg_roles WHERE rolname='cafe_synth_app') AND a.privilege_type IN ('SELECT','INSERT','UPDATE','DELETE');",
       "4","default table ACL incomplete")
    eq("SELECT count(DISTINCT a.privilege_type) FROM pg_default_acl d CROSS JOIN LATERAL aclexplode(d.defaclacl) a WHERE d.defaclrole=(SELECT oid FROM pg_roles WHERE rolname='cafe_synth_owner') AND d.defaclnamespace='public'::regnamespace AND d.defaclobjtype='S' AND a.grantee=(SELECT oid FROM pg_roles WHERE rolname='cafe_synth_app') AND a.privilege_type IN ('USAGE','SELECT');",
       "2","default sequence ACL incomplete")
    eq("SELECT COUNT(*) FROM pg_authid WHERE rolname='cafe_synth_app' AND rolpassword LIKE 'SCRAM-SHA-256$%';",
       "1","app role password is not SCRAM verifier")
    require(login_test(password),"real app SCRAM login failed")
    require(not login_test(b"DefinitelyInvalidSyntheticRolePassword_20261106"),
            "incorrect app password unexpectedly accepted")
    print("P1.2 FIFTH SCOPED OWNER NOLOGIN / APP LOGIN ACL PASS",flush=True)
    print("P1.2 FIFTH DEFAULT CRUD/SEQUENCE PRIVILEGES / APP DDL DENIED PASS",flush=True)
    print("P1.2 FIFTH CORRECT/INCORRECT SCRAM APP PASSWORD PASS",flush=True)
    print("P1.2 FIFTH ZERO DATA TABLES / FIVE DISTINCT PG / ORIGINAL WEB PASS",flush=True)
    print("P1.2 FIFTH SCOPED ROLES INDEPENDENT VERIFY PASS",flush=True)

def provision():
    ident=before()
    os.umask(0o077)
    STAGE.mkdir(mode=0o700)
    new_password=secrets.token_urlsafe(48)
    with APP_SECRET.open("xb") as f:f.write(new_password.encode("ascii"))
    APP_SECRET.chmod(0o600)
    secret_audit()
    flags=os.O_CREAT|os.O_EXCL|os.O_WRONLY
    if hasattr(os,"O_NOFOLLOW"):flags|=os.O_NOFOLLOW
    fd=os.open(str(MARKER),flags,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as out:
        json.dump({"operation":"restore_fifth_scoped_roles_once",
                   "pg":PG,"database":DB,"fifth_cluster":ident,
                   "sql_blob":SQL_BLOB,
                   "app_secret_sha256":hashlib.sha256(new_password.encode()).hexdigest(),
                   "unix":int(time.time())},out,sort_keys=True)
        out.write("\n")
    print("P1.2 FIFTH SCOPED ROLES ONE-SHOT MARKER RECORDED",flush=True)
    sql_script=reviewed_sql().replace(CI_PASSWORD,new_password)
    require(sql_script.count(new_password)==1 and len(sql_script)<6000,
            "private role password substitution invalid")
    p=call(SQL_ARGS,stdin=sql_script.encode("ascii"),timeout=40)
    require(p.returncode==0,
            "fifth-only role SQL failed; preserve marker, never retry")
    print("P1.2 FIFTH-ONLY ATOMIC ROLE SQL APPLIED",flush=True)
    verify()
    print("P1.2 FIFTH SCOPED ROLES RECOVERY COMPLETE — NO SCHEMA/SEED WRITES",flush=True)

def main():
    arg=argparse.ArgumentParser(description=__doc__)
    modes=arg.add_mutually_exclusive_group(required=True)
    for option in ("check","provision","verify"):
        modes.add_argument("--"+option,action="store_true")
    x=arg.parse_args()
    try:
        if x.check:before()
        elif x.provision:provision()
        else:verify()
    except Exception as error:
        msg=str(error)
        if not msg.startswith("P1.2 FIFTH ROLES STOP:"):
            msg="P1.2 FIFTH ROLES STOP: internal safety/compatibility audit failure"
        print(msg,file=sys.stderr,flush=True)
        print("Preserve role stage, markers, fifth container, and protected source; "
              "never blindly retry.",file=sys.stderr,flush=True)
        sys.exit(1)

if __name__=="__main__":main()
