# Gor's Coffee — private QA snapshot before multipart security tests (2026-11-04)

## Owner-confirmed evidence

Owner executed the exact Draft PR #35 proxy switch on Linux:

- `PATCHED QA PROXY PREFLIGHT PASS` (before and during switch)
- `PATCHED QA PROXY HTTP 200 / SIGNUP AVATAR FORM PASS`
- `PRODUCTION 3001 HTTP 200`
- `OLD QA PROXY PRESERVED (STOPPED)`
- `PATCHED QA PORT 3002 SWITCH VERIFIED`
- `PATCHED QA CUTOVER COMPLETE`

Thus port 3002 now targets the patched Rails QA candidate (CarrierWave 2.2.7), with the original QA proxy available for rollback; port 3001 remains on the original site. Both QA Rails containers point to the same isolated QA PostgreSQL, but each uses **its own uploaded-file directory**. The original QA media remains intact.

## This PR

`scripts/cafe_qa_security_snapshot.py` is an owner-local standalone script that adds no changes to the running applications.

`--check` validates all relevant containers are running/stopped in the expected states, the new QA proxy is loopback-only and points to the patched Rails web, QA network is separated from production PostgreSQL, distinct PG system identifiers, media mounts, actual loaded CarrierWave 2.2.7, 3001/3002 HTTP 200, and QA catalog 20 products / test ID 21 absent. It inventories both directories and checks backup disk capacity, without modifying anything.

`--snapshot` repeats all checks, creates a **new private mode-0700 directory** under `~/Backups/cafe_app/private_runtime`, obtains a custom-format `pg_dump` of **only the isolated QA `cafe` database**, verifies its `pg_restore --list` includes tables and data, writes archives of both previous and patched QA media directories, reads the archives back and verifies every original file SHA-256. It checks that neither directory changed during the archival process. It writes a private JSON manifest with archive checksums and checks both HTTP endpoints again. Archives are mode 0600. No extraction/restore, delete, upload or Git commit is performed.

**This is an on-disk checkpoint, not a proven end-to-end recovery.** PG dump is transaction-consistent but the files and database are not snapshotted atomically; while running it, **do not use the browser to register users, upload images, modify products, change the QA database or restart containers.** A future restore rehearsal must run against a wholly isolated temporary PostgreSQL and fresh media directory to establish recoverability; do not restore into original QA or live DB.

The backup will contain potentially private avatars and account data. **Never upload these archives, SQL dumps or the manifest to public GitHub, Google Drive folders indexed by external AI, email or issue comments.** Only report non-sensitive success lines and file counts. Do not put secrets in the commit.

## After verified snapshot

Prepare a separate disposable test database restored from this checkpoint (not the active QA DB) and media copy to run actual multipart uploads in a new isolated environment. Validate valid JPEG/PNG/GIF (complete, decodable files), spoofed HTML/SVG, bad MIME, mismatched signature/extension, excessive bytes, truncated/corrupt images, no residual user files/rows on rejection, authentication/CSRF/rate limiting, and persistence after restart. Independently audit ImageMagick decode/re-encode, pixels/frames/time/resource policy and public file headers (nosniff/CSP).

Production port 3001 and original QA data must remain protected throughout. Legacy Ruby 2.5/Rails 6 and other dependencies need a separate supported-version modernization gate before public deployment.
