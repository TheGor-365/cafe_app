# Cafe loopback real-HTTP header candidate gate — 2026-11-04

## Owner-verified evidence before this gate

The owner ran the pinned in-process Rack header candidate audit from Draft PR #45 on Linux Mint. It reported:
- `QA_RACK_SIGNUP_HEADERS_PASS`
- `QA_RACK_INFO_HEADERS_PASS`
- `QA_RACK_JPEG_HEAD_HEADERS_PASS`
- `QA_RACK_EXISTING_ENFORCING_CSP:NO`
- preflight and postflight: sandbox, original host port 3001 and QA 3002 healthy; distinct three PostgreSQL clusters, protected private ten-file snapshot SHA256 unaltered.

This **does not** establish that an actual HTTP server has adopted the candidate. Prior audit used Rack MockRequest and in-memory wrapper. Draft PR #44 ImageMagick subprocess limits also passed, but no Rails worker inherits them yet.

## This PR: read-only loopback-only real HTTP probe

`scripts/cafe_sandbox_loopback_http_headers_audit.py --check`:

1. SHA-pins two **already owner-downloaded** files under `~/.local/share/cafe_app`: preflight `cafe_header_audit_v3_20261104.py` and the PR #45 `cafe_headers_candidate_v1_20261104.rb`. No repository worktree edits.
2. Calls exact preflight to validate Rails sandbox UID, mounts, internal Docker-only network with no host bindings, sandbox PostgreSQL cluster distinct from QA/production, original source checksums, ten-file private-media snapshot and working original host ports 3001/3002.
3. Starts a **single `bundle exec rails runner -` process** inside the existing separate sandbox Docker container. The runner wraps `Rails.application` with `CafeHeadersCandidate` *in memory only*. It starts an ephemeral WEBrick HTTP server bound specifically to `127.0.0.1:0` **inside that container**; the OS selects an unused port. There is no published host socket, no new container, no Rails config/initializer changes and no persistent worker environment change.
4. Actual Net::HTTP GET `/users/sign_up` and `/info` must return 200 HTML plus `nosniff`, Referrer-Policy and CSP **Report-Only** only (no enforcing CSP). HEAD and GET of one existing private sandbox JPEG must return correct image MIME, nosniff/Referrer, and no HTML CSP. The downloaded JPEG body stays in the runner process; its SHA256 is compared with the on-disk original, neither hash, path nor bytes are printed.
5. The WEBrick server is shut down in Ruby `ensure`. Any failure is redacted to a bounded stage and error **class**. Python captures the subprocess output/stderr and emits only fixed approved markers, never the path, body or raw exception text. After success Python runs the original preflight again.

## Limits and safety

- This is **not** a new separately deployed QA Rails container: the local loopback listener lives only for the `rails runner` call. It is not publicly reachable or wired to local 3001/3002; does not test the existing reverse proxy, browser scripts or real public URL.
- Pure Rails runner GET/HEAD should not need database/media writes; no HTTP POST, upload, migrations or data deletions are performed. Rails may emit ephemeral request logs to its existing tmpfs; this does not modify protected source or media.
- `config.consider_all_requests_local` remains true in this internal development sandbox. Never publish this environment.
- A process exit due to timeout before Ruby `ensure` executes may require inspection of the *sandbox-only* listener state; do not run concurrent reruns or issue broad Docker stop/kill/reset commands without diagnosis.
- Docker network isolation, 3001/3002, ten private original files and exact SHA preflights remain strict prerequisites.
- CI checks Python syntax, embedded Ruby syntax, no-write markers, and the existing pure-Ruby Rack tests. CI does **not** execute the owner sandbox.
- Production safety remains blocked: CSP browser compatibility; persistent Rails middleware integration and static-file serving through the real reverse proxy; JPEG/PNG/GIF multipart+decoder tests, malformed and timeout cases; supported Ruby/Rails update, media backup/rollback and deployment acceptance.

## Status

Draft PR only. Runtime loopback validation pending owner-local execution. No production, QA port 3002, source worktree or Docker resources modified.
