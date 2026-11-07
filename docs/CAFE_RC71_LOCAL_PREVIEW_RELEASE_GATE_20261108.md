# Cafe RC71 isolated local preview · 8 November 2026

This deployment candidate is **localhost-only**, not a public site.
The script `scripts/cafe_rc71_isolated_preview_20261108.py` is explicitly pinned
to commit `83d3346418fccc158bcc72d9c30fb17603b43d30`.
It creates a private clean clone, an internal Docker network, a **NEW**
Postgres 16 data volume and PostgreSQL container, a one-shot DB schema/seed
and Webpacker build, a random local-only admin account, and a Rails web
container bound **only** to 127.0.0.1:3003.

### Isolation / prohibited actions

- No checkout/reset/commit in owner's dirty local branch
  `feature/cafe-integration-local-20261101`.
- No DB migration/reset/seeds on the existing `cafe-app-db`, protected
  fifth PostgreSQL, or any of the previous QA databases.
- No touching original four PG/media, source uploads, or ports 3001/3002.
- No secrets in stdout, GitHub, Google Drive, screenshots or reports.
- No automatic deletion of containers or volumes after failures.
- No existing database/users/orders carried into preview.
- Do NOT expose this unsupported Ruby 2.5 / Rails 6 code to the internet.

### Controlled run

Owner must first download the exact Git blob from the active PR, verify
with `git hash-object`, and run `--check`. If PASS, owner can invoke
`--stage && --launch && --verify` separately. All modes are fail-closed.

The initial private work path is
`~/.local/share/cafe_app/rc71_preview_20261108`; the app endpoint
is `http://127.0.0.1:3003`.

The one-time preview administrator's **random password** is generated
locally and saved in an owner-only 0600 file; it must not be sent to any
assistant. Identity: `preview-admin@example.test`, username
`PreviewAdmin`. This test identity does not exist on port 3001.

The script's Docker behavior has only undergone static CI review until
the owner provides real terminal evidence. No Docker/browser PASS is implied.

### Acceptance gate

1. GET Home/Menu/Cart/Info HTTP200; empty checkout redirects, admin URL
   cannot be accessed by guests.
2. From real browser, preview guest builds drink and verifies cart snapshot;
   completes sample checkout with fictitious details; receives demo receipt.
3. Preview admin signs in and changes order
   `pending → accepted → preparing → ready → completed`.
4. Separate browser verifies isolation from unrelated receipt.
5. Chrome mobile (320/390/430), desktop, console/JS network, keyboard,
   footer and new fixed dock assessed.
6. Preview PostgreSQL and originals independently confirmed isolated.
7. Supported-stack security upgrade, media-license audit, budget approval
   and external HTTPS deployment remain separate public-release gates.
