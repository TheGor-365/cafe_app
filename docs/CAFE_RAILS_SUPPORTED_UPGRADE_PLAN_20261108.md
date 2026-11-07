# Gor's Coffee — Ruby/Rails upgrade compatibility bridge (2026-11-08)

Purpose: take the verified RC71/PR73 functional code to a supported public
runtime. This is a DIAGNOSTIC CI PROBE, not an app upgrade or deployment.

Source: Draft PR73; owner local port 3003 stays in place and is not touched.
Legacy baseline: Ruby 2.5.8, Rails 6.0.3.6, Webpacker 4, old Devise fork.
Latest accepted full Rails suite on PR71: 158 tests / 1328 assertions / zero errors.

## Source of truth

- Official Rails upgrade guide: https://guides.rubyonrails.org/upgrading_ruby_on_rails.html
- Rails maintenance: https://rubyonrails.org/maintenance
- Rails 8.1.4.1 security release (2026-11-04): https://rubyonrails.org/2026/11/4/Rails-8.0.5.2-and-8.1.4.1-have-been-released
- Webpacker retirement: https://github.com/rails/webpacker

## CI implementation

GitHub Actions runs two independent temporary Ruby 2.7.8 + PG16 jobs:

1) ruby27_rails60 — existing Rails6.0 constraint, Ruby bumped only.
2) ruby27_rails61 — Rails6.1.7.10+ constraint and Ruby2.7.8.

Each job changes Gemfile/lockfile ONLY INSIDE its disposable GitHub runner,
installs gems, creates only cafe_test in the GitHub PostgreSQL service and
runs the full Rails suite. CI-only resolved Gemfile.lock is exported as a
short-lived artifact for review; no lockfile or app code changes land in this
PR. On failure inspect exact dependency or test errors and repair the bridge.

## Path to release (not yet passed)

Ruby 2.7 -> Rails6.1 -> Rails7.0 -> Rails7.1 -> Rails7.2 -> Rails8.0 -> Rails8.1.
Rails 6.1, 7.x and 8.0 are intermediate test steps, not acceptable public
deployment targets as of 2026-11-08; Rails 8.1 currently receives security
maintenance. Upgrade Ruby again to a supported 3.x version between stages.

Devise Git fork, CarrierWave/media, Webpacker4/Turbolinks/Bootstrap4 and
CSRF/authentication are explicit compatibility gates. Stub Webpacker packs
in Rails CI do not validate actual JavaScript. Preserve real browser tests.

No changes to the owner's four PGs, fifth tmpfs, RC71 PostgreSQL, ports
3001/3002/3003, dirty local source, uploaded media or Railway deployments.
No public release until the supported stack, backups and assets pass.
