# Gor's Coffee — release gates (2026-11-08)

This document distinguishes a portfolio **demonstration** from a supported public deployment.

## Evidence already verified

- [x] Development features integrated through PR #71: menu, configurable drinks, cart, demo checkout, order-scoped access, admin drink options.
- [x] Rails 6.1 / Ruby 2.7 test suite in isolated CI: 158 tests / 1328 assertions; zero failures/errors (run 42428798391).
- [x] Dedicated Railway project `gors-coffee-cafe-app` + isolated Postgres with 5GB persistent data volume; no changes to owner's local DB.
- [x] Docker build failure root cause reproduced in CI: Rails6.1 ActiveSupport missing stdlib `Logger` load before asset precompile. Fix candidate `RUBYOPT=-rlogger`.
- [x] Docker image builds after Logger/asset-precompile fixes (CI run 42519024703).
- [x] Railway preview service booted and passed healthcheck on release SHA 998868c9fe25900fa17299ec87e7495aa4521e57.
- [x] Railway isolated DB migrations and guarded fictional seed completed; repeated boot is idempotent.
- [x] External HTTPS GET /__cafe_health returns `ok`; Railway managed domain and internal healthcheck succeeded.
- [ ] Authenticated browser smoke: /, /menu, /cart, /info, /catering; confirm the anonymous root returns HTTP 401 and all assets are gated.
- [ ] Browser smoke: responsive layout, Turbo/JS/Bootstrap, auth, CSRF, scoped orders, admin boundaries.
- [ ] Permanent upload storage and rights-cleared demo media, if accepting uploads or showing portfolio imagery.
- [ ] Rails + Ruby + Node + Devise upgraded to supported versions, dependency security audit; safe cookie/SSL headers and recovery email tested.
- [x] Preview Rack HTTP Basic gate with a Railway-only 24+ byte password; independent health endpoint checks PostgreSQL. Rails CI tests gate behavior.
- [ ] Final bilingual portfolio screenshots and actual production URL after successful external verification.

## Protection rules

- Default branch is `master`. Before merging release PR #77 it remains historical; deploy only the reviewed gated release tree. Never repoint Railway at the old legacy master SHA.
- Current code lives in stacked feature PRs and an isolated deploy branch. Merge to default only after a reviewed integrated release PR and passing CI.
- Never run `db:drop`, `db:reset`, legacy seeds, or owner-local Docker commands.
- Never include secrets, real personal data or potentially unlicensed product photographs in public releases.
- No real payment or order fulfilment is implemented. Report demo status truthfully.

## Deployment verification (record after success)

| Item | Current value |
| --- | --- |
| Railway project | gors-coffee-cafe-app |
| Environment | preview |
| Service | cafe-web |
| Private database | Railway Postgres, separate volume |
| Main deployment branch | release/cafe-demo-20261108 (PR #77 to master) |
| Protected demo domain | https://cafe-web-preview.up.railway.app (HTTP Basic gated) |
| HTTP smoke | external /__cafe_health = `ok`; authenticated UI pending |
| Git SHA | 998868c9fe25900fa17299ec87e7495aa4521e57; CI 42519024703 SUCCESS |
| Published portfolio | Pending screenshots and rights review |
