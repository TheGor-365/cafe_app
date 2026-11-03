# Gor's Coffee — QA avatar rollout (2026-11-03)

## Purpose and verified baseline

QA-only deployment script: `scripts/cafe_qa_avatar_rollout.py`. It does **not** change the owner's dirty local Git tree, primary Rails container, primary PostgreSQL, original uploads, public GitHub `master`, or port 3001.

Owner-verified evidence: 8 legacy files (~8.6 MB) in `public/uploads` backed up with SHA-256 matching copies; `uploads.tar.gz` checksum verified; PostgreSQL `cafe.dump` checksum and isolated restore (10 tables) verified; CarrierWave+MiniMagick file smoke and isolated QA Rails SQL/avatar save+thumb+cleanup PASS; live `http://127.0.0.1:3001/info` and QA `http://127.0.0.1:3002/menu` HTTP 200; new QA web `cafe-app-uploads-qa-db-20261103` reaches isolated PostgreSQL.

QA-only replacements (already produced and source-verified on the owner's Linux):
- `~/.local/share/cafe_app/qa_avatar_overrides_20261103/app/controllers/application_controller.rb`
- `~/.local/share/cafe_app/qa_avatar_overrides_20261103/app/views/devise/registrations/new.html.erb`
- `~/.local/share/cafe_app/qa_avatar_overrides_20261103/app/views/devise/registrations/edit.html.erb`

Script verifies that original 3 local files have the known pre-override Git blob IDs and QA overrides contain form fields and Devise sanitizer. This is **required**: all local apps share the read-only `/app` source mount, so editing source files would affect production immediately.

## Run on owner's Linux, not GitHub Actions

Use `git fetch` and `git show` to read script without checking out/merging any branch:

```bash
cd "$HOME/Рабочий стол/rails_projects/lite/cafe_app"
git fetch --no-tags origin feature/cafe-qa-avatar-rollout-20261103
mkdir -p -m 700 "$HOME/.local/share/cafe_app"
git show origin/feature/cafe-qa-avatar-rollout-20261103:scripts/cafe_qa_avatar_rollout.py > "$HOME/.local/share/cafe_app/cafe_qa_avatar_rollout_20261103.py"
python3 -m py_compile "$HOME/.local/share/cafe_app/cafe_qa_avatar_rollout_20261103.py"
python3 "$HOME/.local/share/cafe_app/cafe_qa_avatar_rollout_20261103.py" --check
# Apply only if preflight succeeds and old QA port 3002 works:
python3 "$HOME/.local/share/cafe_app/cafe_qa_avatar_rollout_20261103.py" --apply
```

Expected output includes `PREFLIGHT PASS`, `QA AVATAR REGISTRATION HTML PASS`, `QA PORT 3002 AVATAR FORM PASS`, `PRODUCTION PORT 3001 HTTP 200`, `QA AVATAR WEB READY`. Existing QA proxy remains as stopped rollback candidate. New avatar-enabled QA Rails and the proxy use only QA networks, QA PostgreSQL and QA uploads.

If --apply stops with a mismatch or partial resource creation, do **not** blindly retry; inspect newly created QA containers first. Do not remove any old container or Docker volume.

## Acceptance gates / next release steps

1. Browser on port 3002: verify signup form shows file input; register a disposable QA account using a disposable/known-safe sample JPG, PNG or GIF; check redirect, `/account`, thumb and saved file. No personal photo. Validate wrong extension and oversized files fail safely. If file constraints are absent, **do not release uploads**; add server-side MIME/type and size validation.
2. Before integrating avatar code, reconcile tracked Github `User` and `db/schema.rb` with local protected files. Upstream User lacks `mount_uploader :avatar` and `users.avatar`; these **do exist locally**. Don't overwrite `app/models/user.rb`, migration, schema, image uploader, or `app/views/layouts/application.html.erb`. Proper production implementation needs a reviewed migration/model/updater configuration and unique uploads volume; environment toggles should fail closed without that volume.
3. QA acceptance: registration/login/edit/password-reset UX, admin role restrictions, product/category CRUD safe delete, catalogue/cart, mobile 320/390/430, a11y keyboard, real image persistence after restart, CSRF and invalid inputs. GitHub Draft PR #27 Ruby 115 tests / 831 assertions, JS/Webpack PASS; not locally imported yet. Evaluate PR #28 separately before merging.
4. Backup + production cutover: stop primary Rails only after automated QA and release approval, recreate web with same image/networks/ports/uid/secrets/tmpfs/readonly volumes, add scoped writable bind `~/.local/share/cafe_app/uploads` at `/app/public/uploads`; verify, rollback to old stopped container if smoke fails. Re-enable avatar only after positive evidence, not just a successful local file smoke.
5. Modernize Ruby 2.5/Rails 6 in incremental supported-version stages, security/dependency audit, repeatable CI, seed idempotency, separate Railway cafe project and **approved budget**, persistent storage, HTTPS, monitoring, backups and independent release/rollback before public demo. No real checkout/payments.
6. Portfolio: source-verified screenshots and RU/EN honest case copy, architecture/tests/deploy documentation, 20–60s screen demo and assets in existing Drive `06_CAFE_APP_CANDIDATE` folders; verify permission/licensing, never upload user avatars/DB dumps/private docs. Publish verified public demo links before promoting freelancing.

**Not yet confirmed:** browser upload, browser signup with photo, full local admin QA, public deployment, HTTPS, payment system (not in scope), production persistence. No merges/publish actions should be inferred.

## Rollback and privacy

If new proxy fails, the script attempts stopping the new QA proxy and restarting `cafe-upload-qa-proxy-db-20261103`. It keeps both QA Rails containers and original QA DB/media; never deletes or resets them. If host is compromised or DB/secret mount differs from the verified baseline, stop with explicit diagnostics. Avoid Git-tracking or Drive-uploading original `public/uploads`, `cafe.dump`, secrets, or real accounts.
