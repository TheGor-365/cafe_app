# Cafe App — integration checkpoint (2026-11-01)

Original GitHub master: `06f66f3d318e1a3fe3e5683baf541f5fec8b4c01` (2021). This isolated integration branch combines four separately CI-tested Draft PRs, **without merging to master**:

- [PR #1](https://github.com/TheGor-365/cafe_app/pull/1): server-side guest/user/admin ACL; 18 tests / 60 assertions PASS.
- [PR #3](https://github.com/TheGor-365/cafe_app/pull/3): order-item pricing, quantity validation, forged product-ID rejection, request coverage; 8 tests / 30 assertions PASS.
- [PR #4](https://github.com/TheGor-365/cafe_app/pull/4): escaped flash HTML instead of unsafe `<script>`; 4 tests / 21 assertions PASS.
- [PR #5](https://github.com/TheGor-365/cafe_app/pull/5): menu search, dietary filter whitelist, missing AJAX template; 6 tests / 54 assertions PASS.

The combined branch must pass its **own** CI before being treated as integrated.

## Critical local distinction
Owner's laptop has uncommitted files (Gemfile/lock, avatar/uploaders, migrations/schema and modified layout), plus untracked uploaded files. The GitHub branch excludes those local-only bytes; they were never exported to GitHub. Do not reset, clean, overwrite, or merge directly into dirty local worktree. Local private source backup confirmed at `~/Backups/cafe_app/before_modernization_2026-11-01` (129 MB).

## Constraints
- GitHub master locks older Rails 6.0.3.6 and Ruby 2.5.8; user's local lock uses Rails 6.0.6.1 on Linux. Reconcile and test this difference.
- CI's temporary Webpacker manifest validates server routes/rendering, **not a real JS asset build**.
- Remaining P0: layout caching around user identity, legacy demo-admin seeds, storage/license checks, two-session isolation, real UI/Node/Yarn smoke and staged Ruby/Rails upgrade.
- No Railway service, database migrations, public demo/payment, deployed app or published portfolio screenshots have been claimed.
