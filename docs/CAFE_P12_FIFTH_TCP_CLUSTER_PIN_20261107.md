# P1.2 fifth PostgreSQL — TCP cluster ID pinned schema loader (07.11.2026)

## Evidence (owner Linux)

- Prior fifth SCRAM scoped roles `--verify`: PASS after owner-only one-shot provisioning (do not repeat).
- First schema loader `--check`: offline fake-secret Rails mount probe PASS; Ruby read-only fifth TCP preflight STOP. No schema attempt marker, schema, fixtures or protected database writes.
- Standalone fifth TCP guard: `PHASE=ruby_guard`, `CATEGORY=guard_server_ip`, no writes.
- Independent socket/DNS test: `SOCKET_KIND=DIFFERENT_IPV4`, `DNS_KIND=EXPECTED_ONLY`, `SOCKET_IN_DNS=NO`. No data change.
- Independent TCP `pg_control_system()` proof: `TCP_CLUSTER=MATCH`, PostgreSQL16, fifth database, restored owner role PASS. **Same cluster is independently proven**; exact difference between socket IPv4 and Docker endpoint still not attributed to any specific network translation implementation.

## Corrective design

The original `qa/security/cafe_fifth_schema_target_guard.rb` rejects every difference between `inet_server_addr()` and the container's Docker-inspect endpoint. Preserve the original for audit. New, independently versioned:

- `qa/security/cafe_fifth_schema_cluster_guard_20261107.rb`
- `scripts/cafe_fifth_schema_cluster_scoped_20261107.py`

New Ruby guard keeps the previously reviewed hostname, database, TCP port, PostgreSQL 16, `RAILS_ENV=test`, source, SCRAM postgres session/owner `cafe_synth_owner`, scoped application ACL, schema empty, migration and zero-data checks. It additionally validates that Docker's fifth-only hostname DNS resolves **exclusively** to the expected Docker inspect IPv4, that `inet_server_addr()` is an IPv4, and that a session-limited privileged `pg_control_system().system_identifier` matches the pinned identifier of the original fifth container. It restores the scoped owner via `SET ROLE cafe_synth_owner` in an `ensure` block before any application checks. A mismatched cluster or unexpected DNS fails closed, even if PostgreSQL user/database names coincide. No blanket bypass of the IP identity gate.

New Python helper keeps the original fifth-only Docker/network/PG16/SCRAM/privilege/source/secret constraints, source Git SHA `090b9d37419fcd9f393d8b686ac0f4563ef7b613`, protected four and ports 3001/3002, actual Rails 6.0 runtime and no-network fake secret probe. The original one-shot marker path `cafe_p12_fifth_schema_attempt_20261106.json` stays unchanged, checked absent before `--check`; old marker is also checked absent. Private owner-only Ruby guard is separately SHA-pinned; no owner dirty checkout mutation or Git fetch required.

## Status and next gates

1. GitHub CI: static/mock/negative only, not an owner Linux DB test. Review current PR #66 run separately.
2. Owner must download exact immutable new Python helper and Ruby guard into **distinct private 0600 filenames**, verify both Git blobs, execute **only `python3 -B ... --check`**.
3. If owner read-only `--check` PASS, examine actual result and protected state before any separately authorized one-shot `--create-schema --confirm-target cafe_synthetic`; must never retry an ambiguous schema writer or role `--provision`.
4. After possible schema load, independent `--verify-schema` (not the pre-schema roles `--verify`), then synthetic fifth-only fixtures, isolated writable E2E and eventual integration/release.

No changes to original protected 4 PostgreSQL clusters, source dirty branch, existing media, uploads, volumes, local running Rails web apps or future payments/deploy have been performed from GitHub CI.

References: [PG16 SET ROLE](https://www.postgresql.org/docs/16/sql-set-role.html) and [PG16 pg_control_system()](https://www.postgresql.org/docs/16/functions-info.html).
