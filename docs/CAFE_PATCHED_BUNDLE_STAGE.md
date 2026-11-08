# Gor's Coffee — isolated CarrierWave 2.2.7 bundle stage

Date: 2026-11-04. The owner's latest read-only audit returned QA 20 products, ID #21 absent, live port 3001 + QA port 3002 HTTP 200, distinct databases, and **CarrierWave 2.2.3 loaded by QA**. The owner-provided SHA256 prefixes for local Gemfile and lock are `c5fde478cd117c12` and `99f86e38d68e203e`, respectively; these differ from GitHub repo contents and are the authoritative local baseline.

## Stage 1: no-change audit

Import the script by exact reviewed SHA as a standalone copy outside the user's dirty project. Execute `--check`. Script confirms the exact local branch, Gemfile/lock hashes and an unpinned carrierwave declaration, QA container image, current read-only app mount, legacy bundle volume name/readonly setting, Ruby/Bundler versions, QA installed CarrierWave version, and local Docker image already present.

**If any check fails, stop.** Do not replace local Gemfile or lock with GitHub copies.

## Stage 2: build *new* patched bundle, no activation

Only after the audit passes, execute `--build`. Creates two new owner-private directories outside the repo:

- `~/.local/share/cafe_app/security_bundle_build_20261104`: copies of the owner's Gemfile/lock, with ONLY CarrierWave pinned to 2.2.7 in the copy.
- `~/.local/share/cafe_app/bundle_carrierwave_227_20261104`: completely separate bundle installation.

Runs a disposable `cafe-legacy-full:node14` Docker container with `--network bridge`, no app mount, database networks, secrets or existing bundle volumes; unprivileged uid 1000, read-only root, constrained memory/processes, only the two new writable bind mounts. Attempts Bundler 2.2.13 lock/update/install and verifies loaded version 2.2.7. This can use internet to download approved public dependencies; if the installed image lacks Bundler 2.2.13 or networking is unavailable, the operation fails without changing existing containers; leave the candidate directories intact for diagnostics.

**This does not patch QA or production:** no Docker container restart, no bundle or proxy switch, no changes to project source, DB or media. Review lock diff and installed patched gem before creating a new, isolated QA-only Rails instance.

## Future QA runtime

Mount staged Gemfile+lock and new bundle read-only, add independently verified QA-only uploader from Draft PR #32, keep the application read-only and QA images writable only at their isolated mount, connect exclusively to isolated QA PostgreSQL. Perform full HTTP multipart positive/negative tests, including unsupported MIME/extension, crafted invalid images, >2MiB, unauthenticated requests and restart persistence. Keep old QA instance and proxy for rollback; never directly replace production.

## Release blockers

Original Ruby 2.5 / Rails 6 is legacy and requires supported-version upgrade before serious public usage. ImageMagick decode/re-encode/resource policy, HTTP security headers, true MIME validation, upload rate limiting and storage safety still need acceptance. PR #32 has passed **4 security policy tests, 31 assertions, zero failures** using patched 2.2.7 in ephemeral CI; that is not sufficient to approve public uploads.
