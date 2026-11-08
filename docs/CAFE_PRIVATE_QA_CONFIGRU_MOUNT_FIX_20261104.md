# Cafe QA: OCI read-only mountpoint repair — 2026-11-04

## Verified owner-local outcome

The separate container cafe-upload-security-headers-private-20261104 passed --verify-created with verified network/PG/media isolation and 10-file SHA256, but its first --smoke was unable to start it. Docker returned a redacted "new QA candidate start failed". The owner performed a read-only Docker inspect:
- STATUS=created; EXIT_CODE=128; OOM_KILLED=False
- OCI/runc error categories: read-only file system, OCI runtime create failed, runc create failed
- /app: directory, readonly; /app/config.ru: file, readonly; /app/qa_headers_candidate.rb: file on host, readonly; /app/public/uploads: private sandbox-media copy, writable
- Host 3001/3002 HTTP 200, original source, private media and 3 PG networks remained intact as of previous preflight.

Root-cause hypothesis (not proof until the full sanitized OCI target check): the first QA candidate attempted to add a bind mount at /app/qa_headers_candidate.rb, a path not present in the readonly original /app source mount. OCI/runc cannot create that new mountpoint inside the read-only bind. The original /app/config.ru file, however, already exists.

## Repair design

This is a **NEW** branch and separate helper; it does not modify or recreate the failed container, existing service, old private media or owner's source code.

- scripts/cafe_private_headers_qa_mountfix.py: staged --check (read-only), --create (create but DO NOT start), --verify-created (read-only), --smoke (start only new container).
- --check checks the exact owner v3 SHA-pinned Docker/PG/10-media preflight and requires the preserved failed container to remain Created, private, internal-only, with original 10-file media identical. It extracts the OCI error **in process without printing the raw path** and refuses creation unless both read-only-file-system and qa_headers_candidate.rb appear. Thus it fails closed on a different failure cause.
- A new staging directory headers_private_web_mountfix_20261104 and container cafe-upload-security-headers-mountfix-20261104 are separate from the old failed evidence. No delete, overwrite, restart, stopped service or new network.
- Only ONE extra nested mount: a private generated config.ru at the **existing** /app/config.ru file, mounted readonly. There is no mount at the nonexistent /app/qa_headers_candidate.rb target.
- The config.ru is built from the SHA-pinned, reviewed PR #45 CafeHeadersCandidate Ruby class embedded verbatim between the Rails environment loader and the QA Rack middleware; no new source tree paths need to exist. It adds report-only CSP, nosniff and referrer headers, and an outer read-only GET/HEAD method gate (405 for other HTTP methods).
- All other inherited mounts match the SHA-pinned pre-cache private sandbox: original source, patched bundle and uploader read-only, only the NEW media copy writable. New runtime is Docker root read-only, UID 1000, internal network only, no host ports, 1GiB memory, no-new-privileges, drop caps, no restart. ImageMagick nine env resource caps from earlier CI-approved candidate.
- It shares only the private sandbox PostgreSQL (NOT QA 3002/production) and configures PGOPTIONS=-c default_transaction_read_only=on, verified via Rails SQL. Do not use it for login, mutations or multipart. A fourth independent sandbox PG is required before interactive QA.
- --smoke, if independently owner-executed after exact SHA pin/check/create/verify, tests real HTTP 200 for HTML, static JPEG HEAD/GET with original SHA unchanged, CSP Report-Only, no enforced CSP, Referrer-Policy/nosniff, POST 405 and CarrierWave2.2.7 guard. Existing original services 3001/3002 and 10 media are reverified.
- CI checks syntax and generated Ruby Rack config, source Git blob, existing mountpoint, strict no extra mount, readonly safety, ImageMagick profile, and pure Ruby Rack tests. CI cannot prove owner Docker boots successfully, even with a corrected path.

## Execution constraints and status

Old failed Docker container and previous private candidate stage must be preserved; no blind retries. First run only SHA-pinned --check of the **new** helper. If it reports OCI READONLY ROOT CAUSE ... PASS and EXISTING CONFIG.RU ... VERIFIED, the new stage is eligible for a separate --create. If it refuses the cause, use a new read-only sanitized Docker error inspection; do not create another candidate until the real problem is known.

No public rollout, external proxy/cutover, master merge or Google Drive upload is part of this stage. Browser/CSP compatibility still pending.
