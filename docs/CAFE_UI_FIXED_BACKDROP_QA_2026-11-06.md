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

## Owner-local exact layout reconciliation — 07.11.2026

Owner supplied the actual dirty Linux \`app/views/layouts/application.html.erb\` and its Git blob \`1c5550e55e653cf204f0f6910b1251b2dc0e4320\`. The content is reproducible byte for byte and includes a Bootstrap 4.6.2 / jQuery 3.5.1 CDN head, \`current_user&.avatar&.url(:thumb)\` via CarrierWave, Rails \`button_to ... method: :delete\`, footer, and a four-column grid. The original published PR #65 template was NOT the same owner source. Previous 06.11 installer \`cafe_ui_reviewed_local_install_20261106.py --check\` rejected the dirty layout correctly and **must not be used with --apply**.

New compatible source patch (in PR #65) preserves the local head/CDNs and avatar thumb, retains native Rails DELETE sign-out form, removes only the blank guest avatar/account split, and adds the shared \`cafe-page\` class/semantic main. The stylesheet styles the sign-out form and persistent shell.

New separate owner-local script: \`scripts/cafe_ui_local_layout_adapter_20261107.py\`, with three modes: \`--check\` read-only, later \`--apply\` after approval, and \`--verify\` read-only postflight. It refuses anything except exact original SHA \`1c5550e55e653cf204f0f6910b1251b2dc0e4320\`, deterministic patched SHA \`85ab9031ec6fd13bdefb735588cf46f570daea11\`, and stylesheet SHA \`e3c73d446bfc0126a58a644e5afb96fe5a36c173\` pinned at commit \`28e4c145d09e44cb34377fae0c36b60f9d563bcf\`. It adds only ONE CSS file, edits only one ERB, makes a private 0700/0600 backup first, never touches original uploads, data, Docker, dirty Git history or one-shot markers. No user-local write has been executed at this checkpoint. If preflight fails, preserve state; never bypass the SHA by weakening the script.

Follow-up live visual gate: after an independently reviewed --apply and --verify PASS, check actual localhost:3001 in Chrome at desktop and 320/360/390 mobile widths; verify top/mid/bottom static background and three sticky areas, guest links, signed-in thumb+username+DELETE logout, overlays/CSRF/cart and left navigation. A GitHub CI success is not a deployment or local browser PASS.

## Header top-lock correction — owner screenshot 07.11.2026

Owner supplied a real localhost:3001/users/sign_in screenshot after the prior UI apply. Account Sign in/Sign up is visually unified and user reports scroll works, but central Gor's Coffee brandbar moves ~10–14px vertically between its natural and sticky positions. Root cause from reviewed styles: `zz_cafe_layout_reflow.scss` adds `.col-8 {padding:.85rem}`, while `zzzzz_cafe_unified_shell.scss` positions the central brandbar `sticky;top:0`. The first scroll consumes the initial padding offset.

Remedy in independent append-only style `app/assets/stylesheets/zzzzzz_cafe_sticky_top_lock.scss`: main `#cafe-main-content` padding-top 0, desktop header sticky top 0 and right Account top/margin 0; mobile header retains sticky top 120px after nav+account 60px each. Does not alter existing layout, guest/auth Devise, media, DB, uploads, or Docker. Regression test in `coffee_unified_shell_test.rb` checks page/brand markup and SassC style compilation; GitHub CI only, not real browser acceptance.

Owner-local guarded installer: `scripts/cafe_sticky_header_top_lock_20261107.py`. Read-only `--check` requires exact existing owner-local patched ERB blob `85ab9031ec6fd13bdefb735588cf46f570daea11` and prior CSS blob `e3c73d446bfc0126a58a644e5afb96fe5a36c173`, expected dirty branch and absence of the new stylesheet. Later `--apply` performs one exclusive file create with reviewed Git CSS blob `64fcaa6462b3e60580f4548df9448d04ca9e493f` from immutable commit `dd31cd7244fd786ba654bcf1e037454b81f37873`; `--verify` is a separate read-only postflight. Refuse on unexpected source. Owner must explicitly execute, no local writes were performed by GitHub.

Password reset: Devise User has `:recoverable` and branded Forgot Password form. However development config has localhost:3000 mailer URL and ignores delivery errors, while production has no verified SMTP delivery. Password reset emails are **not** verified on owner 3001; no credential extraction, password reset or write to protected DB has been done. If recovery link fails, plan owner-authorized targeted recovery in an isolated process after approval and backup. No fake admin credentials.
