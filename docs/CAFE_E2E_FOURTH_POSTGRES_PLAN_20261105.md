# Cafe security QA: fourth independent PostgreSQL snapshot clone — 2026-11-05

## Confirmed owner-local checkpoint

The owner ran the SHA-reviewed PR #48 mountpoint-safe QA container smoke in Linux Mint. Result:
- PRIVATE_QA_REAL_HTTP_HTML_HEADERS_PASS
- PRIVATE_QA_REAL_HTTP_JPEG_SHA_PASS
- PRIVATE_QA_POST_BLOCKED_405_PASS
- PRIVATE_QA_CARRIERWAVE_POLICY_PASS
- PRIVATE_QA_READ_ONLY_RUNTIME_HTTP_COMPLETE
- MOUNTPOINT-SAFE PRIVATE QA HEADERS/MAGICK HTTP GATE PASS
- Preflight and postflight: three PG clusters and networks isolated, ten original private media SHA256 intact, QA 3002 and local production 3001 HTTP 200.

The separate web candidate cafe-upload-security-headers-mountfix-20261104 now runs in the PRIVATE original sandbox network without host port. It shares sandbox PostgreSQL only with default_transaction_read_only=on and returns HTTP 405 for non-GET/HEAD. The earlier failed OCI candidate remains preserved. No public access or app release approved.

## This PR — new private DB only

scripts/cafe_private_e2e_postgres_clone.py adds five explicit owner-local phases:

- --check (READ-ONLY): SHA-pinned v3 preflight, currently healthy private QA web and three PostgreSQL identities, verified private backup manifest and exact qa_cafe.dump SHA256; refuses existing target DB and network names.
- --create (separately approved): creates a NEW --internal Docker network cafe-upload-security-e2e-net-20261105, and a NEW container cafe-upload-security-e2e-pg-20261105 from the reviewed postgres:16 image. It does NOT start the DB. No host port, restart policy disabled, 768MiB RAM, PID cap 256, tmpfs PGDATA/runtime socket, no original volume or backup bind mounts. No cleanup action.
- --verify-created (READ-ONLY): network/container image, isolation and source backup audit, plus original three cluster IDs and created state.
- --restore (separately approved): starts ONLY new PostgreSQL on independent Docker network, waits for readiness, streams SHA-verified private owner custom dump into it through pg_restore --single-transaction --exit-on-error --no-owner --no-acl. Never prints contents. On failure preserve the isolated container; do not blindly retry.
- --verify-running (READ-ONLY): fourth PG system identifier different from existing three, 20 products, product ID 21 absent, 2 users, at least 10 schema tables, no host-published ports, network remains dedicated. Repeat old service health checks.

Source: verified private 4 November 2026 snapshot under the owner's local backup directory, previously used to restore the security sandbox. It may contain private user data. NEVER upload snapshot archive/manifest, private files, names or errors to GitHub, Drive, chat or public services.

## Temporary trust authentication: restricted scope

The official image uses POSTGRES_HOST_AUTH_METHOD=trust, the same as the previous successful isolated snapshot restoration. This is acceptable ONLY while the fourth Docker network remains internal and only the fourth PG instance is attached. Any unknown container or public host binding is a hard stop. A web integration requires its own reviewed auth/role/credential plan; long-lived QA should migrate to SCRAM and least-privilege roles. Do not connect production or existing QA instances to this network.

This snapshot DB uses tmpfs. It is NOT a persistent backup and will lose its data if the container is stopped or recreated, depending on Docker lifecycle. Never infer successful backup restoration from merely creating the container.

## Resource/operational boundaries

- No changes to running original Rails servers, PostgreSQL clusters, Docker networks, uploaded media, backups or proxies.
- The copied database can include two test accounts and password hashes; internal only, no external access. No real credentials requested.
- Docker memory pressure can affect concurrent services; inspect capacity if necessary, do not force-stop others.
- No reruns or delete after partial create/restore failure. No destructive commands are implemented in this helper.
- CI validates script and disposable Docker config only; does NOT restore owner dump or read owner environment.
- Next new QA web integration requires separate review and unique writable private media clone; do not relax current GET/HEAD guard on existing QA candidate.
- Public release still blocked: no production deploy, no master merge, no QA 3002 proxy cutover.

Status: Draft PR only; first owner action SHA-pinned --check. Nothing has been created on owner hardware in this stage.
