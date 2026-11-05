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


## Owner follow-up: read-only OCI mount isolation (2026-11-05)

Owner ran SHA-pinned PR #56 P1.1 v3; P1 checks passed, fifth database was still empty, but Rails probe stopped **before shell entry** with `readonly_filesystem`. A separate SHA-pinned diagnostic at PR #56 commit `53a1cd64678a9c8a32053028d456f4650e3087c7`, script blob `95921a7b4f687a19feca625ebb7308d5fd522004`, produced:

- `P1.1 DIAG PRECHECK — FIFTH DB EMPTY / FOUR ORIGINAL PG ISOLATED PASS`
- `P1.1 DIAG PINNED GIT ARCHIVE VERIFIED PASS`
- `P1.1 DIAG BASE PASS`
- `P1.1 DIAG TMPFS PASS`
- `P1.1 DIAG SOURCE_RO PASS`
- `CAFE P1.1 DOCKER START DIAG STOP: BUNDLE_CACHE_RO [OCI_OR_SHELL_ERROR / readonly_filesystem]`.

Thus read-only root, tmpfs and read-only canonical Git source mount **alone** all work. Adding existing read-only dependency volumes triggers the OCI error before shell. Potential nested mount under the read-only `/app` source is a hypothesis, not yet verified. Next read-only owner inspection: list **only** mount destination/type/read-only flag for whitelisted dependency paths on `cafe-upload-security-headers-mountfix-20261104`, withholding volume sources and environment. Do not change any existing volume, container, original project files, fifth DB schema, host ports or production services. Once destination is known, fix only the disposable runner's mountpoints and reverify through CI and owner Linux.

## Follow-up: exact Docker mount identity and narrowly scoped fix

Owner ran `docker inspect --type container` against the existing source QA web and confirmed its **only** whitelisted dependency mount:

```text
target=/app/node_modules type=volume rw=false
```

This proves the `BUNDLE_CACHE_RO` OCI failure appeared when the disposable process tried to add the nested read-only `/app/node_modules` volume under an already read-only `/app` Git snapshot. It does not establish a general Ruby gem or Rails compatibility failure.

The P1.1 runtime probe now intentionally **skips** this single JavaScript-only mount, and whitelists only non-nested Ruby dependency volumes outside `/app` (if any). It additionally fails closed if the inspected existing node_modules mount is missing, writable or not a volume; nothing is remounted or changed on the original source QA container. GitHub CI validates a mocked inspect response and rejects a writable node_modules source. Owner must fetch the new exact PR SHA and rerun the SHA-pinned P1.1 probe only; this is not a fifth-DB schema writer. The fifth database remains empty until an independent verified one-shot schema stage.

## Owner checkpoint: P1.1 v4 — OCI fixed, Bundler blocked

Owner executed SHA-pinned P1.1 v4 probe from PR #56 commit `43a7120c59a3f41e5761cd99fe6a57b0e38c3cd0` (probe blob `c80d47760644dc73c5183161f618238e06ac3407`). Owner stdout confirms:

- P1 re-audit PASS: fifth DB empty / five clusters separate / private media SHA / HTTP 3001+3002;
- `P1.1 INCOMPATIBLE NESTED NODE_MODULES VOLUME EXCLUDED PASS`: nested mount no longer blocks OCI container startup;
- `CAFE P1.1 RAILS PROBE STOP: isolated_rails_container failed [rails_boot / ruby_bundle_resolution]`.

The last marker denotes the failure at `bundle exec rails -v` **after** successful `ruby -v` and `bundle --version`. It does not prove Rails loaded. The pinned `Gemfile.lock` blob `06f3924bf211e56d0845bca1f6508bb81bf8a324` includes only `PLATFORMS: x64-mingw32` and `BUNDLED WITH: 2.2.13`; this is a concrete Linux compatibility concern but does not prove the exact local Bundler error. The proven P0 CI *did* add the Linux platform in an ephemeral checkout and install gems before running Rails 6.0.3.6.

Next: inspect only gem metadata baked into the isolated immutable `cafe-legacy-full:node14` Docker image using disposable read-only networkless execution. Do not mount the dirty checkout, run `bundle install`, enable network access, copy a private bundle, or write PostgreSQL yet. If missing gems or cross-platform lock is confirmed, prepare a **separate** disposable Linux bundle/source normalization strategy with CI evidence; the canonical Git lock remains unchanged.

## Owner checkpoint: container RubyGems inventory (2026-11-05)

Owner ran a standalone `docker run --rm --pull=never --network none --read-only --user 1000:1000 --cap-drop ALL --security-opt no-new-privileges --entrypoint ruby cafe-legacy-full:node14 -e 'require "rubygems"; ...'` against the isolated image **without any source or dependency mount**. Its default RubyGems search path returned:

```text
bundler: 2.2.13, 1.17.3
rails: MISSING
railties: MISSING
activerecord: MISSING
pg: MISSING
devise: MISSING
carrierwave: MISSING
```

This is conclusive only for the image's **unmounted default RubyGems lookup**, not every possible bundle directory and not the running QA source container. It explains the standalone P1.1 runtime failure more directly than the Windows-only canonical lockfile platform, which is an additional potential blocker. No `bundle install`, schema load or fifth PostgreSQL writes occurred.

Next single nonmutating owner step: `docker inspect` the original **running** `cafe-upload-security-headers-mountfix-20261104` and show **destination/type/rw only**, especially `/app`. Do not print bind-mount host sources, volumes names, full environment or credentials. Then identify and verify any already-installed, separately mounted QA dependencies; if none exist, design a disposable CI-like `bundle install` into a distinct new temporary cache without touching protected source or legacy services.

## Owner mount inventory: /bundle is a read-only host bind (2026-11-05)

Owner's nonmutating `docker inspect --format` of original `cafe-upload-security-headers-mountfix-20261104` established all mount targets/types/flags, including `target=/bundle type=bind rw=false` and `target=/app/node_modules type=volume rw=false`. Several other protected `/app` source files and private uploads are also mounted; the standalone probe must **never** carry these into a disposable runner.

P1.1 v5 updates **only** the disposable runner: it inspects the source QA metadata and requires exactly one read-only `/bundle` bind at its original destination; refuses writable, symlinked, unavailable or credential-like bundle paths; does not print the host source; forwards `BUNDLE_PATH=/bundle` and `BUNDLE_FROZEN=true` while retaining `--network=none`, `--read-only`, `--cap-drop=ALL`, and an immutable tracked Git source snapshot mounted read-only at `/app`. Still excludes nested `/app/node_modules`, private uploads, all other original application mounts and the fifth PG. The bundle path may contain untrusted code and must be used only in the constrained disposable test sandbox. GitHub CI tests allowlisted read-only metadata and negatives for writable mounts and secret paths; CI alone cannot prove runtime success.

A Linux Ruby 2.5.8/Rails 6.0 compatibility failure may still occur because the canonical tracked `Gemfile.lock` lists only Windows platform. Do not replace the original lock or alter the source QA's override. Owner must confirm P1.1 v5 real stdout before further schema writer development.
