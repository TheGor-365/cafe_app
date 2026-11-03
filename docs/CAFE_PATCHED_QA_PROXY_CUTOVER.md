# Gor's Coffee — QA proxy switch to patched CarrierWave 2.2.7 (2026-11-04)

## Confirmed prerequisite

Owner ran Draft PR #34 patched Rails candidate `--smoke` on Linux. Terminal confirms `PATCHED RAILS/SQL/AVATAR POLICY PASS`, `PATCHED QA INTERNAL HTML 200 PASS`, `LIVE 3001 AND EXISTING QA 3002 UNCHANGED`, `PATCHED QA CANDIDATE INTERNAL SMOKE PASS`. Candidate is running **only on internal QA network**, no host ports. Patched gems are from isolated private bundle. Both original servers and original QA data still exist.

## Controlled switch

Use `scripts/cafe_patched_qa_proxy_cutover.py --check` to validate production and QA network isolation, exact existing proxy name/target, production HTTP, current QA HTTP, patched web's actual 2.2.7 gem, readonly project, staged Gemfile/lock and uploader, distinct QA PostgreSQL cluster, and loopback-only port. All checks are read-only.

If it passes, `--switch` creates a NEW proxy named `cafe-upload-qa-proxy-patched-20261104` attached only to QA access and QA internal networks, mapping only `127.0.0.1:3002`. It does not start while old QA proxy owns port 3002. Once created and configuration-verified, old QA proxy is stopped, new proxy starts, and `/menu` plus multipart signup HTML must return 200. Main `127.0.0.1:3001/info` must remain 200. On failure, script attempts to stop new proxy and restart old, without deleting any data or containers.

Do **not** remove old proxy, old QA Rails, QA DB or uploaded media.

## Important storage caveat

**Old QA and patched QA point to the same QA PostgreSQL but separate directories for uploaded files.** A rollback after any new QA user/avatar is created in the patched media directory can leave database rows referring to media that the old QA cannot read. For now, verify only the guest forms and existing media; **do not submit a new upload during the initial proxy switch**. Before testing real multipart uploads, take and verify a fresh QA DB/media snapshot, plan a reversible rollback and keep new uploads as disposable fixtures. Never treat an HTTP smoke alone as proving secure uploads.

## Next security tests

Test valid and invalid real multipart payloads in QA only; ensure invalid SVG/HTML, wrong MIME, size >2 MiB, corrupt/truncated images and path traversal fail cleanly without persisted records/files. Verify persisted original/thumbnail after restart. Test MIME according to both true bytes and server inspection. Audit ImageMagick/mini_magick conversion, pixel/time limits, response `nosniff`, CSP, authenticated session, CSRF and rate limits. Ruby 2.5/Rails 6 EOL still blocks serious public deployment.

Current PRs remain Draft and unmerged, with GitHub CI providing only syntax/logic safeguards, not owner's browser acceptance.
