# Fifth synthetic PostgreSQL — scoped roles gate, 2026-11-05

## Verified preconditions

- Owner's fifth synthetic PostgreSQL16 SCRAM cluster successfully passed: \`--check\`, \`--create\`, \`--verify-created\`, \`--bootstrap\`, \`--verify-running\`. It is running in its own Docker internal network, five PG system identifiers are distinct, and original Rails 3001/3002 / original media remain unchanged.
- The owner installed \`cafe_synthetic_pg_roles_v1_20261105.py\` using a SHA-checked ZIP and received \`LEAST-PRIVILEGE PRECHECK COMPLETE — NO CHANGES\`. No role provisioning has been executed by owner yet.
- Original v1 role script SHA256: \`cd92880abc9100d7e82366bb266e86fe91f8777094b1d4b694a2f9171a6058a5\`.
- **Important bug**: v1's post-provision assertions use \`has_database_privilege(...)::text\` / \`has_schema_privilege(...)::text\` but expect native PostgreSQL boolean \`t/f\`. The explicit cast returns \`true/false\`. This would lead to **successful role creation followed by a false verification failure**. Owner MUST NOT run v1 \`--provision\`.
- Corrected v2 replaces exactly seven \`)::text;\` with \`);\`, preserving the native \`t/f\` result. Corrected v2 SHA256 \`ecab358e7edcbc7828621e339ee7211077380ffba39d2046011baea556b8bdea\`. It has NOT yet been executed on the owner's machine or against the owner's fifth PG.
- Both roles are **solely for synthetic** \`cafe_synthetic\`: \`cafe_synth_owner NOLOGIN\` owns public schema; \`cafe_synth_app LOGIN\` gets CONNECT and USAGE, but no SUPERUSER/CREATEDB/CREATEROLE/CREATE ON public/CREATE DB/TEMP/role membership. Default table and sequence privileges are scoped to \`cafe_synth_owner\` in public.
- Password for new \`cafe_synth_app\` is generated at runtime, never logged or committed. Docker/socket administrators have authority over the test DB. No source user record, actual avatar file, customer data, email, secret or backup is in this PR.

## Evidence

Workflow \`.github/workflows/coffee-synthetic-pg-scoped-roles.yml\` creates a completely ephemeral PostgreSQL16 in GitHub Actions, reproduces role SQL in \`qa/security/cafe_synthetic_roles_acl_ci.sql\`, asserts role/ACL boundaries and default owner-created table and sequence CRUD, verifies correct/wrong SCRAM password, and blocks application DDL. Database is discarded by the GitHub runner. Original v1's \`::text\` mismatch was reproduced by CI and the assertion corrected; CI latest SHA PASS is required.

## Next owner gate

1. Locally generate corrected v2 in a **new filename** from SHA-pinned v1: enforce original SHA, exactly seven replacements, new SHA, mode 0600, and only \`--check\`.
2. After v2 preflight PASS and final CI success, separately run v2 \`--provision\` once; never blindly repeat if partial failure.
3. Run v2 \`--verify\` in the following turn. From then onward the old \`--verify-running\` contract (zero extra login roles) is obsolete; v2 uses a compatible five-cluster guard.

No schema load, Rails attach, HTTP POST, public port, deployment, working branch checkout/merge, other PG changes or production release allowed.
