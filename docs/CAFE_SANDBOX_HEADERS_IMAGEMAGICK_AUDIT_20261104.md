# Gor's Coffee — sandbox file-serving headers and ImageMagick resource gate (2026-11-04)

## Verified owner evidence

User Linux terminal from pinned Draft PR #40 proves a full isolated-sandbox HTTP multipart E2E pass:
- One 3-byte rejected-JPEG cache file, exactly FF D8 FF, removed **only from sandbox** after verifying private snapshot original 10 media hashes remained byte-identical.
- New second isolated Rails container `cafe-upload-security-sandbox-precache-20261104` runs with pre-cache candidate uploader, CarrierWave 2.2.7 and isolated PostgreSQL; no published ports.
- All 7 negative multipart cases (HTML-as-JPEG, SVG, mismatched bytes/extension, oversize, empty, truncated JPEG, misleading MIME) returned validation HTTP 200 and no user; all 3 positives (PNG, JPG, GIF) gave HTTP 302, DB+original+thumbnail+authenticated account. Generated user and media cleanup PASS, original 10 media SHA unchanged.
- Production `3001` and active older patched QA `3002` unchanged. **The new pre-cache uploader is NOT active on QA port 3002 or the main site.** No public release approval.

## What this PR adds

`scripts/cafe_sandbox_headers_imagemagick_audit.py --check` conducts a **read-only**, owner-run runtime observation:

1. Loads the exact SHA-pinned original acceptance helper from `~/.local/share/cafe_app`. Requires the main project local checksums, the private ten-file snapshot, sandbox/QA/production distinct PostgreSQL system IDs, the independent internal Docker network, the new Rails container running as UID1000 with a readonly application and pre-cache uploader mount, sandbox-only writable media and no published host port, and active `3001/info` and `3002/menu` HTTP 200.
2. Executes an embedded Ruby Rails runner *inside the new isolated sandbox Rails container*. It verifies the real sandbox PG system ID and CarrierWave2.2.7, performs **HTTP GET /users/sign_up** and `/info` and **HTTP HEAD** on one available image from the ten restored private files (if one is available and not over 5 MB). It outputs only a scrubbed JSON observation: status, MIME, X-Content-Type-Options nosniff, CSP present, Report-Only CSP present, Referrer-Policy present, wildcard CORS and cache-header presence. It **does not** print, send or store the private filename, image contents, credentials, cookies or SQL values.
3. Reads ImageMagick's **actual in-container** `identify -list resource` and `identify -list policy` without changing any policy. Reports relevant declared width/height/area/memory/map/disk/time limits, and whether policy rights were present, using a small whitelist of text tokens rather than disclosing configuration file paths.

This is evidence gathering, NOT a security PASS claim: missing headers, unavailable image HEAD, unlimited policy values or absent policy rights are findings for targeted remediation. HTTP HEAD may differ from an actual GET; independent real-body and content-type validation remains a release gate. Even an ImageMagick resource listing is **not sufficient** by itself: test decoder timeouts, polyglots, frame counts, resource bombs and safe re-encoding separately.

## Source-based policy observations

From checked-in `config/environments/development.rb`, sandbox Rails is development mode (`consider_all_requests_local=true`); this is intentionally internal-only and must not become public. In checked-in `config/environments/production.rb`, `config.force_ssl` is commented and static public file delivery depends on `RAILS_SERVE_STATIC_FILES`; absence of a line of code does not prove actual live HTTP header behavior. Checked-in `config/initializers/content_security_policy.rb` contains commented example policy rather than an active application-wide declaration. Rails defaults, middleware and any front proxy can still change observed headers: therefore inspect actual runtime HTTP, do not make claims solely from source.

## Restrictions and next decision

- No new container, no Docker stop/start, no SQL migration/write, no file upload/removal or snapshot changes. The script only GET/HEADs localhost inside the *already running private Rails sandbox* and executes read-only metadata commands.
- Do not publish private SQL dump/media or exact path names in GitHub, Drive or tickets. Only the sanitized output is suitable for a progress comment.
- Based on actual HTTP/image policy evidence, create another **separate** QA-only candidate header policy and ImageMagick limits with tests. Never edit owner's local uploader, existing QA overlay or public site in place.
- No Draft PR merge or production rollout without a rollback plan, actual browser acceptance, CSP compatibility review and supported Ruby/Rails modernization.
