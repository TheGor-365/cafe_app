# Gor's Coffee — restore isolated QA snapshot for upload security testing

Checkpoint: 2026-11-04. The owner verified snapshot `QA SECURITY SNAPSHOT VERIFIED` at private local path
`~/Backups/cafe_app/private_runtime/qa_security_snapshot_20261104_sqwulocr`.

The archive contains custom-format PostgreSQL `qa_cafe.dump` and separate SHA256-verified tarballs for the older and CarrierWave 2.2.7 QA media directories, each with ten files. These files may include test accounts and personally identifying images: **never upload archive contents to GitHub, Google Drive, email, third-party search or a public URL**.

## Implementation

`scripts/cafe_restore_security_sandbox.py` is an external standalone owner-Linux helper with two commands:

1. `--check`: read-only verification of manifest/checksums, both tar archives (each member path/type/payload), custom Postgres archive listing via `pg_restore --list`, both active services `3001` and `3002`, current QA and production PostgreSQL system identifiers, available local space, and absence of sandbox objects.
2. `--restore`: repeats preflight, restores **only** patched QA media files into a newly created mode-0700 private directory `~/.local/share/cafe_app/uploads_security_sandbox_20261104`, checking every restored file hash. Creates internal isolated Docker network `cafe-upload-security-sandbox-20261104` with no route outside and no published ports, then starts a new temporary PostgreSQL 16 container `cafe-upload-security-sandbox-pg-20261104` using tmpfs `/var/lib/postgresql/data` and `/var/run/postgresql`. It restores QA `cafe.dump` using `pg_restore --exit-on-error --single-transaction --no-owner --no-acl`, verifies the new cluster identifier differs from both original databases, 20 products, id 21 absent and at least ten public tables, and rechecks both active sites and media digests.

No existing Docker resource, original media tree, live/QA database, Git project or proxy is modified. No new Rails web is launched by this script and no real multipart test is executed. The isolated PG container is ephemeral (tmpfs); stopping/removing it deliberately discards only its disposable data. **Do not stop, delete or recreate the database or network during security testing.** If --restore fails, leave the partial sandbox in place for investigation, never blindly repeat it.

## Trust and security

The sandbox PostgreSQL server uses `POSTGRES_HOST_AUTH_METHOD=trust` only on a brand-new Docker `--internal` network without published ports; never attach that network/container to any live or public service. After restoration, the QA database will contain copied accounts and password hashes. Keep the sandbox private. Media extraction rejects symlinks, hardlinks, non-file entries, absolute paths and traversal, and verifies every byte against the authenticated private archive; it does not use `extractall`.

The PostgreSQL custom-format dump can be listed but recovery is only demonstrated after the *successful new separate restore*. This proves that snapshot's DB and media can be restored to private separate targets, not that an application's full end-to-end recovery has been tested, and not that DB/media snapshots were atomic.

## Subsequent end-to-end gate

After the isolated restore is verified, create another Rails candidate on that isolated network, with **read-only** project, patched readonly CarrierWave 2.2.7 bundle, reviewed QA-only uploader, separate sandbox media directory, and a disposable HTTP test ingress restricted to loopback. Real multipart requests must cover:
- Valid decodable JPEG, PNG and GIF; generated thumbnail and persistence after test web restart.
- HTML/SVG masquerading as jpg/png, invalid extensions, incorrect HTTP Content-Type, wrong magic bytes, oversized files above 2 MiB, empty/truncated data and image processing errors.
- Authentication/CSRF, safe rejection codes, no residual media/user rows on failure, no accidental access to production DB.
- ImageMagick resource/size policy and safe serving of originals and thumbnails with `X-Content-Type-Options: nosniff` and appropriate CSP.

Document and independently verify cleanup/rollback of sandbox test data; do not modify the owner's actual QA DB or original images. Existing public uploads remain blocked until these tests and supported Ruby/Rails modernization and security audit.
