# Cafe P1.2 reboot recovery — isolated read-only inventory, 2026-11-06

## Confirmed user-local checkpoint

- After Linux reboot, main `cafe-app-db` retains PGDATA in a permanent Docker volume and site 127.0.0.1:3001 is running.
- The missing QA PG `cafe-upload-qa-pg-20261103` was reconstructed in NEW dedicated persistent volume and restored from a private SHA256-verified owner backup with 20 products, 2 historical QA users and no product ID21. The original one-shot restore hit a SQL readiness race after writing its marker, *before* importing data; separate owner SHA-pinned one-time continuation PASS and independent `--verify` PASS.
- Owner executed PR #58 `cafe_qa_http_boot_v1_20261106.py --start` and got `CAFE QA 3002 MENU/SIGNUP/MULTIPART HTTP 200 PASS`, `CAFE QA PATCHED CARRIERWAVE 2.2.7 PASS`, and `CAFE 3001/3002 PG ISOLATION / RECOVERY COMPLETE PASS`.
- Original three temporary PostgreSQL clusters (`sandbox`, fourth E2E and fifth synthetic) used tmpfs PGDATA, stopped at reboot. Their old cluster identifiers/third/fourth copied QA data/fifth SCRAM roles are **no longer verified**. Old `P1.2 --check` failed internal safety audit after reboot; do not repeat schema writer or start with stale assumptions.

## This draft PR

`scripts/cafe_p12_reboot_inventory_20261106.py --check` is READ ONLY:

- SHA-pins exact reviewed owner P1.2 schema script and SHA-pinned owner QA resume/HTTP boot helpers.
- Rechecks SHA256 of pre-existing private QA dump without printing archive names or contents.
- Verifies both protected live/QA PostgreSQL clusters run with different persistent Docker volumes, unique cluster identifiers, different networks and HTTP200 at 3001/3002.
- Inspects the existing three historical test PG containers and internal networks, validates tmpfs PGDATA without port bindings, the fifth private read-only SCRAM credential mount (never reads or logs credentials), and outputs sanitized names/states only.
- Inspects historical private sandbox/headers/E2E Rails candidates, verifies expected image and no host-published ports or production/QA network exposure.
- Requires absence of a prior one-shot P1.2 schema marker; if marker exists, stop.
- **No Docker start/stop/create, database connection to stopped temporary clusters, pg_restore, migrations, schema load, mark/role changes, deletions, or Git checkout**. The CI only uses mocked Docker states and static checks. No private assets shipped to GitHub.

## Next after owner --check PASS

Prepare a **separate** reviewed one-shot script to restore previously created sandbox/fourth from the SHA-verified owner-only private QA snapshot *without* altering original live/QA media, their PostgreSQL volumes or the owner checkout. Restore their dependents only after isolated PG ready. Reinitialize fifth SCRAM test PG as a fresh empty cluster only after proof of original four distinct PG identities; reinstall scoped synthetic owner/app roles through a separately reviewed gate; then rerun updated PR #57 `--check`. `--create-schema` requires separate explicit scope and PASS, never bundled with diagnostics.

Stop on unexpected Docker network membership, nonempty temporary DB, missing private backup or opaque SQL failure. Keep previous partial recovery markers and all old Docker objects. Do not repeatedly restart test PGs blindly.

## Longer term
Reduce the runtime to production and QA Compose services with persistent volumes and managed dependencies; keep third/fourth/fifth test clusters disposable and off by default, and make reinitialization reproducible. Preserve the dirty local branch, original media and protected backups until reconciled. No cleanup or deployment authorized.
