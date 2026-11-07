#!/usr/bin/env python3
"""P1.4 genuine Webpacker test assets: immutable GitHub ZIP verification then READONLY GET.

Two explicit modes:
 --verify-archive --archive /absolute/path/...zip : no Docker/PG and no extraction.
 --check-real-get --archive /absolute/path/...zip : separately gated, fifth-only
        READONLY Rails Rack GET using actual compiled Webpacker test artifacts.

All source modifications/asset extraction happen only inside TemporaryDirectory
with immutable Rails source archive, never in the owner's dirty checkout. The
fifth PG (tmpfs) and four original PG/media/3001/3002 remain protected. Normal
rails test, fixtures, migrations, seeds, DDL/DML are never invoked.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import zipfile

HOME=Path.home()
REPO=HOME/"Рабочий стол/rails_projects/lite/cafe_app"
PRIVATE=HOME/".local/share/cafe_app"
STUB_HELPER=PRIVATE/"cafe_p14_fifth_html_stub_assets_20261107.py"
STUB_BLOB="215312d18949745695b4fcc70d2485271386ea2f"
GITHUB_RUN=42384029688
GITHUB_ARTIFACT_ID=13578972029
SOURCE_SHA="dc5dacb9d79b9d7a8951ebcd0b74b489933d53cd"
ZIP_SHA256="95cc0c7985b4aba252470aff3493ee64664f371fa7eb9a8127cccd5e551405e3"
DB="cafe_synthetic"
NETWORK="cafe-upload-security-synthetic-net-20261105"
ALLOWED_SUFFIXES={".js",".css",".map",".json",".svg",".png",".jpg",
                  ".jpeg",".gif",".ico",".webp",".woff",".woff2",".ttf",".eot"}
ALLOWED_DIRS={"js","css","media","fonts","images"}
ZIP_PREFIXES=("", "packs-test/", "public/packs-test/")
MAX_ZIP=25*1024*1024
MAX_SINGLE=60*1024*1024
MAX_UNCOMPRESSED=180*1024*1024
MAX_FILES=1500
MIN_JS=1000
MARKERS=(
 b"P1.4 GET DIAG RUBY_ENTRY PASS",
 b"P1.4 GET DIAG APP ROLE / POSTGRES READ-ONLY / CATALOG PASS",
 b"P1.4 GET DIAG ALL HTTP ROUTES / COUNT ASSERTIONS PASS",
)
def require(ok,reason):
    if not ok: raise RuntimeError("P1.4 REAL WEBPACK STOP: "+reason)

def git_hash(path):
    p=subprocess.run(["git","-C",str(REPO),"hash-object",str(path)],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     check=False,timeout=20)
    require(p.returncode==0, "immutable source Git hash unavailable")
    return p.stdout.decode("ascii").strip()

def read_archive(path):
    require(path.is_absolute() and path.name=="cafe-p14-fifth-real-packs-test.zip",
            "archive path must be exact absolute GitHub artifact filename")
    require(path.is_file() and not path.is_symlink(),
            "artifact ZIP missing or symlinked")
    st=path.stat()
    require(st.st_uid==os.getuid() and 0<st.st_size<=MAX_ZIP and
            stat.S_ISREG(st.st_mode) and not(st.st_mode & 0o022),
            "artifact owner/mode/size unsafe")
    data=path.read_bytes()
    require(len(data)==st.st_size,"artifact size changed during read")
    require(hashlib.sha256(data).hexdigest()==ZIP_SHA256,
            "GitHub artifact ZIP SHA256 mismatch")
    return data

def verify_entries(data):
    try:
        archive=zipfile.ZipFile(io.BytesIO(data))
        infos=archive.infolist()
        require(0<len(infos)<=MAX_FILES,
                "unexpected ZIP file count")
        names=[f.filename for f in infos]
        require(len(names)==len(set(names)),"duplicate ZIP paths detected")
        prefix=next((x for x in ZIP_PREFIXES if x+"manifest.json" in names),None)
        require(prefix is not None,
                "real Webpacker manifest is absent")
        files={}
        total=0
        for info in infos:
            full=info.filename
            require(full.startswith(prefix),"mixed ZIP root prefixes")
            rel=full[len(prefix):]
            require(rel!="" or info.is_dir(),"empty ZIP filename")
            require(not info.flag_bits&0x1 and not "\\" in rel,
                    "encrypted/non-POSIX ZIP entry")
            p=PurePosixPath(rel)
            require(not p.is_absolute() and ".." not in p.parts and
                    len(rel)<240 and not any(ord(c)<32 for c in rel) and
                    not rel.startswith("./") and ":" not in rel,
                    "unsafe ZIP path")
            if info.is_dir():
                require(rel.startswith(tuple(d+"/" for d in ALLOWED_DIRS)) or
                        rel.rstrip("/") in ALLOWED_DIRS,
                        "unexpected ZIP directory")
            else:
                require(rel=="manifest.json" or
                        (p.parts[0] in ALLOWED_DIRS and
                         len(p.parts)>=2 and p.suffix.lower() in ALLOWED_SUFFIXES),
                        "unexpected ZIP file type or directory")
                require(0<info.file_size<=MAX_SINGLE,
                        "unexpected ZIP file size")
                total+=info.file_size
                require(total<=MAX_UNCOMPRESSED,
                        "ZIP expanded size limit exceeded")
                files[rel]=info
            kind=(info.external_attr >> 16) & 0o170000
            require(kind in ((0,stat.S_IFDIR) if info.is_dir() else (0,stat.S_IFREG)),
                    "symlink/device/special ZIP file denied")
        require("manifest.json" in files and len(files)>=2,
                "manifest / compiled files missing")
        manifest=json.loads(archive.read(files["manifest.json"]))
        require(isinstance(manifest,dict),"invalid Webpacker manifest")
        entry=manifest.get("application.js")
        require(isinstance(entry,str) and re.fullmatch(
                 r"/packs-test/js/application-[a-z0-9]+\.js",entry),
                "expected genuine fingerprinted application.js absent")
        relative=entry.removeprefix("/packs-test/")
        require(relative in files and files[relative].file_size>=MIN_JS,
                "compiled application.js missing or too small")
        contents=archive.read(files[relative])
        require(b"NON-FUNCTIONAL frontend pack" not in contents and
                b"P1.4 disposable" not in contents,
                "test placeholder is not a real JS bundle")
        return prefix,files,entry,manifest
    except (ValueError,KeyError,UnicodeError,zipfile.BadZipFile,
            zipfile.LargeZipFile,json.JSONDecodeError) as e:
        raise RuntimeError("P1.4 REAL WEBPACK STOP: corrupt or unsafe ZIP/manifest") from None
    finally:
        if 'archive' in locals():archive.close()

def reviewed_stub():
    require(os.getuid()==1000 and REPO.is_dir() and (REPO/".git").is_dir(),
            "unexpected operator/repository")
    require(STUB_HELPER.is_file() and not STUB_HELPER.is_symlink(),
            "original owner-only P1.4 stub helper not found")
    st=STUB_HELPER.stat()
    require(st.st_uid==os.getuid() and st.st_mode&0o077==0 and
            git_hash(STUB_HELPER)==STUB_BLOB,
            "original reviewed P1.4 stub helper hash/mode changed")
    spec=importlib.util.spec_from_file_location("p14_reviewed_html_stub",STUB_HELPER)
    require(spec is not None and spec.loader is not None,
            "reviewed P1.4 source helper not loadable")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    require(mod.DB==DB and mod.NET==NETWORK and
            mod.SOURCE=="090b9d37419fcd9f393d8b686ac0f4563ef7b613" and
            mod.WEBPACKER_YML_BLOB=="83615b0f9ac0ca5508548621150789c7dad71071",
            "original P1.4 immutable source/DB/asset contract differs")
    return mod

def install_real_assets(stub,schema,source,data,verified):
    prefix,files,entry,manifest=verified
    require(schema.SOURCE==stub.SOURCE and schema.DB==DB,
            "source/PG mismatch")
    webpack=source/"config/webpacker.yml"
    require(webpack.is_file() and not webpack.is_symlink() and
            schema.git("hash-object",str(webpack))==stub.WEBPACKER_YML_BLOB,
            "canonical Webpacker configuration blob differs")
    orig=webpack.read_text(encoding="utf-8")
    require(orig.count(stub.YML_BEFORE)==1 and
            "extract_css: false" in orig,
            "canonical webpacker test setting differs")
    root=source/"public/packs-test"
    require(not root.exists() and not root.is_symlink() and
            not (source/"node_modules").exists(),
            "temporary Rails source is not clean")
    root.mkdir(mode=0o700)
    # All paths have already been validated; disallow links and special files.
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for relative,info in sorted(files.items()):
            dest=root.joinpath(*PurePosixPath(relative).parts)
            require(root in dest.parents and
                    not dest.exists() and not dest.is_symlink(),
                    "unsafe or duplicate extraction target")
            dest.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            with dest.open("xb") as stream:
                with archive.open(info) as source_stream:
                    while True:
                        chunk=source_stream.read(1048576)
                        if not chunk: break
                        stream.write(chunk)
            require(dest.stat().st_size==info.file_size,
                    "extracted real asset size differs")
    require(json.loads((root/"manifest.json").read_text())==manifest,
            "staged Webpacker manifest differs")
    require((root/entry.removeprefix("/packs-test/")).stat().st_size>=MIN_JS,
            "real JS missing after staging")
    webpack.write_text(orig.replace(stub.YML_BEFORE,stub.YML_AFTER),
                       encoding="utf-8")
    require(webpack.read_text()==orig.replace(stub.YML_BEFORE,stub.YML_AFTER) and
            schema.git("rev-parse",stub.SOURCE+":config/webpacker.yml")==stub.WEBPACKER_YML_BLOB,
            "temporary only compile:false overlay failed")
    print("P1.4 REAL WEBPACKER MANIFEST / COMPILED TEST JS TEMP STAGING PASS",flush=True)

def verify_only(path):
    data=read_archive(path)
    verified=verify_entries(data)
    _prefix,files,entry,_manifest=verified
    print("P1.4 GITHUB ARTIFACT SHA256 VERIFIED PASS",flush=True)
    print("P1.4 ZIP ENTRIES/PATHS/UNCOMPRESSED SIZE/NO SYMLINK PASS",flush=True)
    print("P1.4 REAL WEBPACKER TEST MANIFEST/COMPILED JS PASS",flush=True)
    print("P1.4 ARCHIVE VERIFY PASS — NO EXTRACTION OR DB ACCESS",flush=True)
    return data,verified

def check_real_get(path):
    data,verified=verify_only(path)
    stub=reviewed_stub()
    view=stub.import_view_module()
    old=view.load_previous()
    p14=old.module()
    p13=p14.pinned_module()
    p13.verify()
    schema=p13.load_schema()
    ip,cluster=schema.target()
    require(cluster not in schema.protected_four(),
            "fifth cluster identity overlaps protected originals")
    secret=p14.app_secret(schema,cluster)
    probe,mounts=schema.runtime()
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="cafe-p14-real-assets-readonly-") as stage:
        source=schema.build_source(probe,stage)
        install_real_assets(stub,schema,source,data,verified)
        for file,sha in ((old.ORIG_RUBY,old.ORIG_RUBY_BLOB),
                        (old.DIAG_RUBY,old.DIAG_RUBY_BLOB),
                        (view.VIEW_RUBY,view.VIEW_RUBY_BLOB)):
            dest=source/"qa/security"/file.name
            require(not dest.exists() and not dest.is_symlink(),
                    "fifth-only Ruby source staging collision")
            with dest.open("xb") as output:
                output.write(file.read_bytes())
            require(schema.git("hash-object",str(dest))==sha,
                    "reviewed Rack GET Ruby source SHA differs")
        argv=stub.make_command(view,old,p14,schema,source,mounts,ip,cluster,secret)
        for flag in ("--rm","--read-only","--pull=never","--cap-drop=ALL",
                     "--security-opt=no-new-privileges",
                     "--network="+NETWORK,"--user=1000:1000",
                     "--env=RAILS_ENV=test",
                     "--env=PGOPTIONS=-c default_transaction_read_only=on -c search_path=public",
                     "--env=CAFE_P12_EXPECTED_CLUSTER_ID="+cluster):
            require(flag in argv,"reviewed fifth-only Docker contract differs")
        require(not any(x in argv[-1] for x in (
            "db:schema:load","db:seed","db:drop","db:prepare","db:migrate",
            "rails test","db:reset")),
            "unexpected database writer command")
        require(schema.target()==(ip,cluster),
                "fifth PG target changed before GET")
        print("P1.4 REAL WEBPACKER FIFTH-ONLY READONLY SCRAM APP/PG TARGET PASS",flush=True)
        try:
            done=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                check=False,timeout=180)
        except (OSError,subprocess.TimeoutExpired):
            raise RuntimeError("P1.4 REAL WEBPACK STOP: disposable Rails runner unavailable/timeout")
        result=old.output_classification(done.stdout,done.returncode,done.stderr)
        asset=view.classify(done.stdout)
        markers_ok=all(x in done.stdout for x in MARKERS)
    require(schema.target()==(ip,cluster),
            "fifth cluster identity changed after real-asset GET")
    p13.verify()
    state,stage,kind,status=result
    print("P1.4 REAL WEBPACK GET STAGE="+stage,flush=True)
    print("P1.4 REAL WEBPACK GET KIND="+kind,flush=True)
    if status is not None and status in old.STATUS:
        print("P1.4 REAL WEBPACK GET HTTP_STATUS="+status,flush=True)
    if state=="PASSED" and markers_ok:
        print("P1.4 REAL WEBPACK TEST ASSETS / SERVER GET ROUTES/ACL PASS",flush=True)
        print("P1.4 BROWSER JS/CSS EXECUTION AND WRITABLE E2E NOT TESTED",flush=True)
    else:
        print("P1.4 REAL WEBPACK VIEW ROOT_CAUSE="+asset["ROOT_CAUSE"],flush=True)
        print("P1.4 REAL WEBPACK SERVER GET BLOCKED; NO INTENDED DB WRITES",flush=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify-archive",action="store_true")
    mode.add_argument("--check-real-get",action="store_true")
    ap.add_argument("--archive",type=Path,required=True)
    args=ap.parse_args()
    try:
        if args.verify_archive:
            verify_only(args.archive)
        elif args.check_real_get:
            check_real_get(args.archive)
    except Exception as exc:
        msg=str(exc)
        if not msg.startswith("P1.4 REAL WEBPACK STOP:"):
            msg="P1.4 REAL WEBPACK STOP: immutable source/artifact/runner safety check failed"
        print(msg,file=sys.stderr,flush=True)
        print("Do not touch original four PG/media, restart fifth tmpfs, or replay P1.2/P1.3 one-shot operations.",
              file=sys.stderr,flush=True)
        raise SystemExit(1)

if __name__=="__main__":
    main()
