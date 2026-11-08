# Gor's Coffee: Rails 7.0 migration probe (2026-11-08)

Isolated CI-only diagnostics stacked on Draft PR75, which pins tested
Ruby 2.7.8 and Rails 6.1.7.10. Rails 7.0.10 is final Rails7.0 release,
but this line is EOL; never deploy it publicly.

Official sources:
https://guides.rubyonrails.org/v7.0.10/7_0_release_notes.html
https://rubyonrails.org/2025/10/29/new-rails-releases-and-end-of-support-announcement

Scope: GitHub Actions disposable Ruby2.7.8 + PostgreSQL16, tested source
from PR75, only CI-local Gemfile/lock mutations, temporary schema, full
Rails Minitest and artifact of resolved dependencies. Keep original
Webpacker4/Devise fork unchanged at this step; record failures explicitly.

Do NOT modify any owner localhost 3001/3002/3003, original PG/media,
fifth synthetic PG, local Git checkout, credentials or Railway deploy.

After CI: if green, create permanent locked stage and proceed Rails7.1.
Even a green Rails7.0 suite does not verify compiled JS/browser security
and does not make this unsupported Rails7.0 release production eligible.
