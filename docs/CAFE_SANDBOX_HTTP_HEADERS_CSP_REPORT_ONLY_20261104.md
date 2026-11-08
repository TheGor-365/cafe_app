# Gor's Coffee — candidate HTTP headers and CSP Report-Only (2026-11-04)

## Owner-observed audit inputs
- A SHA-pinned **read-only** Rails sandbox audit (Draft PR #43) observed `/users/sign_up` and `/info` HTTP 200, `nosniff=YES` and `Referrer-Policy=YES`, but no CSP and no CSP Report-Only.
- An existing **private** sandbox JPEG returned 200 and `image/jpeg` to HEAD, but lacked `X-Content-Type-Options: nosniff` and `Referrer-Policy`.
- Draft PR #44 candidate `MAGICK_*` subprocess resource limits were verified by the owner: 30s time, 8KP width/height, 32MP pixel-cache area, 128 MiB memory, 256 MiB map, 512 MiB disk, 2 threads, 64 cache files; synthetic 10000x1 failed; real private JPEG decoded and SHA256 unchanged; original ten media hashes and 3001/3002 health rechecked.
- **None of these findings means public uploads or production are safe**. Sandbox Rails runs in development; private uploads and local DBs must not be exposed.

## Candidate under review — not loaded in any live/QA instance
`qa/security/cafe_headers_candidate.rb` is a pure-Ruby Rack middleware proposal. It has no initializer and **is not auto-mounted**. Tests run without Rails or Docker.

If mounted outermost around a **new independent** QA Rails process, it:
1. Fills **missing** `X-Content-Type-Options: nosniff` and `Referrer-Policy: strict-origin-when-cross-origin` on all Rack responses, including HTML and static JPEG HEAD/GET **only if those responses pass through the Rack stack**.
2. Adds `Content-Security-Policy-Report-Only` to `text/html` replies only. This prototype deliberately never adds or overwrites enforcing `Content-Security-Policy`; it does not permit `unsafe-inline` in the proposed script policy and includes Google Fonts origins for diagnostic compatibility.
3. Preserves any preexisting header **case-insensitively**, the original header hash, HTTP status, body, MIME type, caching and content-length. It does not read private image bodies, cookies, credentials, file paths or violation reports.
4. Uses only Ruby features compatible with the older Ruby 2.5 syntax, but does **not** establish tested compatibility with the owner's full Rails runtime.

### Important CSP reporting caveat
This candidate intentionally includes **no collector**, `report-uri`, `report-to`, or `Reporting-Endpoints`. It cannot be represented as a functioning centralized report collection system. On a separately approved, isolated QA browser, inspect the **Network** panel for the proposed header and **Console** for any browser-visible CSP policy diagnostics. Some browsers will not provide actionable reporting without a configured endpoint. Do **not** publish a reporting endpoint or accept uncontrolled reports containing URLs and user data. A private, appropriately scoped endpoint needs separate review.

### Existing source constraints
- In `config/initializers/content_security_policy.rb`, the example Rails CSP policy is commented out; the code under review doesn't activate it.
- `app/views/layouts/application.html.erb` uses external Google Fonts; JavaScript and legacy jQuery/Toastr may use inline/eval-like patterns. A strict **enforcing** CSP could break the current UI; `Report-Only` only is appropriate for initial diagnosis.
- `ActionDispatch::Static` is Rails' static-file middleware when `public_file_server.enabled` is true. A candidate middleware configured **before index 0** could see it in a new QA Rails runtime; reverse proxy/Nginx/Railway static-file serving can bypass Rails entirely. Verify real GET and HEAD through the actual QA delivery path before claiming JPEG headers.
- Existing sandbox and QA/live services have distinct networks, PostgreSQL clusters and private media. **Do not mount this candidate in an existing running service, edit its app source, restart it, or change its port/proxy.**
- No reports are collected by GitHub CI; it only tests synthetic Rack response triples.

### Candidate integration design — future, separate QA instance only
Rails provides `config.middleware.insert_before 0, CafeHeadersCandidate` for outermost insertion, after explicitly requiring the reviewed module in a **separate** Rails startup config. This is a design sketch, **not an action performed**. A new immutable source overlay or independent QA process and rollback plan must be validated first.

Accept only if:
- Actual isolated QA `/users/sign_up`, `/info` GET 200, HTML `nosniff`, `Referrer-Policy` and CSP **Report-Only only**; any pre-existing enforced CSP must be inventoried.
- Private QA JPEG GET and HEAD 200 and correct `image/jpeg`, `nosniff` and `Referrer-Policy`; media SHA unchanged and no path or bytes exposed to public GitHub/Drive.
- Browser checks of menu, cart, product panel, sign-in/up, avatar upload, admin and mobile/desktop CSS/JS. Absence of broken UI is not proof of a future enforcing CSP because Report-Only is not enforced.
- Original 3001/3002 local ports remain HTTP 200; three PG IDs distinct; media snapshots identical. No original source or Docker modifications.
- Additional decoder/re-encode and malicious payload tests, supported Ruby/Rails upgrade and signed-off release checklist remain P0.

## Reference material
- Rails documentation: https://guides.rubyonrails.org/configuring.html (middleware stack and outermost index)
- Rails static middleware: https://edgeapi.rubyonrails.org/classes/ActionDispatch/Static.html
- CSP Report-Only reporting requirements: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy-Report-Only
- MDN CSP test/evaluation: https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP

**Status:** proposal + automated pure-Ruby regression; no sandbox Rails integration, browser validation, or public release.
