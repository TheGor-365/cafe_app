# Gor's Coffee — Ruby on Rails portfolio demo

**Educational showcase, not a real café.** Fictional menu and orders; no payment processing, delivery, fulfilment, or customer support. Please use synthetic names and notes only.

[Русский](#русский) · [English](#english) · [Source](https://github.com/TheGor-365/cafe_app) · [Release checklist](docs/CAFE_RELEASE_CHECKLIST.md)

> **Public portfolio preview · 9 November 2026:** `master` uses ordinary Devise **Sign in / Sign up**, guest access and role-protected admin. No separate preview password or HTTP Basic gate. Existing `Eric` is admin; new accounts are non-admin. **Not production-grade:** Ruby 2.7, Rails 6.1 and Node 14 are end-of-life; no real payment or fulfilment. External HTTP and favicon checks are part of release verification.

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

**Технологии действующей версии:** Ruby 2.7.8, Rails 6.1.7.10, PostgreSQL, ERB, Sass/Sprockets, Bootstrap, JavaScript/Webpacker 4, Devise, CarrierWave, Minitest, Docker, Railway. **Ruby 2.7, Rails 6.1 и Node 14 устарели и больше не поддерживаются.** Для коммерческого production-развёртывания необходимы обновление поддерживаемого стека и security review; текущий URL — открытая демонстрация без реальных клиентов и платежей.

### Факты и ограничения

- Подтверждённая изолированная CI-проверка функциональной ветки: [PR #71 / run 42412310443](https://github.com/TheGor-365/cafe_app/actions/runs/42412310443) — **158 tests, 1328 assertions, 0 failures/errors**. Она не доказывает работу Docker/Railway.
- Промежуточная миграция на Ruby 2.7/Rails 6.1 отдельно прошла [CI run 42428798391](https://github.com/TheGor-365/cafe_app/actions/runs/42428798391). Rails 7.0 проверен только как следующий **неподдерживаемый** промежуточный этап.
- Изолированный Railway-проект `gors-coffee-cafe-app` использует **отдельную** PostgreSQL 18. URL https://cafe-web-preview.up.railway.app открывает витрину без дополнительного пароля; Devise реализует регистрацию и вход. Управление каталогом и заказами доступно только роли `admin`. Локальные базы не затрагиваются.
- Права на некоторые старые фотографии товаров не подтверждены. Не публиковать чужие материалы без разрешения.
- Регистрация и вход через Devise работают без дополнительного пароля preview; отправка писем для восстановления пароля не настроена и не должна считаться рабочей.
- Медиахранилище в Railway **не настроено как постоянное**: локальные uploads нельзя считать надёжно сохраняемыми при повторных деплоях.
- Нет реальных клиентов, транзакций, онлайн-оплаты, интеграции доставки или подтверждённой коммерческой эксплуатации.

### Локальный запуск для разработчика

Использовать **новую временную PostgreSQL базу** и изолированное окружение. Текущие команды рассчитаны на нынешний `master` с Ruby 2.7/Rails 6.1 и только на отдельную временную базу.

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
- Открытый сайт не использует HTTP Basic или preview gate: гости видят витрину, пользователи входят через Devise, а административные действия защищены ролью `admin`. Railway использует публичный `GET /__cafe_health` с проверкой PostgreSQL. Не вводите реальные личные или платёжные сведения: стек требует обновления для коммерческой эксплуатации.

### Портфолио

Для презентации предусмотрены RU/EN-кейс, 20 подлинных скриншотов после проверенного запуска и отдельный видео-storyboard. Синтетический контент маркировать как `demo`. Не публиковать адреса, токены, пароли или реальные личные данные.

## English

Gor's Coffee is an **educational Rails coffee-shop demo**, not an operating business. It showcases a searchable catalog, configurable drinks, cart deduplication, server-calculated prices, a fictional checkout, scoped order history, admin CRUD and order statuses, responsive UI, and automated tests.

**Current showcase stack:** Ruby 2.7.8, Rails 6.1.7.10, PostgreSQL, Webpacker 4/Node 14, Devise, CarrierWave, ERB/Sass, Minitest, Docker and Railway. Ruby, Rails and Node versions in this branch are end-of-life. Successful isolated tests are **not** proof of public production readiness.

**Demo data:** 8 categories, 20 products, 6 configurable drinks. No payments, fulfilment, real customers or production orders. Product-media redistribution rights are not fully verified. Upload durability and password-recovery email are not production-ready.

**Reproducibility:** use only a clean disposable PostgreSQL database; never reset the owner's existing development or QA databases. Set `RUBYOPT=-rlogger` for this Rails 6.1 bridge. See the technical and release sections above.

**Evidence:** [158 tests / 1328 assertions (PR #71 CI)](https://github.com/TheGor-365/cafe_app/actions/runs/42412310443); [Ruby 2.7/Rails 6.1 regression CI](https://github.com/TheGor-365/cafe_app/actions/runs/42428798391); [Rails + Docker release CI](https://github.com/TheGor-365/cafe_app/actions/runs/42519024703) **SUCCESS**. Railway showcase: https://cafe-web-preview.up.railway.app (public storefront; Devise Sign in / Sign up; admin restricted by role). Fictional orders only, no real payments. Final browser screenshots are pending.

---

Historical implementation notes: [pre-release README archive](docs/README_ARCHIVE_PRE_RELEASE_2026-11-07.md). Development documentation and handoff: [docs/](docs/).
