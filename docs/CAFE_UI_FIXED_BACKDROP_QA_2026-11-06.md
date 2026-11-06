# Cafe App UI fixed backdrop / unified account QA — 2026-11-06

Source base: PR #63 HEAD a69c18be95cb8d03515fd2d21c77271fb773490a.
Scope: independent public GitHub Draft PR. No owner-local checkout, Docker, database, uploads, marker or deployment modifications.

## Changes
- Replace the guest's empty avatar segment and disconnected Sign in/Sign up box with one responsive Account navigation card.
- Keep Devise routes, signed-in username/settings and DELETE sign-out; only render a user avatar when the runtime actually exposes a valid avatar URL. The current GitHub user schema has no avatar column, so a real local avatar appearance remains to be checked after comparing the owner's modified layout.
- Use one non-interactive viewport-fixed backdrop behind all common-shell pages. Preserve original extereor.jpg/menu.jpg/catering.jpg/info.jpg/reviews.jpg and the Cart gradient. Other routes (including Devise/Account/Admin/Product detail) use the exterior backdrop.
- Add disposable Rails 6 / Ruby 2.5 + PostgreSQL 16 integration tests and SassC SCSS compilation gate. GitHub CI is not real owner Linux or browser evidence.

## Required visual acceptance (not yet passed)
Guest, signed-in and admin: Home, Menu, Cart, Product detail, Info, Catering, Sign in, Sign up, Account, Admin; viewport widths 320, 360, 390, 768, 1024, 1440, 1648. Inspect top/middle/bottom scroll, immobile background, no horizontal overflow, keyboard focus, nav, clicks, dropdowns, auth, cart, modal stacking and touch targets. Test actual Chrome and mobile Safari where available; avoid claiming screenshots until owner supplies genuine captures. Compare the local dirty layout/CSS read-only before integration.

## Restrictions
Draft only. No PR merge, production/QA restart, original uploads/volumes modification or one-shot command replay. Separate fifth-only scoped-role --verify and P1.2 schema gate from UI. Private owner screenshots must not be copied to public GitHub.

## Sticky shell follow-up — owner screenshot 06.11

User's real localhost:3001/info still shows the old split account panel because prior PR #65 existed **only on GitHub**. Nothing had been applied to the local dirty checkout. The screen is not evidence of failure of the new CI-only UI code.

New acceptance requirement: while central document content scrolls, left `nav.cafe-sidebar`, the central `.cafe-brandbar.title-card` and right `nav.cafe-account-widget` stay visible. Desktop: each rail uses `position:sticky` within the grid, sidebar capped at viewport height with independent overflow-y if links exceed screen; brand bar sticks at top within main. Mobile <=760px: existing horizontally scrollable nav, account row and brand header use cumulative sticky top 0/60/120px. Do not transform/clip their grid ancestor or hide links in narrow layouts; real 320/360/390px visual/zoom verification is mandatory. Fixed backdrop remains non-interactive.

### Guarded owner local handoff (not yet executed)
Script: `scripts/cafe_ui_reviewed_local_install_20261106.py` within this PR. First `--check` is **read-only** (exact owner local branch/paths, current layout Git blob, absent new style, common nav/title/Sprockets source). If the user's ERB differs, STOP rather than overwriting owner edits. Later `--apply`, only after reviewing `--check` result, retrieves exact files from immutable commit `10cf64a63c51c146a0389ebc99376e20f659d10c`, checks Git SHA-1 blobs and makes a private 0700 backup before changing *only* the legacy layout and new CSS. No checkout/merge/rebase, Docker restart, SQL/volumes/uploads/one-shot marker change.

UI check does not validate old owner-upload avatar integration when the local layout hash mismatches. Browser/phone screenshots are private; no public PR screenshots, fake app views or claims of verified local behavior.
