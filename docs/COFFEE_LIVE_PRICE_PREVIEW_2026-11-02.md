# Live price preview — local handoff · 2026-11-02

## Scope
The user's local browser confirmed a real Cappuccino Medium + oat milk + vanilla syrup, qty 2, in cart for **$12.30**, with old Rails schema reload / CSRF errors resolved. This improvement adds a visible live **Unit / Total** estimate to each configured beverage card.

- Progressive enhancement: plain HTML POST still works with JavaScript disabled.
- JS accepts integer-cent prices embedded by Rails in HTML `option[data-price-cents]`, not client-supplied price parameters. Existing Rails controller recomputes final price independently.
- Enables updates on HTML change/input events, initial render, DOMContentLoaded, Turbolinks page load.
- Show **From** price on the product card instead of implying base price applies to Medium/Large.
- Error/invalid quantity state disables add button until corrected.
- No new dependencies, no DB migration or seeds needed.

## Local delivery
User's current local feature branch is dirty and includes avatar, Rails 6.0.6.1, schema and other safe changes. DO NOT merge/reset/change db/schema, original migrations, public/uploads/user, Gemfile/lock or outer app layout.

After PASS from CI, import only:
- `app/javascript/coffee_price_preview.js` (new)
- `app/javascript/packs/application.js` (import statement, only if exact current content matches branch's parent)
- `app/views/menu/_products.html.erb` (only if exact parent hash matches)
- `app/assets/stylesheets/cafe_live_price_preview.scss` (new)
- `test/integration/coffee_live_price_preview_test.rb` and `test/javascript/coffee_price_preview.test.js` (new)

**Important:** user compiled Webpack 4 assets into Docker volume `cafe-packs-20261101`; changing application.js does NOT rebuild that pack automatically with read-only mounts. Re-run known isolated Node14 Webpack 4 command with the existing node_modules and packs volumes, then confirm manifest output is updated. Test `localhost:3001/menu` after hard refresh and price totals with qty, options. No production deployment.

## Acceptance
Preview of Medium+oat+vanilla, qty 2 = $12.30 before adding; cart still $12.30. Unsupported input falls back to server error/HTML validation; without JS cart keeps working. Run Node tests and actual webpack build before local import.
