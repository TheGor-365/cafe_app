# Cafe security QA — fourth-PostgreSQL read-only Rails E2E bootstrap, 2026-11-05

## Owner-confirmed baseline

The owner executed the SHA-pinned fourth database --verify-running locally after successful --restore. PASS confirmed FOURTH PRIVATE POSTGRES DISTINCT CLUSTER / CATALOG, QA 20 products and 2 users with product 21 absent, a private internal-only Docker network, no host-published ports, 3 previous PG identities unchanged and original production 3001 / QA 3002 still HTTP 200. The source private 10 media SHA256 was preserved. Fourth database uses tmpfs and is not a permanent backup. Its auth is POSTGRES_HOST_AUTH_METHOD=trust, meaning a container admitted to the network can connect without a password; keep the network isolated.

The previous mountpoint-safe read-only private Rails sandbox PASS includes real HTTP HTML/CSP Report-Only/nosniff/referrer, JPEG GET/HEAD checksum, blocked POST 405, CarrierWave 2.2.7 pre-cache guard, ImageMagick env and default SQL read-only.

## Goal and non-goals

Create a wholly NEW Rails candidate attached solely to the 4th private PostgreSQL, with a fresh copied 10-media tree, and validate readonly HTTP/PG integration. No account registration, upload, login, admin POST, public port, media mutation, source tree changes, migrations, queue workers, external webhook or live release. An interactive writable Rails candidate will be designed in a separate stage with explicit least-privilege/access control and privacy plan, not created here.

## Script

scripts/cafe_private_e2e_web_readonly.py imports owner-pinned verified helpers by their Git blobs and fails closed if changed.

- --check: READ-ONLY. Verifies original preflight, all 3 prior PGs, owner media, previous reviewed header policy and running HTTP web, then 4th database dump SHA/identities/catalog and network sole member. Rejects any existing new name/directory.
- --create: separate explicit action. Copies 10 verified private media files to exclusive new mode-0700 staging directory, exact SHA verifies; copies the reviewed combined Rack header config.ru into new file. Docker create ONLY: new container cafe-upload-security-e2e-web-readonly-20261105 on the independent internal-only e2e network, read-only rootfs, 1000:1000 user, cap drop ALL, no-new-privileges, no host ports, no restart, 1GiB memory and 256 pids; only the new media directory writable. All inherited /app/source/containers and patched bundle mounts remain read-only and unchanged. Env copied only from the safe reviewed source, with exactly one override: DATABASE_URL=postgresql://postgres@cafe-e2e-postgres:5432/cafe; retains PGOPTIONS=-c default_transaction_read_only=on and 9 MAGICK caps. No extra nonexistent mount: new reviewed config.ru overlays the already-existing /app/config.ru.
- --verify-created: READ-ONLY. Inspect new container, mounts, network membership (only 4th postgres and new Rails), 4th PG, media SHA, source and runtime resource caps. Requires new state=created.
- --smoke: separately start ONLY new container if created. Ruby rails runner executes inside that private container and verifies PostgreSQL system identifier matches 4th PG (not one of previous three), DB read-only, 20 products, CarrierWave and ImageMagick env. Real internal TCP GET signup/info HTML with CSP Report-Only, referrer, nosniff; JPEG GET/HEAD and exact SHA; POST returns 405. Original 3 PGs/host 3001/3002/media revalidated. No published port.
- Errors intentionally redact paths, logs, personal data, credentials and DB rows; failures are fail-closed, do not retry blindly and do not delete partial stage.

## Security gates

1. The 4th PostgreSQL is **not protected by network-only trust against a malicious Docker administrator**. Docker socket / root privilege is a trusted boundary. Before connecting any external access or allowing mutations, replace trust with authenticated scoped roles, and use synthetic test accounts/fixtures where appropriate. All E2E Rails connectivity to 4th PG here is readonly and HTTP denies all POST.
2. Neither PR #47 nor #48 nor this PR changes original services. No proxy to 3001/3002 or external internet. GitHub CI contains **only synthetic fixtures**.
3. No original private PostgreSQL snapshot, exported SQL, private image, user data, emails, tokens, passwords, environment values or absolute paths must enter GitHub, public Drive or chat.
4. Existing broken OCI mount candidate is preserved as evidence. All existing media and backup objects are preserved.
5. This task does NOT cover public readiness, dependency modernization, real browser interaction, Rails mutations or actual multipart test. It is an isolated read-only connectivity gate.

## CI and next action

GitHub Actions checks Python, Ruby smoke syntax, exact source/helper pins, no source/PG live-mutating commands, synthetic existing-file Rack OCI mount and inspect. It cannot boot the owner's private Rails image or use private snapshots.

Status: Draft, no owner web object created. First action: fetch SHA-pinned helper into new local private filename and run --check only. Next creation, verify-created and smoke are separate owner-local actions.

## Incident checkpoint: owner --create returned internal audit failed

Owner executed the original SHA-pinned `scripts/cafe_private_e2e_web_readonly.py` (Git blob `c9d76b1858617d3f2407a43dbde613d06ef6d0f9`) with `--create` after its read-only preflight PASS. The command repeated original QA and fourth-PG security checks, then printed `E2E FOURTH WEB BLOCKED: internal audit failed`, with no success marker.

Source-level root cause is proven: `create()` obtains the Docker candidate configuration as local variable `source` from `preflight`, then inside the copying loop reuses `as source` for a media file reader. After copying and writing config.ru, `source_environment(source)` attempts to treat the closed stream as a Docker inspect dictionary, causing a TypeError that the script intentionally redacts. This is a deterministic Python variable-shadowing bug; no Rails application failure is established. It is **likely but not yet verified on the owner machine** that the new private stage and its 10 media/config.ru were created while the new web Docker object was not.

### Safe repair

Updated helper now:
- fixes `as source` to `as reader` and extracts creation from the reviewed inspect dict into `create_container_from_stage`;
- exposes `--inspect-partial`: strictly read-only, repeats original 3001/3002/PG/media checks, requires fourth network membership exactly {fourth PG}, verifies intended E2E web container **absent**, private staging directory owner and restrictive modes, reviewed config.ru and SHA256 of exactly 10 copied private files; only aggregate PASS markers are emitted;
- exposes `--resume-create`: requires the successful partial-stage audit, repeats original isolation preflight, then creates ONLY the missing E2E web Docker object using existing private staged assets. It does NOT recopy media, overwrite source, restart existing containers, create a network, write to DB or remove old objects; new web remains **stopped**.
- CI includes an actual Python regression using ten synthetic fake JPEG payloads and mocks to confirm that `create()` passes the original Docker inspect dictionary to `create_container_from_stage`, plus AST checks preventing file creation/Docker mutation in partial inspection and copy/restart in resume.

**Do NOT repeat the old local `--create`**, delete the old partial stage, run `--smoke` or switch any web app. Owner first fetches the UPDATED SHA-pinned GitHub helper into a *different* local filename and runs **`--inspect-partial` only**. If it fails, read-only diagnosis is required. If successful, the separate `--resume-create` action is eligible; following that, `--verify-created` and `--smoke` are still separate gates. PostgreSQL #4 and the owner source are protected throughout.

Status: patch CI PASS, owner partial-stage audit pending.
