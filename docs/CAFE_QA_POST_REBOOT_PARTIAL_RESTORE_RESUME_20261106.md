# Cafe QA 2026-11-06 — recovery of interrupted first restore

## Owner-observed evidence
- The user executed the SHA-pinned PR #58 QA recovery v1 `--create` and `--verify-created` with PASS; these created a **new persistent QA-only Docker volume** and stopped PostgreSQL container, not the protected production database.
- On first `--restore`, initial backup/created audit passed, then `QA RESTORE ONE-SHOT ATTEMPT RECORDED`, followed by `CAFE QA RECOVERY STOP: read-only SQL inspection failed`. No `pg_restore` success was reported.
- Owner's independent immediate diagnostic: QA PG `running`, `pg_isready` accepting connections, `psql -d cafe` returns `cafe|0|f` (zero public tables, products table absent), the original marker is present.
- Based on v1 script ordering, failed SQL happens after starting PG and the original marker but **before entering the archive-import `pg_restore` block**. This is consistent with an initial Postgres init/readiness race; the exact original SQL error was suppressed, so we do not claim the exact driver error.
- The private snapshot `qa_cafe.dump` was previously independently SHA256 verified, and the production `3001` site stays in service.

## Separate one-shot empty-only continuation (new helper)

`scripts/cafe_qa_persistent_pg_resume_20261106.py`

1. `--check-resume` (read-only): loads only original v1 from private owner path and checks its exact Git blob `37ba432479f4243a725d682fa88faabf8477efb1`; uses v1 archive SHA, production PG + website, internal QA network, container volume and mount checks; requires original one-shot marker with matching backed-up archive and target. Checks new resume marker absent, distinct cluster IDs, selected database `cafe`, zero tables and all public relations/functions/types/extensions/custom schemas, zero unexpected login roles. **Do not restore unless this PASSes.**
2. `--resume-empty` (separate explicit operator action only after PASS): repeats every gate, creates a separate 0600 exclusive resume marker **BEFORE** any write; streams verified private snapshot via `docker exec -i --user postgres <exact QA PG> pg_restore --single-transaction --exit-on-error --no-owner --no-acl`. Never starts/removes/recreates a container, edits media, visits another network, changes a Git branch, or writes to production. On failure preserve both markers and all DB state; no repeat.
3. `--verify` (read-only): independent prior v1 verification: 20 QA products, user baseline 2, absent product id21, distinct QA/live cluster IDs, original HTTP 3001 still 200.

No owner-local resume operation was invoked by CI. GitHub CI mocks `pg_restore` and original QA gate; no real Docker/private archive/SQL access.

## Post-success
Only after `--verify` PASS: launch the existing patched QA Rails candidate and localhost-only QA proxy in separate approved commands, then test HTTP 3002 and DB isolation before returning to synthetic P1.2. Keep old temporary sandbox/fourth/fifth post-reboot standstill; rebuilding fifth SCRAM roles is a separate scope.

## Do not
Never retry original `--restore`; don't run `db:prepare`, `db:reset`, `docker compose down`, delete marker/volume/container, import to live PostgreSQL, export snapshot to chat or GitHub, or use synthetic fifth helper until its fresh dependencies are reestablished.
