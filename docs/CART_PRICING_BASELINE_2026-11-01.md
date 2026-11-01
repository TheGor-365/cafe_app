# Cafe App — cart arithmetic baseline (2026-11-01)

Base: GitHub `master` `06f66f3d318e1a3fe3e5683baf541f5fec8b4c01`.

Issue: `OrderItem#total` already multiplies unit price by quantity, but `before_save :set_total` multiplied by quantity again, persisting a squared quantity factor.

This commit fixes persisted totals and validates positive integer quantities. It adds model regression tests for quantities 1/2/3, updates, original price snapshots, and invalid quantities.

**Not verified:** tests are unexecuted on this GitHub-only branch. Existing legacy fixture issues and Ruby/Rails lockfile setup may block the suite until the separate ACL PR is integrated. This does not establish that cart HTTP flows, session isolation, or payment processing work. Product ID is still permitted on update in `OrderItemsController` and requires a separate request-level fix/test.

This branch does not change local dirty files, original seeds, schema, or Railway.
