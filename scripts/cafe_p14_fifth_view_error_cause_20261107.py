#!/usr/bin/env python3
"""P1.4 read-only fifth-only GET / ActionView nested-cause diagnosis.

--classify-view ONLY. Imports the original, SHA-pinned P1.4 diagnostic
without altering either existing owner script. Uses exactly the fifth
SCRAM app role, internal Docker network, SQL default_transaction_read_only=on
and disposable no-host-port runner. The only database operations are read-only
fixture and identity SELECTs and GET requests. Emits ONLY fixed categories.
Never outputs logs, messages, SQL, URLs, credentials, internal IPs or stacks.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HOME=Path.home()
REPO=HOME/"Рабочий стол/rails_projects/lite/cafe_app"
PRIVATE=HOME/".local/share/cafe_app"
OLD_DIAG=PRIVATE/"cafe_p14_fifth_http_fault_diagnostic_20261107.py"
OLD_DIAG_BLOB="1aee748857e42a13df316858f763aaeadaf02328"
VIEW_RUBY=PRIVATE/"cafe_p14_fifth_view_error_cause_20261107.rb"
VIEW_RUBY_BLOB="7609ff9cef7e5fe2b116b2cde769f91498d15262"
OLD_RUBY_BLOB="e7738e20f8d8656a685d0084f31f19a5e04bed64"
DB="cafe_synthetic"
NETWORK="cafe-upload-security-synthetic-net-20261105"

CAUSES=set("""WEBPACKER_MANIFEST_ENTRY WEBPACKER_COMPILE
SPROCKETS_ASSET_NOT_FOUND SASS_COMPILATION FILESYSTEM_READONLY
FILESYSTEM_PERMISSION MISSING_TEMPLATE NAME_ERROR NO_METHOD
WEBPACKER_MANIFEST_OR_COMPILE WEBPACKER_DEPENDENCY OTHER_VIEW_ERROR""".split())
STATES={"PRESENT","MISSING"}

def require(ok,reason):
    if not ok:
        raise RuntimeError("P1.4 VIEW DIAG STOP: "+reason)

def trusted_file(path,blob):
    require(path.is_file() and not path.is_symlink(),"private immutable helper missing")
    st=path.stat()
    require(st.st_uid==os.getuid() and st.st_mode&0o077==0,
            "private helper permissions differ")
    p=subprocess.run(["git","-C",str(REPO),"hash-object",str(path)],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=20)
    require(p.returncode==0 and p.stdout.decode("ascii").strip()==blob,
            "immutable Git blob check failed")

def load_previous():
    require(os.getuid()==1000 and REPO.is_dir() and
            (REPO/".git").is_dir(),"unrecognized owner/repository")
    trusted_file(OLD_DIAG,OLD_DIAG_BLOB)
    trusted_file(VIEW_RUBY,VIEW_RUBY_BLOB)
    spec=importlib.util.spec_from_file_location("p14_fifth_original_diag",OLD_DIAG)
    require(spec is not None and spec.loader is not None,
            "previous reviewed diagnosis import unavailable")
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    require(m.DB==DB and m.NETWORK==NETWORK and
            m.DIAG_RUBY_BLOB==OLD_RUBY_BLOB,
            "previous P1.4 source/fifth target differs")
    return m

def classify(raw):
    # Never echo or print arbitrary application logs or error messages.
    lines=raw.decode("utf-8",errors="replace")[:60000].splitlines()
    kinds={
      "ROOT_CAUSE":CAUSES,
      "PACK_MANIFEST":STATES,
      "PUBLIC_PACKS":STATES,
      "NODE_MODULES":STATES,
    }
    values={}
    for key,choices in kinds.items():
        prefix="P1.4 VIEW DIAG "+key+"="
        matches=[line[len(prefix):] for line in lines
                 if line.startswith(prefix) and line[len(prefix):] in choices]
        values[key]=matches[0] if len(matches)==1 else "UNAVAILABLE"
    return values

def run():
    old=load_previous()
    p14=old.module()
    p13=p14.pinned_module()
    p13.verify()  # real owner fifth+four protected PG before GET, SELECT only
    schema=p13.load_schema()
    ip,cluster=schema.target()
    require(cluster not in schema.protected_four(),"fifth target overlaps original four")
    app_file=p14.app_secret(schema,cluster)
    runtime,mounts=schema.runtime()
    print("P1.4 VIEW DIAG FIFTH/APP SECRET / ORIGINAL FOUR PG CHECK PASS",flush=True)
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="cafe-p14-view-fault-readonly-") as stage:
        source=schema.build_source(runtime,stage)
        for file,sha in ((old.ORIG_RUBY,old.ORIG_RUBY_BLOB),
                         (old.DIAG_RUBY,old.DIAG_RUBY_BLOB),
                         (VIEW_RUBY,VIEW_RUBY_BLOB)):
            target=source/"qa/security"/file.name
            require(not target.exists() and not target.is_symlink(),
                    "staged original source path collision")
            with target.open("xb") as f:
                f.write(file.read_bytes())
            require(schema.git("hash-object",str(target))==sha,
                    "staged Ruby source checksum differs")
        argv=old.command(p14,schema,source,mounts,ip,cluster,app_file)
        original="bundle exec rails runner qa/security/cafe_p14_fifth_http_fault_diagnostic_20261107.rb"
        replacement="bundle exec rails runner qa/security/cafe_p14_fifth_view_error_cause_20261107.rb"
        require(argv[-1].endswith(original) and argv[-1].count(original)==1,
                "previous reviewed read-only runner differs")
        argv[-1]=argv[-1].replace(original,replacement)
        for flag in ("--rm","--pull=never","--read-only",
                     "--cap-drop=ALL","--security-opt=no-new-privileges",
                     "--network="+NETWORK,"--user=1000:1000",
                     "--env=RAILS_ENV=test",
                     "--env=PGOPTIONS=-c default_transaction_read_only=on -c search_path=public",
                     "--env=CAFE_P12_EXPECTED_CLUSTER_ID="+cluster):
            require(flag in argv,"read-only fifth Docker contract changed")
        require(not any(word in argv[-1] for word in (
            "db:schema:load","db:seed","db:migrate",
            "db:prepare","db:drop","db:reset","rails test")),
            "unreviewed writing operation in the test runner")
        require(schema.target()==(ip,cluster),"fifth cluster changed before GET")
        try:
            process=subprocess.run(argv,stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,check=False,timeout=150)
        except (OSError,subprocess.TimeoutExpired):
            raise RuntimeError("P1.4 VIEW DIAG STOP: no-write runner unavailable/timeout")
        result=old.output_classification(
            process.stdout,process.returncode,process.stderr)
        asset=classify(process.stdout)
    require(schema.target()==(ip,cluster),"fifth cluster changed after GET")
    p13.verify() # Always verify catalogue, ACL, fifth and protected 4 after GET
    state,stage,kind,status=result
    require(state in ("PASSED","BLOCKED") and
            stage in old.STAGES and kind in old.ERROR_KINDS,
            "unrecognized outcome from prior reviewed fault classifier")
    print("P1.4 VIEW DIAG STAGE="+stage,flush=True)
    print("P1.4 VIEW DIAG KIND="+kind,flush=True)
    if status is not None and status in old.STATUS:
        print("P1.4 VIEW DIAG HTTP_STATUS="+status,flush=True)
    for key in ("ROOT_CAUSE","PACK_MANIFEST","PUBLIC_PACKS","NODE_MODULES"):
        print("P1.4 VIEW DIAG "+key+"="+asset[key],flush=True)
    print("P1.4 VIEW DIAG RESULT="+state+"; NO INTENDED DB WRITES",flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classify-view",action="store_true",required=True)
    args=parser.parse_args()
    try:
        if args.classify_view:
            run()
    except Exception as exc:
        msg=str(exc)
        if not msg.startswith("P1.4 VIEW DIAG STOP:"):
            msg="P1.4 VIEW DIAG STOP: internal immutable-source/isolated-runner check failed"
        print(msg,file=sys.stderr,flush=True)
        print("Preserve fifth tmpfs PG, P1.2/P1.3 one-shot markers and four originals.",
              file=sys.stderr,flush=True)
        raise SystemExit(1)

if __name__=="__main__":
    main()
