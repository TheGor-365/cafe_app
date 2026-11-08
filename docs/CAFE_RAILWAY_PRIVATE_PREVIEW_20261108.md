# Cafe App — Railway isolated preview (2026-11-08)
**NOT a public production release.** Ruby 2.7 / Rails 6.1 are EOL. Keep web service without a public Railway domain until supported-stack migration or a reviewed authenticated proxy.
Source: this branch, forked from tested PR #75 SHA afec154c8bc01644201be56b8ade597ce3e959f9; does not alter master, owner-local databases, or other Railway applications.

Railway project: a6c48a67-c6f4-4f12-a5df-6d1de0f45d69
Railway environment: e47229ba-6dd7-47ec-9155-a329bb2a963c (preview)
Postgres: new independent private Railway Postgres, referenced as ${{Postgres.DATABASE_URL}}.
Expected web runtime: RAILS_ENV=production, SECRET_KEY_BASE from Railway variable, NODE 14 build, Bundler 2.2.13, port 3000.

Deploy pre-command: `bundle _2.2.13_ exec rails db:migrate && bundle _2.2.13_ exec rake cafe:bootstrap_preview`.
The seed task refuses any project/environment except the above, requires CAFE_PREVIEW_SEED_ALLOWED=YES and a private `.railway.internal` DATABASE_URL. It initializes only missing demo catalog, never user accounts or payments. No production license/security guarantee is implied.

Gates before user screenshots: terminal Railway deployment SUCCESS, private route HTTP checks, assets, no 5xx, auth/checkout/ACL browser check through protected HTTPS gateway. Persisted media needs a separate storage decision. Work toward currently maintained Ruby/Rails before unrestricted public launch.
