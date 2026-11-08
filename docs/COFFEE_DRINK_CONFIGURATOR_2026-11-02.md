# Drink configurator V1 — integration gate · 2026-11-02

First full vertical slice: sizes S/M/L and one optional milk, syrup, extra shot choice for six named demo beverages. All selected IDs validated against active options of the actual product. Selected size, extras, unit price and prices at selection are persisted for the cart. Existing products with no options still use the base product price.

Prices are in integer cents in `product_variants` and `product_modifier_options`. `OrderItem.unit_price` remains the existing decimal persisted snapshot so old cart tests, legacy order totals and existing data continue to work. `order_item_modifiers` persists option references and label/price snapshots; every extra group is 0–1 per cart line. Price never comes from the HTTP request.

Database changes: add exactly one **new** migration `20261102000100_create_cafe_drink_options.rb`. GitHub updates `db/schema.rb` for CI, but the owner's LOCAL schema contains an extra `users.avatar` column, so **NEVER import GitHub db/schema.rb**. Keep owner's local schema and run migration against the existing Cafe database only after a fresh native PostgreSQL backup and a non-production check. Do not run db:schema:load, reset, clean, force checkout, or overwrite uploads.

Site requires local import of new models/migration, updated controllers/cart/menu/seed, CSS and tests; no need to import lockfiles/outer application layout. Repeatable `db:seed` updates six demo beverages; does not provision accounts. No real payments, checkout or delivery.

Manual QA: catalog shows 3 sizes and configurable extras; selected medium with oat milk and vanilla at 2 units correctly totals and snapshots; quantity change retains original price after catalog prices change; unavailable option/foreign option rejected; guest sessions isolated. This is progressive HTML, not a JS live total estimator. Frontend builds and browser tests remain separate.
