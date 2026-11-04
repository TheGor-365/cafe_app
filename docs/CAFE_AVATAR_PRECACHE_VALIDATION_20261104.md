# Gor's Coffee — pre-cache validation candidate after isolated forensic run

2026-11-04 owner read-only forensic report established **one** added file under `temporary/cache` (3 bytes), no missing or changed baseline files, two baseline users and **zero generated accept/reject users**. Private sandbox currently has 11 files versus 10 archived. Production loopback 3001 and patched QA loopback 3002 HTTP 200; sandbox DB isolated from both.

The prior multipart request suite reached final cleanup check before failing `QA media differs from restored baseline after cleanup`. A 3-byte residue is *consistent* with the test case `truncated_jpeg` (3-byte JPEG signature), but do not equate bytes with a confirmed identification until inspecting the private sandbox's exact SHA256 path and content.

The CarrierWave 2.2 file uploader writes to its cache before invoking the `process` callbacks. The existing patched QA uploader only enforced image signature in `process :verify_image_bytes!`. If an image decoder rejects a file later, a cached temporary file can remain without an associated DB record.

## Candidate patch (NOT deployed)

`qa/security/avatar_uploader_preflight.rb` keeps the reviewed store directory, 2 MiB size cap, filename and content type allowlists, 50×50 thumb, and process-time byte guard. It adds `#cache!` validation of the *original incoming* file **before** invoking `super`, including:
- size cap, exact filename extension and initial magic byte agreement,
- reject explicitly misleading multipart Content-Type,
- `MiniMagick::Image#validate!` on source plus decoder format and pixel dimensions (12 megapixels maximum),
- reject corrupt images with `CarrierWave::IntegrityError` before public `uploads/tmp` caching.

No broad deleting, cache sweeping, original uploader overwrite or production deployment. The CI Ruby 2.5 test uses a **simulated image decoder** to assert method ordering and failure without public cache writes; it is not a claim that real ImageMagick accepts real files. The final acceptance gate remains owner-local isolated Rails on an independent test DB/media (not current public QA or production).

## Caution and follow-up

Do not edit the original private `app/uploaders/avatar_uploader.rb` file or existing shared `qa_patched_avatar_20261104` override: both current patched QA and sandbox mount the latter and replacing it would affect the host 3002 without restart. For acceptance, use a NEW private uploader override and NEW independent sandbox Rails only.

Before rerunning multipart tests, preserve the error evidence and remove only the exact three-byte generated temporary file within sandbox if path, SHA, signature, baseline and DB/network identity all agree. Do not delete arbitrary files or cache directories; maintain the private snapshot of ten originals. Adapt the probe to report signed-off per-case statuses and investigate other potential leaks (reject files, no persistent user, no orphans).

The private image/SQL backups must remain only on owner Linux. Ruby 2.5/Rails 6 EOL and image processing limits remain blockers to public uploads.

## Surgical sandbox-only evidence cleanup — no action until path check passes

The new `scripts/cafe_sandbox_scoped_cache_cleanup.py` uses the *unchanged* verified read-only forensic helper to enforce: private snapshot is still SHA256-valid; exactly ten original files remain byte-identical; only one extra file of exactly 3 bytes exists under `tmp`; its path SHA256 prefix matches the owner-observed opaque ID `c7f26d5886cc`; its bytes equal the original truncated-JPEG fixture `FF D8 FF`; file is a regular, non-symlink, single-link object inside the private sandbox; sandbox vs QA vs production PG clusters are distinct and generated synthetic users are zero. `--check` makes no changes. `--clean` performs **one `unlink` only on that exact sandbox file**, and verifies the entire 10-file baseline again. It never removes a directory, changes a DB row or touches the original QA/live upload trees. If any guard fails, stop without any deletion.

## New isolated acceptance candidate

`scripts/cafe_precache_sandbox_acceptance.py` uses the owner-reverified private 10-file sandbox baseline and original sandbox Rails configuration to create **another** internal-only sandbox Rails instance, with the new `qa/security/avatar_uploader_preflight.rb` mounted as a distinct read-only private file. The old local uploader and the *currently running patched QA* uploader mount remain untouched. The script has `--check`, `--create`, `--smoke` and `--test` stages. Only `--test` invokes the existing Git-blob-pinned real HTTP multipart Ruby suite inside that new sandbox container (same disposable sandbox DB/media). The new sandbox has **no host port** and no DB migration. Any failed test preserves evidence and blocks release; never rerun `--create` over an existing container.

Before the owner runs acceptance, the Ruby 2.5 pre-cache policy CI must pass, and the helper/uploader Git blob IDs must be fetched, checked and copied into new private host paths. No public upload or master merge is implied by CI success.
