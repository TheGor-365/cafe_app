# Cafe P1.2 schema loader after fifth SCRAM scoped role recovery — 2026-11-06

**Branch:** feature/cafe-p12-fifth-schema-scoped-20261106 (Draft, based on PR #63 a69c18b). Separate from UI PR #65 and handoff PR #64.

## Root cause and guarded change

The 05.11 P1.1 runtime probe called an older fifth-role gate expecting zero LOGIN roles. The fifth cluster was recreated after a tmpfs reboot and, on 06.11, both scoped roles were successfully restored by the owner's one-shot PR #63 procedure. Blindly running the old 05.11 schema helper would fail that old gate or refer to the wrong pre-reboot role state.

This branch modifies **only** `scripts/cafe_fifth_schema_one_shot.py` and a dedicated CI workflow. Its new preflight uses exact pinned 06.11 owner-private role helper Git blob `a02f23a9cd2c982309a1649ea0b314618f9da94a` and requires `roles.verify()` (only before schema DDL), including app SCRAM positive/negative, ACL, fifth distinct cluster, protected four and role recovery marker. Reuses the exact reviewed Ruby fifth SQL guard blob `e5dae1c3b740acf3298b5baf12747f69d4d2a721`. It skips the obsolete `probe.probe()` but still checks QA dependency mounts and performs a real offline Rails-version probe in a disposable no-network container with a fake secret. Before schema DDL, another disposable network-only preflight performs SELECT-only Ruby SQL checks with the fifth-specific network/role.

New **independent** one-shot schema attempt marker `~/.local/share/cafe_app/cafe_p12_fifth_schema_attempt_20261106.json` is created exclusively (O_EXCL, O_NOFOLLOW) before any writer SQL. Both old 05.11 schema marker and new marker must be absent to pass preflight. Never remove or reuse any attempt marker to force a rerun. The later postflight `--verify-schema` checks recovery marker identity and newly loaded 10 tables, 8 FKs/sequences, owner/role ACL, migration versions and zero data before fixtures.

## Exact boundary

Fifth target ONLY: `cafe-upload-security-synthetic-pg-20261105`, internal network `cafe-upload-security-synthetic-net-20261105`, database `cafe_synthetic`, PostgreSQL16 SCRAM. Canonical reviewed Rails snapshot SHA `090b9d37419fcd9f393d8b686ac0f4563ef7b613`; isolated legacy Ruby2.5/Rails6 and verified read-only QA gems. Original PostgreSQL 3001/3002, PG3/PG4, uploads and owner dirty Git tree are excluded.

## Acceptance and limits

1. **Current blocker:** obtain the independent owner read-only 06.11 scoped roles `--verify` PASS. The in-script `--provision` self-check already passed but is not a substitute. Never run `--provision` again.
2. GitHub CI on this exact branch must pass its static/mock gates. CI does **not** touch owner's fifth PG.
3. Only after both PASS, review the new script's exact SHA, install a new owner-private 0600 copy without modifying the dirty checkout, and run `--check` READ ONLY relative to all protected databases. Inspect stdout and the unchanged original four plus 3001/3002. Stop on any mismatch.
4. `--create-schema --confirm-target cafe_synthetic` is a **future separately authorized one-shot action**, not authorized by this Draft PR; no automatic invocation. A failed/ambiguous result is not retried.
5. After a future successful fifth-only schema write, use **this script** `--verify-schema`; do not run the pre-schema roles helper `--verify` or old `--verify-empty` (those demand zero tables). Fixtures and writable E2E are separate future gates.

No PR merge, DB/seed operations, Docker restart, volume deletion, original media publication or production deployment was executed while preparing this branch.
