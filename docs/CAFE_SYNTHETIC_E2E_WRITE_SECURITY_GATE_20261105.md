# Cafe security E2E — synthetic writable boundary tests (2026-11-05)

## Last owner-confirmed QA result

Owner executed the SHA-pinned new private fourth-PostgreSQL Rails candidate `--smoke` and received:
- E2E_FOURTH_DB_READ_ONLY_CARRIERWAVE_PASS
- E2E_FOURTH_DB_READ_ONLY_HTML_HEADERS_PASS
- E2E_FOURTH_DB_PRIVATE_JPEG_HTTP_SHA_PASS
- E2E_FOURTH_DB_POST_DENIED_405_PASS
- E2E_FOURTH_DB_RO_HTTP_SMOKE_COMPLETE
- FOURTH PRIVATE DB RAILS HTTP READ-ONLY E2E BOOTSTRAP PASS
- ORIGINAL 3001/3002/THREE PG AND MEDIA UNCHANGED
- NO LOGIN/UPLOAD/POST/ADMIN OR PUBLIC RELEASE AUTHORIZED

Interpretation: Rails is running inside only the fourth network, it reaches precisely the new PostgreSQL with 20 restored products, and network/DB/media/protected-header/GET/HEAD constraints passed. **Not** evidence that writable uploads, account registration, actual CSRF in the running server or authentication flows work. The fourth DB snapshot includes 2 copied user accounts and PG host authentication is `trust`; it is not an appropriate target for unrestricted user-flow tests.

## Actual repository analysis

- `config/routes.rb` exposes Devise registration/login/password endpoints, admin resources `products` and `categories`, and cart actions.
- `ProductsController` and `CategoriesController` require authenticated admin and use strong parameters. Image upload is intentionally excluded from `product_params`; attempting multipart product upload does not exercise an enabled route.
- `ApplicationController#configure_permitted_parameters` allows Devise username fields but not avatar; original User model and tracked schema do not include an avatar column. The avatar security policy under `qa/security/avatar_uploader_preflight.rb` is a separately reviewed isolated candidate, NOT evidence of an enabled live HTTP avatar endpoint. Do not enable it without a new test-only mount and owner approval.
- `OrderItemsController` scopes update/destroy to `current_order.order_items.find`, so cross-session mutation must be rejected. Existing cart tests cover consolidation; new CI test covers direct cross-session update and delete.
- `config/environments/test.rb` disables forgery protection for ordinary suite speed; the new security test switches it on only for the duration of one test, restores previous setting in ensure, and asserts missing-token POST is rejected.
- `config/environments/development.rb` uses consider_all_requests_local=true. Even internal-only QA instances may show sensitive errors if exposed; no browser/public network should be added without a separate review.

## This PR — synthetic tests only

Adds `test/integration/cafe_e2e_write_boundary_test.rb` and scoped GitHub Actions workflow `coffee-e2e-write-boundary-ci.yml`.
- CI uses disposable PostgreSQL16 with test-only user/password and `RAILS_ENV=test` on ruby:2.5.8, creating the schema from the repository and synthetic admin/customer data and synthetic catalog entries.
- Covers unauthorized catalog/category mutation, product image strong-parameter rejection, forged Devise avatar/admin field handling, cross-session basket write isolation and anti-CSRF missing-token rejection.
- Runs alongside existing admin CRUD, Devise/account and cart consolidation regression suites.
- No private database, image, backup, password, personal filenames or container is shared with GitHub.
- No changes to application controllers, production dependencies or database schema; all writes are disposable CI fixture writes only.

## Next safe local gate before owner-side writable HTTP

1. Confirm GitHub CI integration tests pass and resolve any failures.
2. Add a separately approved disposable synthetic-only database with strict scoped roles, authentication and no copied private user/password hashes. Prefer an isolated new temporary test DB/network over opening the fourth copied-user database. No public ports.
3. Prepare a new **test-only** web candidate, with its own media directory and one allowed write path, strict MIME/file signatures/size/pixel policy, CSRF/session authentication, and operation-specific audit/count checks. Copying production or QA account credentials into it is forbidden.
4. Only then run reversible mutation tests: one synthetic signup, session login/logout, CSRF negative case, unauthorized admin changes, cart create/update/delete, multipart cases using **synthetic** images, and no residual files after rejected uploads. Confirm original media SHA256 and three older PG identities before/after. No permanent public access, deployment, merge to default branch or main QA 3002 cutover.
5. Keep separate receipt/checkpoint with explicit facts, sources and date.

This PR does not authorize mutations on the already running fourth-DB Rails candidate: that candidate must remain GET/HEAD-only with `PGOPTIONS=-c default_transaction_read_only=on`, and existing POST must continue returning HTTP 405.
