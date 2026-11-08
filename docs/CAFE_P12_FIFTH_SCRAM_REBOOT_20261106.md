# Cafe P1.2 — fifth PostgreSQL SCRAM recovery after reboot (2026-11-06)

## Confirmed user-local status
Main Cafe 127.0.0.1:3001 and QA 127.0.0.1:3002 restarted with independent persistent PG volumes, SQL + HTTP 200. Historical sandbox PG3 and fourth PG4 restarted using a single SHA256-verified owner-only backup, and independent --verify-clones passed 20 products/2 historical QA users/absent test product ID21 and four distinct PG system IDs. Four isolated historical Rails test candidates started with private exclusive marker and source/media/fourth readonly SQL audit PASS. Original owner feature branch remains dirty and untouched.

## Fifth PG reboot scope
The old fifth synthetic PostgreSQL16 SCRAM uses preexisting Docker object cafe-upload-security-synthetic-pg-20261105, internal network cafe-upload-security-synthetic-net-20261105, a private readonly password bind, tmpfs PGDATA and no host port. It was exited after reboot; its cluster and its old scoped roles disappeared with tmpfs. It must NOT receive copied QA products/users. It must NOT be recreated and must NOT use original --create or --bootstrap modes; those expect new/created-only containers.

The new scripts/cafe_p12_fifth_scram_reboot_20261106.py --check is read only, pins original fifth helper Git SHA 153ffca0535e0c42921d18ea39943bb4a92795fd and owner PR61 reboot helper Git SHA c6e037a97218b084560ccdba183dab4ad0aee1b4. This repeats original four-PG/media/HTTP/readonly Rails audit plus existing fifth PG Docker image, TMPFS, network, secret, SCRAM and stopped state. Absence of old fifth Rails schema marker and new restart marker required. No owner Docker write.

The separately approved --start-empty makes a private 0600 exclusive attempt marker before the ONLY Docker write: docker start of the exact existing fifth container. It waits for actual TCP PostgreSQL readiness to avoid the temporary initdb Unix-only server, then original --verify-running asserts five unique PG system IDs, SCRAM HBA-only, zero imported tables and zero added login roles, plus unchanged original four. No password printed or committed. No local Rails code changes, no Docker create/remove/reset, no schema/data import, no migrations, no public port. On any ambiguity or marker, preserve objects and do not retry blindly.

The read-only --verify-empty checks the restart marker and PostgreSQL state until scoped roles are separately provisioned. After scoped owner/app roles exist, --verify-empty's no-extra-login-role guard is obsolete and the next role/ACL-specific verifier applies.

## Next stage and limits
After fifth SCRAM startup, recover its least-privilege owner NOLOGIN and app LOGIN roles, private credentials, positive/negative SCRAM checks and app DDL denial using a separately reviewed one-shot recovery. Prior owner v2 role-provisioning helper may assume original cluster ID; inspect its exact code/markers before reuse. Only after role checks pass may the fifth-only Rails schema PR57 --check be retried. No direct production or QA schema/data writes, no local Git checkout/merge, no public deploy. CI is mock/static and cannot confirm local Docker.
