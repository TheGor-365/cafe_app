# Gor's Coffee — public portfolio showcase release checklist (2026-11-09)

This is an illustrative café web app, **not a commercial production service**. No payment processing, actual food preparation, fulfillment or real café exists. Visitors must use fictional data.

## Confirmed before removing the outer preview gate

- [x] Isolated Railway project `gors-coffee-cafe-app`, environment `preview`, service `cafe-web`, private PostgreSQL 18 with persistent volume.
- [x] Deployed integrated application from GitHub `master`, commit `ea1fe1ee091277e7732ca98b6bdf39990781bb90`; Railway deployment `42111cde-b4c4-4cda-b8eb-596ddf3c4875` was SUCCESS.
- [x] Existing user `Eric` was promoted to `admin` using an isolated Railway-only one-shot command; the promotion flag was disabled and the startup command restored afterward.
- [x] Base application supports Devise sign-in/sign-up, non-admin registration, account editing, guest menu, cart, fictional checkout, scoped order history, product/category CRUD and admin order queue.
- [x] Previous copy cleanup passed 173 tests / 1419 assertions / 0 errors, Docker production build SUCCESS (PR #81).
- [x] Local user databases, separate Railway services and old image assets were not reset.

## Open-showcase change in PR #82

- [x] Remove the second password prompt: no `CafePreviewAccessGate` in `config.ru`. Guests see the storefront; Devise is the only interactive account sign-in/sign-up.
- [x] Keep a DB-backed `GET /__cafe_health` via an ordinary Rails controller for Railway readiness.
- [x] First-party SVG favicon served from `public/favicon.svg`; versioned HTML link forces clients to refresh cached former login HTML.
- [x] Add isolated tests for normal navigation, SVG MIME, health, and role-based denial of admin pages.
- [ ] CI Minitest and Docker for PR #82 passing before merge.
- [ ] Railway deploy from `master` SUCCESS after merge.
- [ ] External unauthenticated HTTPS smoke: `/`, `/users/sign_in`, `/users/sign_up`, `/favicon.svg`, `/__cafe_health`, plus admin access redirection.
- [ ] Owner confirms `Eric` sign-in and visible admin links.
- [ ] Owner provides 10 desktop + 10 mobile screenshots; preserve bytes, rename in English, deliver ZIP files and manifest.

## Boundaries / risk acceptance

- The publicly browsable application still runs **unsupported Ruby 2.7.8, Rails 6.1.7.10 and Node 14**. It is not approved for real users, payment or confidential data. A supported-stack upgrade, dependency audit, rate limiting, verified SSL/cookie behavior and real E2E checks are needed before commercial operations.
- Product photo redistribution rights and persistent upload storage remain unverified; do not upload private or potentially unlicensed assets.
- Password recovery by email is not verified; new accounts use normal Devise credentials, but do not promise email-based resets.
- Newly registered accounts have no admin role; only explicitly authorized owner account(s) may change products and order statuses.
- No `db:drop`, `db:reset`, repeat seeding or changes to other projects; the fictional catalog must stay intact.
- Website footer/checkout clearly indicate no real ordering/payment. Do not solicit real customer information.

**Working URL:** https://cafe-web-preview.up.railway.app (Railway project name retains `preview`, but the website is intended as an accessible portfolio demonstration once the release checks above pass).
