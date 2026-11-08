# Gor's Coffee — release gates (2026-11-08)

This document distinguishes a portfolio **demonstration** from a supported public deployment.

## Evidence already verified

- [x] Development features integrated through PR #71: menu, configurable drinks, cart, demo checkout, order-scoped access, admin drink options.
- [x] Rails 6.1 / Ruby 2.7 test suite in isolated CI: 158 tests / 1328 assertions; zero failures/errors (run 42428798391).
- [x] Dedicated Railway project `gors-coffee-cafe-app` + isolated Postgres with 5GB persistent data volume; no changes to owner's local DB.
- [x] Docker build failure root cause reproduced in CI: Rails6.1 ActiveSupport missing stdlib `Logger` load before asset precompile. Fix candidate `RUBYOPT=-rlogger`.
- [ ] Docker image build passes after fix.
- [ ] Railway private preview deploy passes / application boots.
- [ ] DB migrations and guarded demo seed with no real accounts or order data.
- [ ] HTTP smoke: /, /menu, /cart, /info, /catering and error pages return expected responses.
- [ ] Browser smoke: responsive layout, Turbo/JS/Bootstrap, auth, CSRF, scoped orders, admin boundaries.
- [ ] Permanent upload storage and rights-cleared demo media, if accepting uploads or showing portfolio imagery.
- [ ] Rails + Ruby + Node + Devise upgraded to supported versions, dependency security audit; safe cookie/SSL headers and recovery email tested.
- [ ] Restricted preview access until the public-release security gate is passed.
- [ ] Final bilingual portfolio screenshots and actual production URL after successful external verification.

## Protection rules

- `master` is currently the historical default branch; do not expose it on Railway.
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
| Main deployment branch | deploy/cafe-railway-private-preview-20261108 |
| Public domain | None verified |
| HTTP smoke | Pending |
| Git SHA | Record after successful build and deploy |
| Published portfolio | Pending screenshots and rights review |
