# Cafe P1.2 — post-reboot private test Rails only, 2026-11-06

## Evidence and dependency

Owner confirms local worktree remains dirty on `feature/cafe-integration-local-20261101` and **must not be modified**. After reboot:
- Existing production `127.0.0.1:3001` and patched QA `127.0.0.1:3002` were restarted from persistent PostgreSQL volumes. Both served HTTP 200; QA CarrierWave 2.2.7 and sign-up multipart form PASS.
- Existing PG3 sandbox and PG4 fourth E2E were separately started and restored from an owner-only SHA256-verified private QA dump. `--restore-clones` owner output confirmed 20 products / 2 historical test QA users / ID21 absent; fifth SCRAM PostgreSQL still exited/empty in tmpfs.
- Independent owner `--verify-clones` still outstanding at time of authoring.

Old P1.2 PR #57 fifth-only schema-loader preflight imports a SHA-pinned old fifth PG helper, whose `source_baseline()` requires:
- PG3 sandbox + PG4 fourth internal-only clusters distinct from original production and QA;
- the original private **fourth read-only E2E Rails** web running;
- the old internal **headers report-only candidate** running;
- old sandbox pre-cache candidate and its original sandbox web running for the original verified snapshot/media guard chain.

## New helper and security boundaries

`scripts/cafe_p12_reboot_private_test_rails_20261106.py`:

- `--check`: READ ONLY, imports SHA-pinned owner test DB restore verifier Git blob `403609bc7710b88b109959caed49a850c7f068c8`; verifies protected original/QA ports + independent PG3/PG4 baselines, private dump and one-shot marker. Checks exact **four pre-existing** Docker QA candidate names, stopped or running; validates original legacy runtime image, uid1000, read-only root, no published host port, separate internal-only networks, code mounted readonly, media mounted only as preexisting private clone. Source databases must resolve to exact sandbox-only or fourth-only DNS targets; headers and fourth DB connections require `PGOPTIONS=-c default_transaction_read_only=on`. Requires synthetic fifth PG stopped and its Rails DDL marker absent.
- `--start`: separate one-shot step after preflight, creates private exclusive 0600 marker **before Docker start**, sequentially starts only sandbox Rails, sandbox pre-cache Rails, private headers candidate, private fourth read-only E2E Rails; never starts or restarts a production or patched QA resource. After start, imports exact prior reviewed fourth Rails helper Git blob `62e52015dfe7dd5ca15b1c3eabe380a38e7eca0a` and rechecks its full restored DB/media/network/headers read-only E2E contract. Stops on any ambiguity, preserves all containers/markers, no blind retry.
- `--verify`: READ ONLY postflight, no Docker or SQL writes, recheck old source and restored clusters independently.

The two older sandbox Rails may have writable **only private sandbox media** mounts; no HTTP uploads are sent. No original media or production/QA volumes are mounted into the new staging. The report-only headers and fourth E2E Rails have read-only PostgreSQL sessions; all four candidate containers have no host port.

## Limits

CI runs static + mocked contract only; **no owner Docker is reachable from GitHub**. The original fourth read-only helper's preflight is run on the owner host, not CI. All steps are fail closed. This restores only previously created QA infrastructure — **NOT** fifth SCRAM PG roles, synthetic Rails schema, seeds, migrations, or app changes. Must execute owner `--verify-clones` before moving to a new test Rails gate. No branch checkout/reset/merge or cleanup.

## Owner-local preflight failure and fix (2026-11-06)

Owner fetched PR #61 exact head `a284c5b3d6b128e4441395d59fd3eb6168297e4b`, helper blob `00ea6dde28da2f1670d7ba2555a142de59802d25`, installed into a private 0600 owner path and ran `--check` only. Protected two-temp-PG `--verify-clones` passed with 20 products/2 historical QA users and 3001/3002 isolation. Rails boot preflight stopped on **`sandbox-original source/media mount scope changed`**. No boot marker was written, no test Rails was started by this preflight.

**Root cause found in original reviewed code:** `scripts/cafe_sandbox_rails.py` `mount_specs()` explicitly inherits pre-existing **read-only named Docker volumes** from patched Rails dependency mounts, while original PR #61 new preflight blanket-rejected every volume. The newer rule was stricter than the historical verified construction. `scripts/cafe_precache_sandbox_acceptance.py`, `scripts/cafe_private_headers_qa_mountfix.py`, and `scripts/cafe_private_e2e_web_readonly.py` also explicitly inherit read-only named volumes. This discrepancy is a source-contract bug; **not** evidence of Docker media or data damage.

PR #61 now accepts `Type=volume` only when `RW=false` and the volume name is nonempty. It continues to require read-only `/app`, exact original private-media source per candidate with only that media bind writable, SHA-pinned readonly Ruby `/bundle`, no host port, dedicated internal network, exact sandbox/fourth DB URL, expected UID/image, and no original QA secret mount. New `test/security/cafe_p12_test_rails_mount_contract_test.py` exercises a legitimate read-only named volume plus negative mount, network, secret, media and public-port cases in CI.

**Owner must NOT run the old installed v1 helper again.** After exact new PR head GitHub CI passes, fetch new script by commit+blob into a **new filename** and run `--check` only. `--start` is separately gated. Production/QA, restored test PG, original private media and user worktree remain unchanged.
