# Cafe QA 2026-11-06: verified boot of recovered local 3002

## Confirmed owner data
- Owner ran `cafe_qa_persistent_resume_v1_20261106.py --resume-empty` and received `QA VERIFIED BACKUP RESTORED TO PERSISTENT PG PASS`, 20 products, 2 users, ID21 absent, primary 3001 not changed.
- Owner independently ran `--verify` and received `QA POST-RESUME INDEPENDENT VERIFY PASS`.
- The original QA Rails `cafe-app-patched-qa-candidate-20261104` and TCP proxy `cafe-upload-qa-proxy-patched-20261104` remain existing stopped containers.
- New persistent PG container `cafe-upload-qa-pg-20261103` and its volume remain running; QA network `cafe-upload-qa-net-20261103` is internal. Original PostgreSQL is on `cafe-app-private` only.

## Safe operator action
`scripts/cafe_qa_existing_http_boot_20261106.py` is SHA-pinned via Git fetch into a new owner private script path, not run out of a dirty checkout.

- `--check`: READ-ONLY verifies SHA-pinned owner QA resume/restore helpers; both markers, private dump SHA, QA persistent PG with distinct system ID, 20 products/2 test users and protected production 3001; existing Rails and proxy identities, read-only mounts, Docker networks, localhost-only proxy port mapping, Rails QA database alias pointing **only to the private QA PG**.
- `--start`: repeats preflight and runs only `docker start cafe-app-patched-qa-candidate-20261104` and `docker start cafe-upload-qa-proxy-patched-20261104` if they aren't already running; waits for private QA GET /menu HTTP200; independently verifies /users/sign_up multipart/avatar form, CarrierWave 2.2.7, production 3001 and distinct database identities.
- `--verify`: read-only independent HTML/DB/Bundle check once running. Failed start leaves preserved Docker objects; no automatic cleanups or retries.

No Docker create/remove/restart/compose/down, host-wide container starts, migrations, SQL writes, source changes, user uploads, PR merge, or production port modification. A no-op on already-running QA services.

## CI and limitations
GitHub Actions simulates only the exact two `docker start` calls and safe idempotency, with static guard. No GitHub access to the owner's Docker daemon. Local execution output is required for acceptance. Previous fifth synthetic PG `tmpfs` lost after reboot; P1.2 cannot advance with stale cluster IDs/roles; do not use old schema loader write action.

## Next
When owner local QA HTTP 3002 PASS: resume isolated P1.2 recovery plan; improve shared persistent Compose infra only after protecting existing production volume, QA volume and private media. All prior unrelated Docker apps are out of scope.
