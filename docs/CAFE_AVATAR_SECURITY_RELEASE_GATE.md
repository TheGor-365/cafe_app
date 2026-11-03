# Gor's Coffee — avatar upload security release gate (2026-11-04)

## Scope and status

This PR is **a candidate security policy and disposable CI proof only**, not a production upgrade.

The original AvatarUploader and avatar-mounted User model exist in the owner's dirty local Linux tree but are **absent upstream on GitHub**. This branch does not add or replace those files inside app/ in order to protect the owner's existing real avatars and private source. The read-only local app on ports 3001 and 3002 still has CarrierWave 2.2.1 installed in its legacy bundle.

Known advisory CVE-2026-44587 requires CarrierWave 2.2.7 for the 2.2 series; earlier Content-Type fixes are in 2.2.5 and 2.2.6. PR #30 has already verified that 2.2.7 resolves and passes the tested Rails suites in isolated CI. CI cannot patch the owner's live or QA Docker bundle.

## Candidate policy

qa/security/avatar_uploader.rb defines an isolated, drop-in AvatarUploader using the same storage directory and thumbnail processing as the owner's current uploader. It adds:
- Filename extension allowlist: jpg, jpeg, png, gif
- Explicit MIME allowlist: image/jpeg, image/png, image/gif only (not SVG/HTML)
- Size range: 1–2 MiB; an independent byte-size check
- Magic-byte signature check for JPEG/PNG/GIF, matched to filename extension
- Reject discrepancies with CarrierWave::IntegrityError

test/security/cafe_avatar_policy_test.rb exercises valid header types and rejects spoofed SVG/HTML, header-extension mismatches, empty data and >2 MiB bodies. The GitHub CI workflow resolves CarrierWave 2.2.7 **only in a throwaway checkout**. It does not modify the tracked Gemfile/lock or owner's container.

These controls do not prove a valid/non-polyglot image. Actual image decode/re-encode, ImageMagick pixel/resource limits, file serving headers (X-Content-Type-Options: nosniff), appropriate CSP, rate limiting and real multipart HTTP negative tests remain required before public uploads.

## Safe local sequence

1. Read-only audit the actual Linux AvatarUploader hash and app User mount, Gemfile/lock hashes, isolated QA web bundle mount, live vs QA PostgreSQL cluster identifiers, and dedicated QA uploads directory. Recheck HTTP 3001 and 3002.
2. Build an independent patched Ruby2.5 Rails6 bundle using reviewed Gemfile/lock **outside** the protected project. Pin CarrierWave 2.2.7; do not modify cafe-legacy-bundle-20261101 or original Gemfile/lock. Test the patched bundle separately.
3. Prepare a separately verified, private QA-only uploader override from the security candidate. Start **another** QA Rails container with readonly app, new readonly patched bundle, readonly uploader override, and separate writable QA uploads. Do not stop or modify production web, production DB or original media. Switch 3002 proxy only after all QA SQL/HTTP smoke and with rollback.
4. Browser-test legitimate photo and thumbnail and persistence after QA restart. Test SVG, HTML, invalid bytes, disguised MIME, oversized files, non-image payloads and unauthenticated requests through multipart HTTP. Negative responses must be safe and should not leave persisted uploads.
5. Only then plan supported Ruby/Rails upgrade and release approval, persistent production media with verified rollback, HTTPS, healthchecks and monitoring.

**This PR does not complete the security release gate. No public upload should be enabled until all local tests and the patched runtime pass.**
