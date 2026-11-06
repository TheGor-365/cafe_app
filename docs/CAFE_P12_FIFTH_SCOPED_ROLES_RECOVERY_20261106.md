# Cafe P1.2 — fifth PostgreSQL scoped roles recovery after reboot

Date: 2026-11-06. Review-only; do not merge, do not overwrite local working tree.

## Owner confirmed

Original localhost:3001 and patched QA:3002 HTTP 200, restored sandbox PG3 and fourth PG4 independent from SHA256 backup; restored four private historical Rails candidates and independent read-only verification PASS. Fifth existing SCRAM PostgreSQL16 was restarted exactly once after tmpfs reboot under private exclusive marker; owner stdout confirmed five independent cluster identifiers, strict SCRAM, zero public tables and zero additional LOGIN roles; preserved original Docker and media. Owner next action before roles: independently run fifth reboot --verify-empty (must not run after roles are added).

## Why not reuse Nov-5 scoped roles

Fifth PGDATA is tmpfs, so old role DDL and any old role password were lost with reboot; old one-shot role marker/old helper is not safe to retry. Re-create only the two canonical least-privilege roles in the new fifth cluster via a new exclusive marker and new private password. Preserve older 20261105 role artifacts, no overwrites.

## Implementation

- --check READ-ONLY: verifies exact SHA-pinned fifth reboot helper Git blob b9bd1df811d61e0e177e4c2f16f4d680248bb206, owner-only reboot marker, source 4 PG, private media/fourth read-only E2E and fifth internal-only container + secret. Repeats SCRAM HBA and five PG IDs, empty tables/sequences, no scoped role/default ACL, no other login roles. Requires absence of new role recovery directory/marker. Uses reviewed role SQL Git blob 6c033b139ec9921c00c39e691010a44b55bf49bf.

- --provision SEPARATE ONE-SHOT: after preflight PASS, generates 0700 owner-private dir and 0600 random app password file, then exclusive 0600 marker BEFORE SQL. Substitutes exactly one CI-only password in canonical SQL with fresh cryptographic random URL-safe password, passes SQL to psql over docker exec -i stdin in the exact pre-existing fifth PG as postgres. SQL is an atomic transaction confined to fifth. Never print or put credentials in Docker argv/env, Git or CI. Failure is fail-closed: DO NOT retry, preserve all artifacts.

- --verify READ-ONLY: checks marker/fifth PG identity and password hash, protected 4 PG and media/HTTP E2E, owner/app role attributes, exact privileges, defaults for new tables/sequences, zero data tables and positive/negative real SCRAM app TCP login. No local negative DDL write test; GitHub disposable CI of PR53 tested DDL denial.

## Target role policy

cafe_synth_owner: NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; owner of public schema for future reviewed Rails DDL.

cafe_synth_app: LOGIN NOINHERIT, no CREATE privilege on schema or database, no TEMP, no other DB access or membership, only CONNECT cafe_synthetic and USAGE public; owner default grants app SELECT/INSERT/UPDATE/DELETE on new tables and USAGE/SELECT on sequences.

## Evidence and next gates

Original SQL in PR #53 ran against a disposable PostgreSQL; not proof of current local Docker. New CI asserts static scopes and mocks exclusive marker-first SQL, stdin-only secret and login. Owner independently runs --check, then separately approved --provision once, then --verify. Reboot empties fifth tmpfs again; old markers stay for forensics. The earlier 20261105 schema read-only helper imports old role helper/old role password and may be incompatible after recovery: create a new reviewed schema preflight before any fifth-only Rails schema DDL. No QA user/media import, no production/QA SQL writes, no branch checkout or merge.
