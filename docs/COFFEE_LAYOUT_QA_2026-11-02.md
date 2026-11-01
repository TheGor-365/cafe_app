# Cafe responsive layout QA — 2026-11-02

Visual evidence from the owner's localhost:3001 browser: Home cards and entire cart flow work; on desktop the page has unwanted horizontal/vertical scroll, sidebar text loses contrast on white Cart background, and the raw Rails success banner (green and very wide) occupies a Bootstrap row column.

This patch is **one new stylesheet** `app/assets/stylesheets/zz_cafe_layout_reflow.scss` plus isolated CI/regression. It does not edit the owner's dirty `app/views/layouts/application.html.erb`, account avatar, uploads, DB schema, migrations, CSS pack, Ruby or JS dependencies.

CSS makes the legacy four-column shell an explicit grid with `minmax(0, 1fr)`, converts .alert to a fixed compact notice outside grid sizing, restores coffee-dark sidebar/account surfaces, scopes the cart background and fixes 100vw widths. At <=760px, navigation wraps above content. SassC compilation and HTML markup regression in CI; *browser viewport/overflow measurements still require local verification*, never infer them from CI.

Local import:
- fetch branch `feature/cafe-responsive-layout-flash-20261102`
- inspect that file does not exist locally
- import **only** `app/assets/stylesheets/zz_cafe_layout_reflow.scss` (no merge/reset)
- no Rails server restart needed in development, hard-refresh
- check Home/Menu/Cart at desktop; test responsive mode ~375px and 768px
- evaluate horizontal overflow in browser: `document.documentElement.scrollWidth > document.documentElement.clientWidth`
- after adding/updating/removing cart: flash must not move nav; notification can cover some content temporarily but should remain compact and readable
- Cart must have readable nav on dark backdrop and correct totals/guest isolation.

No public deployment and no new real payments. Existing PR #14 remains Draft; await owner screenshot + browser smoke.
