# Coffee cart consolidation — 2026-11-02

## Trigger / evidence
The user verified the live price preview and showed two **identically configured Cappuccino Medium + oat milk + vanilla** entries in the cart, with quantities 2 and 3 and a total of $30.75. User wants to continue making the café product professional.

## Behavior
- On new POST Add to cart, identical cart lines **within the same guest session** are aggregated. Match requires product, variant, unit price snapshot, variant label snapshot and exact per-group modifier IDs, label and price snapshots. Modifier order is ignored.
- Price changes and label changes in the catalog create a distinct price batch; existing snapshots never mutate.
- Quantity cap remains 20 per line: reject a merge exceeding 20; do not silently create a new line or lose quantity.
- A separate visible **Combine matching items** POST button appears only when older already-saved duplicate rows can be safely joined; it is user-initiated and has CSRF protection.
- The parent's Order row is locked for aggregation to serialize parallel adds to the same order; no cross-session changes.
- Keeps pre-configuration cart lines editable after subsequent creation of product sizes.
- No schema/migration changes, no seeds, no changes to Gemfile/lock, avatar/uploads or old Rails migration. No JS/CSS pack change, Sprockets new CSS only.

## Local import
Owner uses dirty local branch `feature/cafe-integration-local-20261101` with Rails 6.0.6.1 and working `localhost:3001`. **Do not merge/reset or replace local schema or outer layout.** Compare existing files against branch `feature/cafe-live-price-preview-20261102` before guarded import; bring only new service, controller/view/model/routes/CSS/test. Container binds /app readonly but Rails reloads Ruby in development; restart only if necessary, then hard-refresh to replace CSRF form token.

## Acceptance
- Existing local two lines 2 + 3 should show **Combine matching items**; click => one line qty 5 subtotal $30.75.
- Add another item of the same exact variant and extras => quantity increments, no duplicate line (unless cap would exceed 20).
- Different milk/syrup, variant, or price snapshot remain separate.
- Empty guest can't modify another's cart.
- Mobile cart remains usable.
- No background normalization or irreversible database migration.
