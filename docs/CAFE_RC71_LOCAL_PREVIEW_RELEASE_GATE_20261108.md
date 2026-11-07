# Cafe RC71 isolated local preview · 8 November 2026

This deployment candidate is **localhost-only**, not a public site.
The script `scripts/cafe_rc71_isolated_preview_20261108.py` is explicitly pinned
to commit `83d3346418fccc158bcc72d9c30fb17603b43d30`.
It creates a private clean clone, an internal Docker network, a **NEW**
Postgres 16 data volume and PostgreSQL container, a one-shot DB schema/seed
and Webpacker build, a random local-only admin account, and a Rails web
container bound **only** to 127.0.0.1:3003.
The runtime uses the immutable image IDs already backing the reviewed local
containers and passes `--pull=never`; mutable tags cannot trigger a hidden pull
between preflight and launch. The staged Git worktree must remain completely
clean, including untracked files.
Staging also creates the empty nested Docker mountpoint directories required
below the read-only `/app` bind; this does not change the pinned Git tree.
PostgreSQL readiness requires two successful SQL probes from the same
postmaster, avoiding the official image's temporary initialization server.
Because PR71 pins Devise to a Git revision not present in the owner's shared
bundle, staging also fetches that exact commit and mounts it read-only as a
Bundler local override. Because other locked versions also differ, launch
copies the shared bundle read-only into a new preview-only volume and installs
only into that private volume in a build container with no published ports or
database access. Runtime mounts the resulting private bundle read-only; the
shared bundle remains unchanged.
The copied private bundle is owned by the preview UID 1000; dependency setup
and runtime never need remapped container-root access to the owner-only source.
Only the offline bundle-copy container receives `CHOWN` after dropping all
capabilities; it has no network, source checkout, database, secrets or ports.
Bundler writes any required platform metadata only to an owner-only preview
copy of `Gemfile.lock`; its SHA-256 is recorded after build and every Rails
runtime mounts that copy read-only with frozen mode. The pinned source lockfile
is never modified.
Schema loading is executed through a guarded Rails runner on the already
verified `rc71-pg/cafe` connection. It does not invoke the development rake
hook that also prepares the configured test database, so no existing or fifth
test database can be selected.
Rails and PostgreSQL remain only on the internal network and publish no host
ports. A stateless read-only TCP proxy with no mounts, source, bundle, DB
credentials or application environment joins a separate access bridge plus
the internal network and is the only container bound to `127.0.0.1:3003`.

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

The command builders have offline unit coverage in CI. Real Docker and browser
acceptance are still required on the owner machine; static CI alone does not
imply a Docker/browser PASS.

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
