#!/usr/bin/env python3
"""P1.4 fifth-only GET server-rendered HTML with disposable Webpacker *stub* assets.

--check-html ONLY. The previously proven VIEW_ERROR was MissingEntryError:
canonical reviewed source has neither public/packs-test manifest nor node_modules.
The test-only temporary clone, NOT the owner's working tree, receives a small
sentinel JS pack/manifest and *only* a test compile:false config overlay.
This is a BACKEND HTML/ACL smoke test, NOT real JS/CSS/frontend acceptance.

Reuses exact SHA-pinned original P1.4 app SCRAM/PGOPTIONS read-only Docker
runtime and root-cause diagnostic. Before AND after: independent P1.3 catalog,
scoped ACL, four original PG/media/web; no writable HTTP, DB mutations, services,
checkout, retries of P1.2/P1.3 one-shot operations or exposed host ports.
"""
from __future__ import annotations

import argparse
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
VIEW_PY=PRIVATE/"cafe_p14_fifth_view_error_cause_20261107.py"
VIEW_PY_BLOB="d0c3544f8eacc7c4940bc5c2d1fdcd0a7621b349"
WEBPACKER_YML_BLOB="83615b0f9ac0ca5508548621150789c7dad71071"
SOURCE="090b9d37419fcd9f393d8b686ac0f4563ef7b613"
NET="cafe-upload-security-synthetic-net-20261105"
DB="cafe_synthetic"

STUB_NAME="application-p14-placeholder-get-only.js"
JS_STUB=b"/* P1.4 disposable, NON-FUNCTIONAL frontend pack for Rails SSR/GET only. */\n"
EXPECTED_MANIFEST={"application.js": "/packs-test/js/"+STUB_NAME}
YML_BEFORE=("test:\n  <<: *default\n  compile: true\n\n"
            "  # Compile test packs to a separate directory\n"
            "  public_output_path: packs-test")
YML_AFTER=YML_BEFORE.replace("compile: true","compile: false")
EXPECTED_MARKERS=[
    b"P1.4 GET DIAG RUBY_ENTRY PASS",
    b"P1.4 GET DIAG APP ROLE / POSTGRES READ-ONLY / CATALOG PASS",
    b"P1.4 GET DIAG ALL HTTP ROUTES / COUNT ASSERTIONS PASS",
]
def require(ok,reason):
    if not ok:
        raise RuntimeError("P1.4 HTML STUB STOP: "+reason)

def git_sha(schema,path):
    return schema.git("hash-object",str(path))

def import_view_module():
    require(os.getuid()==1000 and REPO.is_dir() and
            (REPO/".git").is_dir(),"unexpected owner/repository")
    require(VIEW_PY.is_file() and not VIEW_PY.is_symlink() and
            VIEW_PY.stat().st_uid==os.getuid() and
            VIEW_PY.stat().st_mode&0o077==0,
            "previous owner-private view diagnostic missing/unsafe")
    observed=subprocess.run(["git","-C",str(REPO),"hash-object",str(VIEW_PY)],
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                            check=False,timeout=20)
    require(observed.returncode==0 and
            observed.stdout.decode("ascii").strip()==VIEW_PY_BLOB,
            "previous view diagnostic source SHA differs")
    spec=importlib.util.spec_from_file_location("p14_previous_view",VIEW_PY)
    require(spec is not None and spec.loader is not None,
            "previous view diagnostic cannot be loaded")
    view=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(view)
    require(view.DB==DB and view.NETWORK==NET and
            view.VIEW_RUBY_BLOB=="7609ff9cef7e5fe2b116b2cde769f91498d15262",
            "reviewed view probe or fifth target differs")
    return view

def install_stub(schema,source):
    require(schema.SOURCE==SOURCE and schema.DB==DB,
            "canonical source/DB differs")
    config=source/"config/webpacker.yml"
    require(config.is_file() and not config.is_symlink(),
            "temporary source lacks Webpacker config")
    require(git_sha(schema,config)==WEBPACKER_YML_BLOB,
            "canonical Webpacker config is not reviewed blob")
    original=config.read_text(encoding="utf-8")
    require(original.count(YML_BEFORE)==1 and
            "extract_css: false" in original and
            "public_output_path: packs-test" in original,
            "reviewed Webpacker v4.3 test section differs")
    require(not (source/"node_modules").exists(),
            "unexpected node_modules in reviewed source")
    output=source/"public/packs-test"
    require(not output.exists() and not output.is_symlink(),
            "source already has a real manifest or public test packs")
    js=output/"js"
    js.mkdir(parents=True,mode=0o700)
    stub=js/STUB_NAME
    manifest=output/"manifest.json"
    with stub.open("xb") as stream:
        stream.write(JS_STUB)
    with manifest.open("x",encoding="utf-8") as stream:
        json.dump(EXPECTED_MANIFEST,stream,sort_keys=True)
        stream.write("\n")
    # Restrict all modifications to a disposable copy, and only the Rails
    # test Webpacker compile setting. Real app/source remains untouched.
    config.write_text(original.replace(YML_BEFORE,YML_AFTER),encoding="utf-8")
    require(config.read_text(encoding="utf-8")==original.replace(YML_BEFORE,YML_AFTER),
            "Webpacker temporary test overlay differs")
    require(json.loads(manifest.read_text(encoding="utf-8"))==EXPECTED_MANIFEST and
            stub.read_bytes()==JS_STUB and
            len(tuple(output.rglob("*")))==3,
            "test-only stub manifest/js invalid or extra files")
    # The original immutable config blob is locally accessible but not changed.
    require(schema.git("rev-parse",SOURCE+":config/webpacker.yml")==WEBPACKER_YML_BLOB,
            "original Webpacker Git blob changed")
    print("P1.4 TEMP-ONLY WEBPACKER COMPILE=FALSE / STUB MANIFEST PASS",flush=True)

