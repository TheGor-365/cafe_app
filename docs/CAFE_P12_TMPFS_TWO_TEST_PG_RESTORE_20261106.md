# Cafe P1.2 — restoring two existing private tmpfs PostgreSQL test clusters (2026-11-06)

## Confirmed owner-local evidence

Owner ran SHA-pinned PR #59 `cafe_p12_reboot_inventory_v1_20261106.py --check` and got all PASS:
- Independent persistent production and QA PostgreSQL with protected HTTP 3001 and 3002 PASS.
- Verified private QA archive SHA256 PASS.
- Existing sandbox (#3), fourth E2E (#4) and fifth synthetic SCRAM PostgreSQL all `exited` after reboot and have **tmpfs-only** PGDATA.
- Existing sandbox Rails, precache Rails, headers candidate and fourth private read-only Rails all `exited`; no host ports.
- No test PG was started, restored, or written by inventory.

## Scope

`scripts/cafe_p12_existing_tmpfs_pg_restore_20261106.py` uses the exact installed PR #59 SHA-pinned owner inventory `af125038530314febacd35a59d5d213a85f8f742`.

- `--check` (READ ONLY): revalidates owner archive, original production/QA PG and HTTP, exact stopped PG3 and PG4 metadata (Postgres16, tmpfs-only data, dedicated internal networks, host `trust` **only for internal historical test clusters**, no host ports/mounts), confirms fifth stopped and its Rails schema marker absent, confirms new test restore marker absent.
- `--restore-clones` (ONE SHOT, separately owner-authorized): reruns check; writes a new exclusive private 0600 attempt marker *before* any Docker/SQL change; starts **only two existing** sandbox/fourth PostgreSQL containers; waits for real SQL on database `cafe`; verifies strictly empty catalog, exact distinct PG cluster system IDs; imports private SHA256-verified QA `qa_cafe.dump` once per test PG via `pg_restore --single-transaction --exit-on-error --no-owner --no-acl`; validates 20 products, 2 preexisting QA users, deleted product id 21 absent, and production/QA unchanged after each import.
- `--verify-clones` (READ ONLY): independently checks two PGs, SHA/persistent live/QA baseline, unique PG IDs, marker and expected data counts. Does not touch fifth synthetic PostgreSQL.
- No new containers, networks, volumes, published ports, credentials, user accounts, schema changes on production/QA, code checkout changes, deleting or resetting anything, or copying/uploading private data to GitHub.
- If a restoration fails or times out after marker, do not retry same command, delete marker, recreate a PG or wipe it. Inspect partial state and prepare a separately reviewed scoped continuation.

## Why these two are separate from the fifth

Sandbox and fourth originally held two historical QA users and used internal-network PostgreSQL `trust`; they are suitable only for read-only, isolated security QA. The fifth synthetic PostgreSQL must have a **fresh** SCRAM-only cluster and least-privilege roles with no QA users; no data from the private QA dump belongs in the fifth. Once PG3/PG4 restored, restart only their approved original read-only Rails candidates after independent review; then recreate fifth SCRAM and scoped owner/app roles using a separate marker-aware script. **Never run PR #57 `--create-schema` before fresh `--check` PASS and separate explicit authorization.**

## Owner operation

Fetch exact branch SHA/source blob into a *new private path* without checkout and run `--check` only. CI mocks can verify script assembly/negative cases but cannot confirm owner's Docker state. After owner PASS, separately run `--restore-clones` once, then `--verify-clones`.
