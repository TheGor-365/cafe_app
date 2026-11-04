# Cafe private QA headers runtime — 2026-11-04

## Owner-verified evidence

On 4 November the owner ran exact SHA-pinned PR #46 real loopback TCP HTTP audit:
- LOOPBACK_HTTP_SIGNUP_HTML_PASS
- LOOPBACK_HTTP_INFO_HTML_PASS
- LOOPBACK_HTTP_JPEG_HEAD_PASS
- LOOPBACK_HTTP_JPEG_GET_SHA_PASS
- LOOPBACK_REAL_HTTP_CANDIDATE_READ_ONLY_COMPLETE

Original 10 private media SHA256, three distinct PostgreSQL clusters, QA/live isolation, host ports 3001/3002 HTTP 200 were reverified. The prior ImageMagick subprocess limit probe (PR #44) and in-memory Rack header probe (PR #45) also passed. None of these earlier runs installed permanent protection in a Rails worker.

## Explicit three-phase owner-local workflow

The reviewed helper at scripts/cafe_private_headers_qa_runtime.py is not run by CI against private resources.

1. --check: READ-ONLY. Verifies pinned owner preflight, source/runtime hashes, 10 original files, distinct sandbox PG and networks, source Docker image, mounts, healthy 3001/3002. Refuses any existing target directory/container.
2. --create: creates only a *new* private stage at ~/.local/share/cafe_app/headers_private_web_candidate_20261104 with a SHA-verified 10-file **copy** of the private media, a reviewed config.ru overlay, and a NEW Docker container named cafe-upload-security-headers-private-20261104. Container is CREATED BUT NOT STARTED. Originals are never overwritten or removed.
3. --smoke: starts ONLY the new candidate container and checks its real internal TCP HTML GET, JPEG HEAD+GET with SHA verification, CSP Report-Only/nosniff/referrer, pre-cache CarrierWave2.2.7 guard, MAGICK_* inherited variables, and **POST 405**. Re-verifies original media, PG isolation and 3001/3002.

No host port, public DNS, Railway deploy, or QA 3002 cutover. Existing source is mounted read-only; the new /app/config.ru and /app/qa_headers_candidate.rb overrides are read-only and affect only the new container. The only writable source bind is the NEW private media copy. The private Docker network has no external connectivity. Credentials/raw private DB/media data are never printed or uploaded.

## Important database constraint

The new QA web initially uses the existing INTERNAL-ONLY SANDBOX Postgres cluster, **not** production or QA 3002 Postgres. Its Rack config blocks ALL HTTP methods except GET and HEAD (405). The new container also sets PGOPTIONS=-c default_transaction_read_only=on, verified by a SHOW query in smoke, to keep normal libpq sessions read-only. A privileged DB role can override this option, so it is defense-in-depth, not a strict independent read-only database permission. It is suitable only for read-only HTML/static smoke. It is **not** an independent writable test database and must not be used yet for real login, admin mutations, avatar upload, or multipart testing. A separate fourth internal PostgreSQL cluster and distinct test fixtures are prerequisites before enabling POST or exposing a local browser preview.

## ImageMagick and CSP boundaries

The proposed ImageMagick limits (time 30s, width/height 8KP, pixel cache area 32MP, memory 128MiB, map 256MiB, disk 512MiB, threads 2, file 64) become environment variables in the newly started candidate process; this does not prove negative timeout enforcement. Area is a pixel-cache threshold, not a total-decoded-pixel cap.

CSP is Report-Only, no collector; the user must inspect Chrome/Firefox Console and compare actual network response before considering enforcement. No external reverse proxy has been tested. UI/JS/Google Fonts/browser and multipart tests remain blocked until dedicated independent QA state and a controlled localhost-only preview are added.

## Fail-closed and resource safety

On partial --create failure leave the new stage/container in place and diagnose, **do not blindly rerun or delete**. The script offers no cleanup operation. The new container has readonly root, user 1000, 1GiB RAM, pids-limit, all caps dropped, no-new-privileges, no host ports, no restart policy. Existing 3001/3002 and Docker volumes should remain unchanged. CI validates only syntax, pure Rack tests and static safety guards, not owner's runtime.

Next: owner --check after SHA-pinned fetch; then separately --create and --smoke if checks pass. No production readiness or master merge approval.
