# Cafe Rails 6.1 / Ruby 2.7 — isolated upgrade stage

This branch is an intermediate upgrade candidate only; do not deploy publicly.
Parent source: Draft PR73 b62998c58b13f6322d581c2bd5b3ceb0c383db87.
Reference CI: https://github.com/TheGor-365/cafe_app/actions/runs/42427952297
Full Rails suite passed in disposable CI with Ruby2.7.8/Rails6.1.7.10:
158 tests, 1328 assertions, zero failures, zero errors and zero skips.

Reproducible Gemfile/Gemfile.lock for this candidate are imported directly
from the successful GitHub artifact ID 13596810048, with SHA-256 checks:
- Gemfile: 7d059de9e1bb03c178ba7b2ff9c7947fba3c067b92d8d5c040c6142b0743b544
- Gemfile.lock: f5803e40308ac3ab519f886f6afff84cebffd9534616dc30e81f4537e7f7e1ff

The one-time GitHub Actions promotion may update only Gemfile, Gemfile.lock
and .ruby-version on THIS feature branch. It must not merge to master,
repoint the owner's Docker PGs, restart ports 3001/3002/3003,
copy uploads, or create public cloud resources.

After artifact promotion, verify full Rails suite again using the locked
files in GitHub CI on a fresh, disposable PostgreSQL 16 instance.
Do not claim Rails 8 compatibility or supported public readiness.
