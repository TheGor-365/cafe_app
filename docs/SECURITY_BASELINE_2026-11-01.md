# Cafe App — server-side admin ACL baseline (2026-11-01)

Source: GitHub `TheGor-365/cafe_app`, base `master` at `06f66f3d318e1a3fe3e5683baf541f5fec8b4c01`.

## Findings
- Product/category mutations lacked controller-side authorization; hiding admin links does not protect HTTP requests.
- Legacy integration tests expected anonymous writes and omitted product category IDs.
- Placeholder user fixtures collided with the unique email index.

## This branch
- Require Devise authentication for new/create/edit/update/destroy on both resources.
- Respond 403 to authenticated non-admins, relying on existing `User.admin`.
- Preserve public index/show.
- Cover all five protected actions in negative request tests for guests/regular users.
- Update positive tests to use real test admins and valid category IDs.
- Replace invalid user fixtures with non-authenticating placeholders.

## Verification limitations
Code prepared for review. **No tests or CI have run.** The GitHub branch is based on remote `master`, so it does not contain any uncommitted local Gemfile, lockfile, UI, migration, avatar, or media changes. Validate before combining with the local dirty branch.

## Deferred separate P0 items
Layout cache/session isolation; unsafe toast script interpolation; cart pricing/quantity; fixed admin seed passwords; legacy dependency support; upload validation and persistent media.
