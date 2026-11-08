# Gor's Coffee — preview release checklist (2026-11-09)

This is a **portfolio project**, not a real café or supported production commerce platform.

## Verified engineering baseline

- [x] Menu, search, cart, configurable drinks, orders, administrative CRUD and server-side checks integrated into `master`.
- [x] Dedicated Railway `gors-coffee-cafe-app` project, `preview` environment and persistent PostgreSQL volume. Other user services and databases remain untouched.
- [x] Ruby 2.7.8 / Rails 6.1.7.10 and Node 14 builds work in the isolated environment. These runtimes are **end of life** and require upgrading before a real public business launch.
- [x] The Logger loading issue was resolved and isolated CI production Docker build passed.
- [x] HTTPS `/__cafe_health` responds with `ok` and tests its PostgreSQL connection.
- [x] An owner account is a normal Devise user first. Only the exact Railway-configured username with an independently configured strong secret can activate owner privileges; regular registration cannot grant `admin`.
- [x] The source tests verify standard sign-in/registration paths, protected non-authenticated pages, owner claims and privilege boundaries.
- [ ] Owner completes live browser check of normal sign-in, signup, account, cart, order and all admin CRUD navigation.
- [ ] Capture and curate 10 desktop + 10 mobile screenshots, with original image bytes preserved.
- [ ] Persistent upload storage and rights-cleared product media.
- [ ] Supported Ruby/Rails/Node/Devise, security audit, confirmed email/password recovery and production operational controls.

## User-facing copy

- Customer and admin pages use standard labels: **Menu**, **Cart**, **Checkout**, **Orders**, **Sign in**, **Create account**, **Manage products** and **Manage categories**.
- Repeated “demo” badges were removed from visible templates; internal Rails model and path names such as `demo_orders` were **not** renamed to avoid data migration and breaking links.
- A small footer disclaimer still states that this is a portfolio project and no actual purchases/payments are possible. Do not imply live commerce.

## Railway

| Item | Verified or intended state |
| --- | --- |
| Project | `gors-coffee-cafe-app` |
| Environment | `preview` |
| Web service | `cafe-web` |
| Database | Isolated PostgreSQL (do not reseed or reset) |
| Source | `TheGor-365/cafe_app`, `master` |
| URL | https://cafe-web-preview.up.railway.app |
| Owner setup | `CAFE_OWNER_USERNAME` and `CAFE_OWNER_CLAIM_TOKEN` configured as Railway-only variables, never in Git |
| Owner claim | `/owner/access` for an already signed-in eligible user |
| Release PR | #80, gated on Rails and Docker CI |
| Live auth smoke | Must be verified after the new `master` deployment |

## Operational protections

- Never run `db:drop`, `db:reset` or repeat the catalog seed against owner/local/shared/preview databases.
- Never publish the owner claim token, passwords, KYC, real customer details or unlicensed images.
- The legacy application should remain portfolio-only; no payments, fulfilment or public commercial orders.
