# Gor's Coffee — sandbox multipart cleanup failure, read-only forensics (2026-11-04)

## Verified evidence supplied by owner

The owner executed Draft PR #38's exact validated scripts on Linux, with the following results:

- `cafe_sandbox_rails.py --check`, `--create`, and `--smoke` all PASSED. A new sandbox-only Rails container is running with CarrierWave 2.2.7, the restored private sandbox PostgreSQL and 10 copied QA images, with **no published host port**. Production 3001 and QA 3002 stayed HTTP 200.
- `cafe_sandbox_upload_tests.py --check` PASSED and `--run` entered `BEGIN REAL HTTP MULTIPART TESTS IN ISOLATED SANDBOX`.
- The Ruby test ended **after the per-case assertions** but **failed the final media baseline check**: `stdin:196:in <main>: QA media differs from restored baseline after cleanup (RuntimeError)`. There was no final success marker. The test runner exited non-zero. Neither a secure-upload PASS nor a production release can be claimed.

The test's Ruby `ensure` block destroyed its generated `accept-` and `reject-` disposable users, then compared the on-disk file SHA256 inventory against the original ten files. This alone does **not** identify whether CarrierWave cache/temp files, avatar originals, thumb versions, or changed baseline files are responsible. A read-only diff is required **before any deletion, further uploads, or rerunning the test**.

## New Draft PR

`scripts/cafe_sandbox_media_forensics.py` is a read-only instrument:

- Confirms the sandbox Rails/database are running strictly on the dedicated **internal** Docker network; distinct from active QA and live PostgreSQL via `system_identifier`; no sandbox host ports; only the sandbox media bind writable; protected application and secret mounts; HTTP 200 on live 3001 and QA 3002.
- Reads `~/Backups/cafe_app/private_runtime/qa_security_snapshot_20261104_sqwulocr/manifest.json`, verifies the SHA256 of `qa_uploads_patched.tar.gz`, and calculates the ten original filenames/hashes **in memory**. **Never extracts or writes** snapshot data.
- Calculates current sandbox-only media SHA256, then reports counts for added/missing/modified files, aggregate category `temporary/cache`, `avatar/or-thumbnail` or `other`, byte sizes, and **opaque short hashes of path names**. It intentionally does **not** expose original filenames, real account emails, image content, password hashes or secrets.
- Reads aggregate sandbox user counts (total and `accept-`/`reject-` generated email prefixes) through read-only SELECT, never queries the live databases for accounts.
- Does not run any `DELETE`, cleanup, `docker stop/rm`, `shutil.rmtree`, restoration or upload; it leaves the sandbox intact for follow-up.

## Next decision: based on actual evidence, not guesses

- **Only cache/tmp files added, DB test users zero:** The file validation likely behaved correctly in the per-case tests, but CarrierWave or multipart caching leaves temporary artefacts. Determine whether this is expected during sessions or a true leak, add a test-only scoped cleanup/persistence policy and repeat only against the sandbox after it is safe.
- **Avatar originals/thumbs remain:** Investigate CarrierWave delete callbacks and generated synthetic user cleanup; do not delete files merely by ID because baseline owners can have legitimate files.
- **Baseline files modified/missing:** Treat as a higher-severity isolation/persistence issue; preserve the sandbox unchanged and investigate before any new uploads.
- **Generated test users remain:** Investigate transaction/cleanup correctness; don't claim rollback or reuse the sandbox automatically.
- **No current difference:** Analyze timing/determinism and improve the Ruby probe to print per-case results before the final assertion, then run safely in sandbox.

Private media archives, SQL dumps and account information remain **only on owner's Linux**. GitHub and the Google Drive status doc receive summary facts, never original private data.

## Release status

Patched CarrierWave 2.2.7 is present in QA. Upload tests are **NOT ACCEPTED** due to the final cleanup failure. Before allowing public uploads, revalidate actual HTTP negative cases, image processing and resource caps, safe file serving, `nosniff` and CSP, authentication and CSRF, rate limiting, and supported Ruby/Rails runtime. All PRs remain Draft and unmerged.
