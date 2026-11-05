# Cafe P1.1 — pinned legacy Rails runtime probe, 2026-11-05

## Confirmed owner boundary

Owner ran P1 local target read-only helper, blob `501914861518530bed0d18c8f1ca08550fe65e4d`, on existing dirty `feature/cafe-integration-local-20261101` and reported:

- `P1 CANONICAL RAILS BLOBS + ORIGINAL FOUR PG/MEDIA AUDIT PASS`
- `P1 FIFTH CLUSTER RUNNING / INTERNAL / NO PORT / EMPTY SCHEMA PASS`
- `P1 LEGACY RAILS IMAGE / SOURCE QA INSPECTION PASS`
- `P1 LOCAL TARGET PREFLIGHT READ-ONLY PASS — NO WRITES`.

The fifth PostgreSQL still has **zero application tables**; no fixtures, Rails attachment or local DDL.

## This change

A **non-writing** runtime compatibility probe is needed before one-shot schema load because GitHub's canonical Rails Gemfile.lock and owner's dirty local installation are different trust surfaces. The new `scripts/cafe_synthetic_schema_runtime_probe.py --probe`:

1. Re-runs the exact SHA-pinned P1 local target gate (rechecks empty fifth DB, roles/SCRAM, isolated four original DB/media, HTTP 3001/3002).
2. Extracts tracked files from the exact reviewed Git commit `090b9d37419fcd9f393d8b686ac0f4563ef7b613` into an automatically cleaned private temporary directory, refusing tar symlinks and unsafe paths; verifies canonical schema, seeds and Gemfile.lock blob hashes.
3. Starts one disposable Docker container with the already present `cafe-legacy-full:node14`, `--network=none`, `--rm`, `--read-only`, user 1000, dropped capabilities, no host ports, no DB credentials, no private media. Shared gem cache mounts may be **read-only volumes only**, never protected application source or uploads.
4. Runs `ruby -v && bundle exec rails -v` only, requires Ruby 2.5.8 / Rails 6.0; cleans the local source snapshot. Does **not** run `db:schema:load`, SQL, migrations, seed, tests against any database, or create persistent Docker objects.

GitHub Actions checks source and interface only: CI cannot prove the owner's Docker image actually boots. This is a staging probe, **not** the owner-local fifth DB schema writer.

## Outcomes

- `P1.1 RAILS RUNTIME PROBE PASS — NO DATABASE WRITES`: only permits designing/reviewing the separate P1 schema writer.
- `CAFE P1.1 RAILS PROBE STOP`: keep fifth DB empty; inspect dependency/runner mismatch without modifying original working tree, four PostgreSQL clusters or live/QA ports.
- Partial output or ambiguity: STOP. No retry of a future one-shot writer until independent inspection.

## Subsequent P1 schema writer design requirements

Separate PR, exact target Docker network/cluster identity and previously verified SCRAM roles; ephemeral Rails runner in the isolated fifth network with canonical read-only source; private credential transport without Docker env/argv leakage; NO superuser DDL until target preflight. DDL using `SET ROLE cafe_synth_owner` only; default app role must never receive DDL. Explicit `--create-schema` mode with stop-on-nonempty, no second invocation after failure, and independent `--verify-schema` mode that checks exactly eight app tables + two Rails metadata tables, eight FKs, owner/sequence ownership, all expected migration versions, app CRUD ACL, zero users and zero seeds. Verify old PGs/media/HTTP 3001/3002 unchanged. No PR merge, public deploy or paid resource.
