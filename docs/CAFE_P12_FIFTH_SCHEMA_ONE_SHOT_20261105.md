# Cafe P1.2 — fifth-only Rails schema loader (Draft; no owner writes)

Date: 2026-11-05.

## Owner-confirmed prerequisite

Owner executed SHA-pinned P1.1 v6 from Draft PR #56, commit
f744b999d49ee6956d964bbf0c78bb46590c9487,
script blob 13ac9907b94d4beafe5b0be4707e197b4b24069a.
The stdout reports:

- Four original PostgreSQL clusters, protected media hashes and HTTP
  3001/3002 PASS.
- Fifth PostgreSQL16 SCRAM private network, owner/app ACL and empty
  public schema PASS, no Rails attachment or DDL.
- Linux-compatible QA dependency bundle, canonical read-only source PASS.
- RUBY 2.5.8 / RAILS 6.0 RUNTIME BOOT PASS.
- P1.1 RAILS RUNTIME PROBE PASS — NO DATABASE WRITES.

The visible turbo_chat terminal prompt is outside the subshell; inside
the command the user explicitly changed into cafe_app. No checkout.

## Exact targets / boundaries

Fifth Docker PostgreSQL ONLY:
  cafe-upload-security-synthetic-pg-20261105
Fifth internal Docker network ONLY:
  cafe-upload-security-synthetic-net-20261105
Fifth database ONLY:
  cafe_synthetic
PostgreSQL version:
  16, SCRAM-only, private port, no published host port
Canonical Rails source commit:
  090b9d37419fcd9f393d8b686ac0f4563ef7b613
Docker Ruby/Rails runtime:
  cafe-legacy-full:node14, Ruby 2.5.8, Rails 6.0

The only permitted source overlays are the previously checked, existing
read-only QA Gemfile, Linux Gemfile.lock and /bundle, plus a Git-blob
pinned Ruby pre/post target guard. Original local dirty source, media,
live web and four protected PostgreSQL clusters are NEVER mounted.

The Rails writer (if separately authorized) runs in one ephemeral Docker
container, with no host ports, only the fifth internal network, UID 1000,
read-only root/source/dependencies, tmpfs writable only for temporary
Rails files, no-new-privileges and dropped capabilities.

The fifth SCRAM password is mounted read-only from the already verified
private file and read inside the isolated shell. It never appears in
Docker command-line environment arguments, GitHub or logs printed by
the orchestrator. PostgreSQL session login is postgres, but PGOPTIONS
sets CURRENT_USER to NOLOGIN cafe_synth_owner; the Ruby pre-write guard
independently checks DB identity, IP, port, roles and permissions.
Residual risk: session_user postgres remains privileged, so the
isolated runner must only execute exact reviewed source and gems.

## Three modes / explicit stage gate

1. --check — READ ONLY. Re-runs pinned P1.1, verifies old four PG,
   media, 3001/3002, fifth-only network/roles/empty DB/source,
   credential file metadata and absence of one-shot attempt marker.
   This is the ONLY mode initially requested from the owner.

2. --create-schema --confirm-target cafe_synthetic — separately
   authorized later. Before Docker DDL it records an exclusive
   one-shot marker at:
   ~/.local/share/cafe_app/cafe_p12_fifth_schema_attempt_20261105.json
   It invokes only Rails db:schema:load, with independently pinned
   Ruby pre/post checks. No db:prepare, db:reset, db:drop, db:migrate,
   db:seed, restoration, accounts or original media. An interrupted
   or failed attempt is NEVER retried without separate forensics.

3. --verify-schema — READ ONLY. Independent postflight, does not call
   preflight gate expecting an empty fifth DB. Asserts 10 exact tables
   (8 app + 2 Rails metadata), 8 FKs, all canonical schema_migrations,
   owner-owned tables/sequences, CRUD ACL with application DDL denied,
   zero rows in all app tables and unchanged protected four PG/media/web.

The fifth PG database files reside on tmpfs and are disposable.
A completed schema is not a backup or a publicly deployed service.

## Evidence policy

GitHub Actions checks only Python/Ruby syntax, source constraints,
argument construction and negative-mode behavior. It has NO access
to owner's local Docker/PG. Existing Draft PR #54 independently
proved actual Rails schema and synthetic seeds in disposable GitHub CI,
but is NOT evidence of a fifth owner-local schema load.

Owner-local P1.2 --check PASS is required before any one-shot DDL
instruction. If the check fails, only inspect the blocker, do not alter
original four databases, dirty project, Docker networks or media.
