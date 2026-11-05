# Gor's Coffee — restore missing QA PostgreSQL after reboot (2026-11-06)

## Observed evidence from owner local terminal

- Primary `cafe-app-db` is running PostgreSQL16 with a persistent Docker volume for PGDATA.
- Primary `cafe-app-local-3001-web` is running; owner screenshot shows working home page on 127.0.0.1:3001.
- The intended QA PostgreSQL container `cafe-upload-qa-pg-20261103` is **missing**.
- `cafe-app-uploads-qa-db-20261103` is a Rails web container (image `cafe-legacy-full:node14`), NOT PostgreSQL.
- Patched QA Rails and proxy are preserved stopped; patched Rails network is only `cafe-upload-qa-net-20261103` and its existing DATABASE_URL is `postgresql://postgres@cafe-app-db:5432/cafe`.
- QA private network is `--internal`, and has no running endpoints; main PG lives only on the separate `cafe-app-private` network.
- Verified local backup under the preexisting private snapshot directory: manifest `verified=true`, 20 QA products, test product id21 absent, exact SHA256 of `qa_cafe.dump` matches.
- Sandbox, fourth E2E and fifth synthetic test PG used tmpfs for PGDATA and all stopped on reboot: their original cluster IDs/data and fifth scoped DB roles cannot be assumed available.

## What the script does

`scripts/cafe_qa_persistent_pg_recovery_20261106.py` supports:

1. `--check`: READ ONLY original live PG volume identity and production HTTP 3001, existing patched QA network, URL/alias, proxy port mapping, backup SHA, available old QA container name and new volume name. Initially ask owner to run **only this**.
2. `--create`: separately authorized. Creates only a NEW named persistent QA Docker volume `cafe-qa-pgdata-persistent-20261106` and the previously MISSING container `cafe-upload-qa-pg-20261103`. Image `postgres:16`, only `cafe-upload-qa-net-20261103`, private alias `cafe-app-db` that resolves only inside QA network, no host port, read-only root filesystem with private writable PGDATA volume and tmpfs socket/tmp, 768MiB cap, restart=no. No production volume or network.
3. `--verify-created`: read-only confirms the new container remains stopped and all Docker mount/ACL/network metadata.
4. `--restore`: one-shot, writes a new private attempt marker BEFORE starting only this new QA PG; waits for readiness; streams previously SHA-verified private archive through `pg_restore --single-transaction --exit-on-error --no-owner --no-acl` into only `cafe-upload-qa-pg-20261103` on its own QA Docker network. On failure preserve marker, new volume and container, DO NOT retry blindly.
5. `--verify-running`: read-only verifies PG cluster differs from production; 20 products, zero product id21, 2 test users, Rails schema present, production PostgreSQL unchanged and home page still HTTP 200.

The original patched Rails `cafe-app-patched-qa-candidate-20261104` and existing loopback-only proxy `cafe-upload-qa-proxy-patched-20261104` are not started by this script; after restore PASS they are started in order in a separate owner command, and verified at 127.0.0.1:3002.

## Security caveat

The existing legacy QA Rails configuration has **no DB password** in its DATABASE_URL. To preserve compatibility, this isolated QA database uses PostgreSQL `POSTGRES_HOST_AUTH_METHOD=trust` on its dedicated Docker **internal** network and NO host-published port; it is **NOT a production-grade auth configuration**. No access is granted to production's network or volumes. Next architecture track is a simpler persistent Compose infrastructure with credentials and automatic QA dependency ordering, after the current recovery and P1.2 gates.

This backup contains two historical QA user rows. Keep the original private dump and QA media restricted; do NOT publish, push to GitHub, share with external AI, or attach to public network.

No user-local restores occurred during GitHub PR creation/CI. P1.2 synthetic schema writer remains blocked after reboot until all independent test clusters are reconstructed and reviewed; never re-use prior P1 PASS as current.

## Policy

No `docker compose down -v`, DB reset/drop, no existing volume cleanup, no branch checkout, no PR merge, no restart/replacement of original production PostgreSQL and no secrets printed. After a failed create/restore keep everything for forensic inspection.
