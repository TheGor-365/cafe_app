# Gor's Coffee — patched QA candidate (2026-11-04)

## Verified evidence from owner

Owner ran the independently reviewed Draft PR #33 bundle script `--build` in Linux and confirmed:

- Original local Gemfile SHA256 prefix `c5fde478cd117c12`; lock `99f86e38d68e203e`
- Ruby 2.5.8, Bundler 2.2.13, original QA CarrierWave 2.2.3
- New CarrierWave 2.2.7 resolved, downloaded, bundled and loaded successfully
- `ISOLATED PATCHED BUNDLE VERIFIED` / `NO EXISTING APP CONTAINER OR BUNDLE SWITCHED`
- Private stage: `~/.local/share/cafe_app/security_bundle_build_20261104`
- New patched bundle: `~/.local/share/cafe_app/bundle_carrierwave_227_20261104`

Earlier QA SQL confirmed 20 original products and removal of test product ID 21; QA and main HTTP ports 3002 and 3001 are healthy.

## What the next script does

`scripts/cafe_patched_qa_candidate.py` provides three discrete gates:

1. `--check` **read-only**: match local Git branch and source SHA256, ensure staged Gemfile/lock and patched gem exist, inspect exact current old QA container, readonly /app and original /bundle, QA uploads, QA network identity and separate PostgreSQL clusters, guest home/menu HTTP.
2. `--create` **new isolated objects only**: copy existing QA uploads to another private directory with SHA256 equivalence; obtain exactly reviewed `qa/security/avatar_uploader.rb` from the fetched GitHub branch into a new private QA override; create a **not-started** candidate `cafe-app-patched-qa-candidate-20261104`. It uses the *same exact existing image, command, user, tmpfs, readonly project*, old QA-only Devise/controller file overrides, but replaces only its bundle with readonly bind to new CarrierWave 2.2.7 gem collection, mounts the staged Gemfile and lock readonly, new uploader candidate readonly, and an isolated writable copy of QA uploads. It connects only to the isolated QA database network, and exposes **no host port**.
3. `--smoke` starts **only the new candidate**. It verifies actual patched bundle version, QA PostgreSQL system identifier, safe uploader configuration, internal signup form/multipart markup and current 3001/3002 HTTP. **It does not switch the QA proxy**.

Original main Rails/PostgreSQL/avatars; original QA Rails/PostgreSQL/avatars; ports 3001/3002; protected application layout/model/uploader; Git branch and old bundle remain unchanged. This script never removes containers or directories. After partial failure, do not retry blindly; inspect the generated candidate/media and resolve the blocker, retaining rollback resources.

## Remaining release gates

After new candidate internal smoke PASS, prepare a **separately reviewed QA proxy cutover** from port 3002 to the new QA only, with immediate rollback, while preserving the previous proxy/container. Only after that run genuine multipart/browser tests using disposable media: valid jpeg/png/gif, crafted SVG/HTML and mismatched MIME/extension/signature, oversized files, corrupt images, unauthenticated requests, no file persistence on failure, restart persistence, and product/admin regression. More security measures (actual image decode/re-encode, ImageMagick pixel/resource limits, response `nosniff`, CSP, rate limit) remain unverified. No public user uploads until release approval.

Do not merge Draft PRs to master or deploy a public version just because candidate tests pass. Legacy Ruby/Rails still require upgrade and broader security audit.
