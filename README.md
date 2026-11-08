# Gor's Coffee — Ruby on Rails portfolio demo

**Educational showcase, not a real café.** Fictional menu and orders; no payment processing, delivery, fulfilment, or customer support. Please use synthetic names and notes only.

[Русский](#русский) · [English](#english) · [Source](https://github.com/TheGor-365/cafe_app) · [Release checklist](docs/CAFE_RELEASE_CHECKLIST.md)

> **Preview release · 9 November 2026:** integrated source on `master`, Railway `preview` environment with its own PostgreSQL, HTTPS healthcheck and automated Rails/Docker checks. Account creation and sign-in use one Devise flow, with no second shared preview password. Owner administration requires a one-time code configured in Railway only. This is a non-commercial portfolio app on **unsupported Ruby 2.7 / Rails 6.1 / Node 14**, not a supported public production service. Never use actual card data or customer information. Authenticated owner-browser QA is still required.

## Русский

### Что демонстрирует проект

Gor's Coffee — учебный full-stack веб-сервис кафе для портфолио Ruby on Rails-разработчика.

- Каталог с поиском, фильтрами, категориями, карточками товаров и адаптивной навигацией.
- Демонстрационный набор: **8 категорий, 20 товаров, 6 настраиваемых напитков**.
- Размеры S/M/L, выбор молока, сиропа и дополнительного эспрессо.
- Корзина, изменение количества, объединение одинаковых конфигураций.
- **Цена проверяется на сервере**; итог и дополнения сохраняются снимком заказа.
- **Вымышленный checkout**, история заказов, доступ к заказам по сессии/владельцу, админская очередь и статусы.
- Административное управление категориями, товарами и настройками напитков с серверными проверками прав.
- Адаптивные интерфейсы, Devise, Minitest, интеграционные проверки и GitHub Actions.

**Технологии текущей промежуточной ветки:** Ruby 2.7.8, Rails 6.1.7.10, PostgreSQL, ERB, Sass/Sprockets, Bootstrap, JavaScript/Webpacker 4, Devise, CarrierWave, Minitest, Docker, Railway. **Ruby 2.7, Rails 6.1 и Node 14 устарели и больше не поддерживаются.** Переход на поддерживаемые версии — обязательное условие публичного релиза.

### Факты и ограничения

- Подтверждённая изолированная CI-проверка функциональной ветки: [PR #71 / run 42412310443](https://github.com/TheGor-365/cafe_app/actions/runs/42412310443) — **158 tests, 1328 assertions, 0 failures/errors**. Она не доказывает работу Docker/Railway.
- Промежуточная миграция на Ruby 2.7/Rails 6.1 отдельно прошла [CI run 42428798391](https://github.com/TheGor-365/cafe_app/actions/runs/42428798391). Rails 7.0 проверен только как следующий **неподдерживаемый** промежуточный этап.
- Приватный Railway-проект `gors-coffee-cafe-app` имеет **отдельную** PostgreSQL 18 и защищённую тестовую точку входа: https://cafe-web-preview.up.railway.app. Внешний `GET /__cafe_health` подтверждён, авторизованное browser QA ожидается. Локальные пользовательские базы и загруженные файлы не затрагиваются.
- Права на некоторые старые фотографии товаров не подтверждены. Не публиковать чужие материалы без разрешения.
- Регистрация и восстановление пароля по почте не должны считаться готовыми к реальному использованию, пока не настроена и не проверена отправка писем.
- Медиахранилище в Railway **не настроено как постоянное**: локальные uploads нельзя считать надёжно сохраняемыми при повторных деплоях.
- Нет реальных клиентов, транзакций, онлайн-оплаты, интеграции доставки или подтверждённой коммерческой эксплуатации.

### Локальный запуск для разработчика

Использовать **новую временную PostgreSQL базу** и изолированное окружение. Текущие команды рассчитаны на промежуточную ветку Ruby 2.7/Rails 6.1, не на исторический `master`.

```bash
bundle _2.2.13_ install
yarn install --frozen-lockfile
# DATABASE_URL должен указывать ТОЛЬКО на новую временную БД.
RUBYOPT=-rlogger RAILS_ENV=test bundle _2.2.13_ exec rails db:schema:load
RUBYOPT=-rlogger RAILS_ENV=test bundle _2.2.13_ exec rails test
```

Для разработки пользовательского интерфейса: в отдельной development-БД подготовить схему, выполнить разрешённые demo-seeds только там, затем запустить Rails; JS-паки собираются Webpacker. Существующий рабочий каталог владельца, `localhost:3001/3002`, Docker volumes и частные базы **не трогать и не сбрасывать**. Никогда не выполнять `db:drop`, `db:reset` или повторный seed на существующих пользовательских базах.

### Railway

- Изолированный проект `gors-coffee-cafe-app`, окружение `preview`, сервис `cafe-web` + отдельный Postgres с томом.
- Сборка из `Dockerfile`; `SECRET_KEY_BASE` задаётся через секреты Railway; `DATABASE_URL` — только приватное соединение.
- Разрешённый demo-bootstrap ограничен конкретными Railway project ID, environment ID и `CAFE_PREVIEW_SEED_ALLOWED=YES`. Он не создаёт учетных записей и не должен переноситься в другие среды.
- Docker/CI сборка, миграции, запуск Puma, внутренний healthcheck и внешняя HTTPS-проверка `GET /__cafe_health` подтверждены. Вход и регистрация выполняются через Devise, без дополнительного общего пароля. Для назначения владельцу роли администратора используется отдельный однократный секрет в Railway; его нельзя публиковать или передавать в сообщениях. Открытая эксплуатация как реального бизнеса запрещена до обновления стека и проверок безопасности/медиа.

### Портфолио

Для презентации предусмотрены RU/EN-кейс, 20 подлинных скриншотов после проверенного запуска и отдельный видео-storyboard. Синтетический контент маркировать как `demo`. Не публиковать адреса, токены, пароли или реальные личные данные.

## English

Gor's Coffee is an **educational Rails coffee-shop demo**, not an operating business. It showcases a searchable catalog, configurable drinks, cart deduplication, server-calculated prices, a fictional checkout, scoped order history, admin CRUD and order statuses, responsive UI, and automated tests.

**Current intermediate stack:** Ruby 2.7.8, Rails 6.1.7.10, PostgreSQL, Webpacker 4/Node 14, Devise, CarrierWave, ERB/Sass, Minitest, Docker and Railway. Ruby, Rails and Node versions in this branch are end-of-life. Successful isolated tests are **not** proof of public production readiness.

**Demo data:** 8 categories, 20 products, 6 configurable drinks. No payments, fulfilment, real customers or production orders. Product-media redistribution rights are not fully verified. Upload durability and password-recovery email are not production-ready.

**Reproducibility:** use only a clean disposable PostgreSQL database; never reset the owner's existing development or QA databases. Set `RUBYOPT=-rlogger` for this Rails 6.1 bridge. See the technical and release sections above.

**Evidence:** [158 tests / 1328 assertions (PR #71 CI)](https://github.com/TheGor-365/cafe_app/actions/runs/42412310443); [Ruby 2.7/Rails 6.1 regression CI](https://github.com/TheGor-365/cafe_app/actions/runs/42428798391); [release Rails + Docker + Basic gate CI](https://github.com/TheGor-365/cafe_app/actions/runs/42519024703) **SUCCESS**. Railway preview: https://cafe-web-preview.up.railway.app (Devise registration/sign-in; owner claim protected with Railway-only secret). Authenticated owner-browser proof and final screenshots are pending.

---

Historical implementation notes: [pre-release README archive](docs/README_ARCHIVE_PRE_RELEASE_2026-11-07.md). Development documentation and handoff: [docs/](docs/).


### Account and owner preview walkthrough (November 2026)

1. Open the Railway preview URL. Choose **Sign in** or **Create account**. These are standard Devise forms; registration cannot assign `admin`.
2. Sign in with the existing owner account. For the **first** owner activation only, open `/owner/access` and enter `CAFE_OWNER_CLAIM_TOKEN` from the Railway **cafe-web → Variables** panel. Access is restricted to the account matching `CAFE_OWNER_USERNAME`, to the specific Railway project/environment and to a database without an existing administrator.
3. Once activated, **Manage products**, **Manage categories**, **Orders**, and drink size/add-on configuration appear in the owner navigation. These actions are still guarded on the server.
4. Never paste the claim token, passwords, real customer information or payment data into chat or screenshots. Screenshot collection uses 10 desktop + 10 mobile views; keep originals unaltered.

**Scope limit:** Marketing copy no longer repeats “demo” on every screen, but the footer retains a clear portfolio/no-payment disclosure. Email password-reset delivery and persistent uploads remain unverified; no live ordering or money movement is supported.
