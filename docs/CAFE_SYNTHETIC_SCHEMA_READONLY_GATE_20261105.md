# Cafe fifth synthetic PG — schema and fictional fixtures read-only gate

Date: 2026-11-05. This document is a QA plan, NOT permission for local schema writes.

## Owner-verified state
- Fifth PostgreSQL16 in independent Docker internal network, five distinct cluster IDs, SCRAM host authentication and no published port.
- Owner ran v2 role gate \`--provision\` and separate \`--verify\`: role ACL and valid/invalid login PASS.
- Fifth database still has **zero public application tables**, and Rails has NOT attached to it. Live HTTP 3001 and QA 3002 plus old four DB clusters and media remain untouched.

## Canonical GitHub objects (not the dirty working tree)
- \`db/schema.rb\`: Git blob \`2506954d1ea3e6368eb219956863b2acb91441c8\`, Rails schema version \`2026_11_02_000100\`, 8 app tables and 8 foreign keys.
- \`db/seeds.rb\`: Git blob \`dae2eed43c78ff79a14e3bf3e83d59a649803cd4\`, fictional 8 categories / 20 catalogue products / 6 configurable beverages and their options, **no users**. Only permitted in Rails development/test.
- \`db/migrate/20261102000100_create_cafe_drink_options.rb\`: Git blob \`1d0ebdd9f4d7b5d70fb13868da97f76dd722f65e\`.
- Schema includes Devise \`users\` with \`encrypted_password\` column; this does NOT mean it contains real or even synthetic users. Tables will start empty.

## New read-only owner helper
- \`scripts/cafe_synthetic_schema_readonly_gate.py\`, \`--check\` only: reads the above exact Git blobs from a SHA-fetched remote ref; imports the SHA256-pinned v2 role helper and repeats its real-only READ audits (five PGs, ACL/SCRAM, user role authentication, and zero public tables). No Rails invocation, SQL DDL/DML, Docker changes or local branch checkout.
- Any mismatch blocks: exact blob contents, schema version/table names/FKs, dev/test-only seed guard, role helper checksum/permission.
- The script does not execute migrations or seeds, or import data from any owner DB.

## GitHub CI (disposable only)
\`.github/workflows/coffee-synthetic-schema-seeds-ci.yml\` uses Ruby 2.5.8 and a throwaway PostgreSQL16 with synthetic roles. The intention is to exercise actual Rails \`db:schema:load\` under a scoped owner role, then Rails \`db:seed\` under a non-superuser scoped app role, assert exactly 8 tables owned by schema owner, 8 categories, 20 products, 18 variants, 30 modifier options, and zero users. It also proves app-role DDL denial.
Only successful completed CI at the exact commit may support an assertion that this full lifecycle works. Tests run in GitHub ephemeral workers; there is **no connection to user's fifth database**.

## Next owner steps
1. After GitHub CI PASS and exact branch/blob SHA pinning, run the new helper \`--check\` only. No credentials are sent to GitHub.
2. Build a *separate* reviewed schema loader with no host port and deterministic target checks; no unchecked \`rails db:prepare\`, \`db:reset\`, \`db:drop\`, \`db:seed\` against existing local apps or databases. Schema loader must use fifth internal network and owner role, with privilege reduction, schema emptiness checks, and post-apply checks before/after.
3. Only after successful schema load on isolated fifth PostgreSQL, create synthetic catalogue fixtures and verify exact counts and 0 users. Then create dedicated writable Rails E2E in the fifth network, separate uploads, and no external service cutover.

## Release boundary
Neither this gate nor successful CI permits public release, Rails POST enablement, using copied fourth-PG QA accounts, attaching live Rails to fifth PG, or updating/merging the owner's dirty local branch. Credential files stay private on the host.
