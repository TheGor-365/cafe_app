# Cafe P0: authenticated HTML and safe local seeds — 2026-11-01

Scope: remove the unkeyed full-page fragment cache from `app/views/layouts/application.html.erb` so a cached view cannot mix distinct users' identity, flash, cart and page content.

Replace the historical seed with repeatable local-only sample categories. No demo admin or known password is created. The seed raises outside `development`/`test`; deliberate production demo setup remains a separate approval gate.

Request regression covers two different browser sessions under enabled fragment caching and logout. Seed regression runs the task twice and checks that admin count is unchanged. Combined CI is required for proof; changes have not been tested locally.

**Local conflict risk:** user has uncommitted changes to this same layout, plus local Gemfile/lock, avatar uploader, edited original devise migration and schema. These remote fixes MUST NOT overwrite the local version. Reconcile the layout manually preserving avatar features before any local merge. The 129 MB source backup exists on the user's machine, not in GitHub. Do not reset/clean the dirty worktree.

No production release, payment or Railway deployment.
