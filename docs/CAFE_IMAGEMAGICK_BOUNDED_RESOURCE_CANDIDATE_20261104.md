# Cafe sandbox ImageMagick bounded resource candidate — 2026-11-04

## Owner-verified input

- Owner's private **sandbox** completed a SHA-stable JPEG decode with `MAGICK_TIME_LIMIT=30`; `identify -list resource` printed `Time: 30`.
- Earlier read-only header/ImageMagick audit passed three isolated PostgreSQL clusters, internal network, exact ten private media-file SHA checks and HTTP 200 on original local 3001/3002. Original ImageMagick time limit was **unlimited**. Image HEAD lacked nosniff and referrer policy; HTML lacked CSP.
- These are owner-supplied local terminal observations, not proof that a persistent Rails worker has been hardened.

## Candidate (not applied to any Rails service)

`qa/security/imagemagick_resource_limits.env` is a **reviewed template**, not an env file automatically loaded by Rails. Only `scripts/cafe_sandbox_imagemagick_limits_candidate.py --check` sets those variables for **new subprocesses inside the existing private sandbox**, without Docker container restarts or application writes.

| Resource | Candidate limit |
| --- | --- |
| Time | 30 seconds |
| Image width and height | 8KP each |
| Pixel-cache area | 32MP |
| Pixel-cache heap | 128MiB |
| Pixel-cache mapped memory | 256MiB |
| Pixel-cache disk spill | 512MiB |
| Threads | 2 |
| Pixel-cache files | 64 |

Important: `MAGICK_AREA_LIMIT` is a **pixel-cache threshold**, not an independent total-pixel rejection. Dimensions are per-axis. Add a separately verified pixel-count/frame-count and format validator before public upload. Resource limits also cannot guarantee that every codec/delegate obeys limits; keep process timeouts, sandbox isolation and up-to-date libraries.

## Owner-local acceptance criteria

1. SHA-verify both the new helper and the pre-existing v3 audit; import the v3 audit without modifying it.
2. Reverify existing network, PostgreSQL, source and 10-file original snapshot state (fail closed).
3. Under subprocess-only `MAGICK_*` limits, read `identify -list resource` and reject missing, unlimited or too-loose limits.
4. Decode in-memory safe 8×8 sample; reject an in-memory 10000×1 sample over the proposed width cap.
5. Re-decode one existing private sandbox JPEG; prove its SHA unchanged, and re-run preflight. Output only sanitized fixed markers. No media paths, original bytes, DB values, raw Docker stderr or secrets.
6. Do **not** treat this as a real timeout enforcement test. A later separately approved negative timeout test, bounded multipart/decoder tests and a new throwaway QA Rails process inheriting the env profile are required.

## Further gates

The new QA Rails candidate must inherit these limits across MiniMagick subprocesses, pass valid PNG/JPEG/GIF avatar uploads and re-encoding, reject malicious/polyglot/multiframe/oversize images, preserve private media, and verify no breakage of menus/cart/auth. HTTP static-file nosniff/referrer and HTML CSP report-only require separate QA review and actual browser verification. Keep 3001/3002 untouched; no automatic rollout, PR merge, deploy or production promotion.
