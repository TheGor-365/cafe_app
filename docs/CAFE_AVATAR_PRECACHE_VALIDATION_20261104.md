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