def make_command(view,old,p14,schema,source,mounts,ip,cluster,secret):
    argv=old.command(p14,schema,source,mounts,ip,cluster,secret)
    original="bundle exec rails runner qa/security/cafe_p14_fifth_http_fault_diagnostic_20261107.rb"
    replacement="bundle exec rails runner qa/security/cafe_p14_fifth_view_error_cause_20261107.rb"
    require(argv[-1].endswith(original) and argv[-1].count(original)==1,
            "reviewed read-only Rack command changed")
    argv[-1]=argv[-1].replace(original,replacement)
    for required in ("--rm","--read-only","--cap-drop=ALL",
                    "--security-opt=no-new-privileges",
                    "--network="+NET,"--user=1000:1000",
                    "--env=RAILS_ENV=test",
                    "--env=PGOPTIONS=-c default_transaction_read_only=on -c search_path=public",
                    "--env=CAFE_P12_EXPECTED_CLUSTER_ID="+cluster):
        require(required in argv,"fifth-only read-only command gate changed")
    require(not any(t in argv[-1] for t in (
            "db:seed","db:schema:load","db:migrate","db:drop",
            "db:prepare","db:reset","rails test")),
            "unsafe Rails command detected")
    return argv

def run():
    view=import_view_module()
    old=view.load_previous()
    p14=old.module()
    p13=p14.pinned_module()
    p13.verify()
    schema=p13.load_schema()
    ip,cluster=schema.target()
    require(cluster not in schema.protected_four(),
            "fifth ID overlaps original PostgreSQL")
    secret=p14.app_secret(schema,cluster)
    runtime,mounts=schema.runtime()
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="cafe-p14-html-stub-only-") as stage:
        source=schema.build_source(runtime,stage)
        install_stub(schema,source)
        # The original helper is imported privately; all its Ruby GET probes
        # are revalidated by their frozen Git blob checksum.
        ruby_sources=((old.ORIG_RUBY,old.ORIG_RUBY_BLOB),
                      (old.DIAG_RUBY,old.DIAG_RUBY_BLOB),
                      (view.VIEW_RUBY,view.VIEW_RUBY_BLOB))
        for file,sha in ruby_sources:
            dest=source/"qa/security"/file.name
            require(not dest.exists() and not dest.is_symlink(),
                    "temporary Rails source already has a diagnostic file")
            with dest.open("xb") as stream:
                stream.write(file.read_bytes())
            require(git_sha(schema,dest)==sha,
                    "staged Ruby GET probe SHA changed")
        argv=make_command(view,old,p14,schema,source,mounts,ip,cluster,secret)
        require(schema.target()==(ip,cluster),
                "fifth cluster changed before GET")
        print("P1.4 READONLY SCRAM APP / FIFTH CLUSTER / FOUR PG PASS",flush=True)
        try:
            done=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                check=False,timeout=180)
        except (OSError,subprocess.TimeoutExpired):
            raise RuntimeError("P1.4 HTML STUB STOP: isolated runner unavailable/timeout")
        result=old.output_classification(done.stdout,done.returncode,done.stderr)
        asset=view.classify(done.stdout)
        marker_ok=all(marker in done.stdout for marker in EXPECTED_MARKERS)
    require(schema.target()==(ip,cluster),"fifth cluster changed after GET")
    p13.verify()
    state,stage,kind,http_status=result
    print("P1.4 HTML STUB GET STAGE="+stage,flush=True)
    print("P1.4 HTML STUB GET KIND="+kind,flush=True)
    if http_status is not None and http_status in old.STATUS:
        print("P1.4 HTML STUB GET HTTP_STATUS="+http_status,flush=True)
    if state=="PASSED" and marker_ok:
        print("P1.4 SERVER-RENDERED HTML ROUTES/ACL PASS — STUB FRONTEND ASSETS",flush=True)
        print("P1.4 REAL WEBPACK JS/CSS / BROWSER INTERACTION NOT TESTED",flush=True)
    else:
        print("P1.4 HTML STUB VIEW ROOT_CAUSE="+asset["ROOT_CAUSE"],flush=True)
        print("P1.4 HTML STUB GET RESULT=BLOCKED; NO INTENDED DB WRITES",flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-html",action="store_true",required=True)
    args=parser.parse_args()
    try:
        if args.check_html:
            run()
    except Exception as exc:
        reason=str(exc)
        if not reason.startswith("P1.4 HTML STUB STOP:"):
            reason="P1.4 HTML STUB STOP: internal immutable/runtime/asset overlay check failed"
        print(reason,file=sys.stderr,flush=True)
        print("Never reset fifth PG, replay schema/seed one-shots, or change protected four PG.",
              file=sys.stderr,flush=True)
        raise SystemExit(1)

if __name__=="__main__":
    main()
