# Cafe QA — fifth synthetic-only PostgreSQL / SCRAM phase gate — 2026-11-05

## Confirmed source and owner facts
- Owner verified Rails read-only E2E using the fourth independent PostgreSQL (20 copied QA products, 2 copied QA users). Internal HTML/JPEG headers & checksum, CarrierWave pre-cache, ImageMagick env, POST 405 and PG read-only PASS; original 3001/3002, three earlier clusters and media unaffected.
- Draft PR #51's CI security integration suite on disposable PostgreSQL PASS on exact commit ff84764be4a2ac2e39d72281b6d11130835ac26e: https://github.com/TheGor-365/cafe_app/actions/runs/41934134249.
- Fourth PostgreSQL is not appropriate for writable auth because it contains copied QA accounts and has trust host authentication. Existing read-only Rails must remain unchanged.

## This change: an entirely new empty database
- `scripts/cafe_synthetic_pg_scram_gate.py`: SHA-pinned earlier owner helper imports, checks original four PostgreSQL cluster IDs, original service/media guards, new name availability and exact image postgres:16.
- `--check`: strictly READ-ONLY, no file/Docker/SQL writes; verifies protected source and uniqueness of a fifth Docker network/database/credential folder, and sufficient staging disk.
- `--create`: separate manual action AFTER preflight. Creates a new private 0700 staging directory and random password file (host file mode 0644 under 0700 parent) for Docker's POSTGRES_PASSWORD_FILE. The file must be readable by postgres UID within the container; other host users cannot traverse the 0700 staging directory. Never print credential. Creates a new --internal network `cafe-upload-security-synthetic-net-20261105`, then a new STOPPED container `cafe-upload-security-synthetic-pg-20261105` with postgres:16. It has NO published ports, read-only root filesystem, tmpfs PGDATA and Unix socket and /tmp, restart=no, 768MiB memory / 256 pids, isolated password bind readonly. No original network/DB/volume source bind.
- PostgreSQL authentication intentionally uses `POSTGRES_HOST_AUTH_METHOD=scram-sha-256` and `POSTGRES_INITDB_ARGS=--auth-local=peer --auth-host=scram-sha-256`; the plaintext password itself never appears in container environment or GitHub. The temporary privileged postgres role exists ONLY in the new isolated instance. Do not attach an application with postgres superuser access.
- `--verify-created`: READ-ONLY, inspects exact state, network, memory/rootfs/tmpfs/mount/secret and protected owner services.
- `--bootstrap`: starts ONLY the fifth DB. Confirms readiness, empty public schema, zero extra login roles, five distinct PG system IDs, strict pg_hba host SCRAM and password_encryption SCRAM, no published port; no restoration, schema load, account creation, migrations or real data.
- `--verify-running`: READ-ONLY repetition of fifth DB + original protected baseline. All modes fail closed, no automatic retries, no container deletion/stop/restart.
- CI uses disposable synthetic-only password and Docker postgres:16, creates and boots it in a private network with read-only rootfs/tmpfs; proves correct password succeeds and wrong password fails. No user files/SQL/media submitted.

## Operational limitations / security
- The new cluster is EMPTY and ephemeral (PGDATA on tmpfs). It is not a backup. Starting the new DB is *not yet authorization* to load schema, create test users or let Rails write; authenticated application roles and least-privilege database schema loader must be designed and validated separately.
- The 0644 credential file is only safe because its parent is 0700 owned by the operator, Docker bind is read-only, and the only network member is the new PostgreSQL. It remains readable to processes INSIDE the database container. A production deployment needs a stronger secret manager/mount authorization.
- Protect source data, all four prior PGs and original Rails/QA services; do not publish new DB ports or connect it to the fourth network, and never use original user passwords, IDs or images as synthetic fixtures.
- A developer with local Docker socket/root access is trusted: container isolation does not protect from such an administrator.
- No merge to master, no public deploy or port changes authorized.

## Next safe action and acceptance
1. Fetch helper from a SHA-pinned PR commit and verify Git blob to a **new** private filename. Run `--check` only.
2. If successful, separately request `--create`, then `--verify-created`, then `--bootstrap`, `--verify-running`. Do not blindly rerun a partially failing phase.
3. After full empty-DB success, create separate schema-owner / scoped app roles and a synthetic Rails test-data/HTTP harness. Until then leave the existing fourth-DB web POST405 + PGOPTIONS read-only.
