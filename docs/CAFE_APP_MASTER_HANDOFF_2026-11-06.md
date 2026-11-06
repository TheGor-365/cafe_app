# CAFE APP — MASTER HANDOFF 2026-11-06
## CAREER / Gor's Coffee / продолжение разработки от последнего PASS

**Дата:** 6 ноября 2026, пятница, Asia/Yerevan.
**Репозиторий:** https://github.com/TheGor-365/cafe_app
**Предыдущий полный план:** [CAFE_APP_MASTER_HANDOFF_2026-11-05.md](CAFE_APP_MASTER_HANDOFF_2026-11-05.md). Данный документ является более новой точкой возобновления и исправляет устаревшие статусы из мастера 05.11. Предыдущий master содержит большой исторический roadmap и рабочие PR, читать его для деталей, но НЕ выполнять его старую секцию «первый шаг».

**Цель нового чата:** максимально автономно довести рабочий портфолийный Ruby on Rails demo Gor's Coffee через две новые визуальные починки, завершение безопасной интеграции, тестов, деплоя, документации и портфолио до согласованного релиза. Работать по фактам, не повторять уже завершённые действия. GitHub/Google Drive/Railway/Gmail connectors можно использовать для релевантных операций в рамках доступа; для локального Linux/Docker нет прямого доступа — давать пользователю 1 проверенную команду за раз. Число PR/CI запусков не KPI; KPI — релизный продукт, воспроизводимые тесты и проверенные коммерческие кейсы.

## 1. ТОЧНЫЙ СТАТУС И ПЕРВЫЕ ДЕЙСТВИЯ

**Самое последнее действие пользователя 06.11.2026:** ОДНОКРАТНО выполнено:
    python3 -B "$HOME/.local/share/cafe_app/cafe_p12_fifth_scoped_roles_v1_20261106.py" --provision

**РЕАЛЬНЫЙ OWNER STDOUT PASS:**
- P1.2 FIFTH SCOPED ROLES ONE-SHOT MARKER RECORDED
- P1.2 FIFTH-ONLY ATOMIC ROLE SQL APPLIED
- P1.2 FIFTH SCOPED OWNER NOLOGIN / APP LOGIN ACL PASS
- P1.2 FIFTH DEFAULT CRUD/SEQUENCE PRIVILEGES / APP DDL DENIED PASS
- P1.2 FIFTH CORRECT/INCORRECT SCRAM APP PASSWORD PASS
- P1.2 FIFTH ZERO DATA TABLES / FIVE DISTINCT PG / ORIGINAL WEB PASS
- P1.2 FIFTH SCOPED ROLES INDEPENDENT VERIFY PASS
- P1.2 FIFTH SCOPED ROLES RECOVERY COMPLETE — NO SCHEMA/SEED WRITES

Подтверждена реальная локальная пятая PostgreSQL + scoped-role транзакция, включая встроенную проверку. Отдельный независимый запуск роли --verify пока НЕ выполнен.

**ПЕРВОЕ действие владельцу, read-only:**
    python3 -B "$HOME/.local/share/cafe_app/cafe_p12_fifth_scoped_roles_v1_20261106.py" --verify

После PASS обновить PR #63 checkpoint; это НЕ требует SQL записей. ОДНОРАЗОВУЮ --provision никогда не повторять. Более старый --verify-empty тоже не запускать: он ожидал отсутствие LOGIN-ролей, а cafe_synth_app уже существует.

**ПАРАЛЛЕЛЬНО** без ожидания owner CLI: автономно изучить и начать отдельный Draft PR для двух UI-багов из §3. Сначала CI/source review, никаких изменений локальной dirty ветки или production Docker.

## 2. ОКРУЖЕНИЕ И ЗАЩИТА ДАННЫХ

- Локальная ОС Linux Mint; путь проекта: /home/gor/Рабочий стол/rails_projects/lite/cafe_app. Локальная ветка feature/cafe-integration-local-20261101, есть существенные modified/untracked files и public/uploads. Без прямого согласования НЕ checkout/reset/clean/rebase/merge/overwrite; не удалять и не сбрасывать файл и volume.
- Production-original localhost:3001 HTTP 200, PG cafe-app-db. Отдельная patched QA localhost:3002 HTTP 200, PG cafe-upload-qa-pg-20261103 на persistent volume. Оба защищены.
- Две disposable tmpfs PostgreSQL #3 sandbox cafe-upload-security-sandbox-pg-20261104 и #4 E2E cafe-upload-security-e2e-pg-20261105: после reboot 06.11 восстановлены ОДНОКРАТНО из проверенного приватного QA dump; отдельный --verify-clones PASS, 20 товаров + 2 исторических QA test users, system IDs четырёх PG различны, 10 приватных медиафайлов SHA сохранён. Ни один файл дампа/пользователей не публиковать.
- Четыре старых isolated Rails-кандидата sandbox-original, sandbox-precache, headers-reportonly и fourth-readonly после reboot запущены ОДНОКРАТНО; отдельный независимый --verify PASS, 3001/3002 и media не затронуты. Fourth-readonly предназначен для GET/security, НЕ для writable POST E2E.
- Пятый контейнер cafe-upload-security-synthetic-pg-20261105: PostgreSQL16, БД cafe_synthetic, сеть cafe-upload-security-synthetic-net-20261105 internal-only, no published ports, SCRAM TCP, PGDATA tmpfs. ОДНОКРАТНО восстановлен пустым после reboot через PR #62 и отдельно --verify-empty PASS ДО ролей: пять независимых system IDs, 0 app tables/0 дополнительных LOGIN ролей. Старые роли и старый cluster ID от 05.11 исчезли из tmpfs.
- Новые роли уже применены ОДНОКРАТНО 06.11 в пятой БД через PR #63: cafe_synth_owner NOLOGIN, владелец public schema, без привилегий суперпользователя; cafe_synth_app LOGIN/SCRAM, только scoped CONNECT/USAGE и default CRUD privileges, без CREATE/other DB connect/membership. Рандомный пароль хранится только в новом приватном owner файле, никогда не печатать/переносить.
- **Пятая DB до сих пор без прикладной Rails-схемы и seeds**. PGDATA в tmpfs, при новом cold reboot тестовая БД исчезнет — не использовать её для публичного persistent deploy.
- One-shot маркеры для двух PG recovery, четырёх Rails boot, пятой SCRAM bootstrap и пятой roles recovery существуют. НЕ обходить/снимать/перезаписывать их. При ошибке — read-only диагностика, никаких повторных SQL/docker start по инерции.
- После роли old --verify-empty и старый P1.2 schema helper 05.11 нельзя запускать без совместимости со свежим PR #63.

## 3. ДВА ВИЗУАЛЬНЫХ ДЕФЕКТА — НОВЫЙ ПРИОРИТЕТ

Пользователь прислал два скриншота своего localhost:3001 от 06.11.2026. Скриншот A: на Home в правом верхнем углу Sign In / Sign up размещены на геометрически сломанной тёмной площадке: лишний пустой блок слева, шов и несогласованные углы. Скриншот B: при скролле /menu фон кафе **неподвижный**, прокручивается только меню; на остальных страницах фон движется вместе с контентом. Владелец требует такой же неподвижный фон на ВСЕХ страницах.

**Проверенные root causes по коду GitHub:**
1. app/views/layouts/application.html.erb — four-column markup: nav col-2, content col-8, пустой avatar placeholder col-1 для гостя, отдельный auth col-1.p-2 с h6 ссылками Sign In/Sign up. app/assets/stylesheets/zz_cafe_layout_reflow.scss формирует grid areas nav/main/avatar/account (192px, fluid, 52px, 112px), а app/assets/stylesheets/zzzz_cafe_account_corner.scss меняет desktop widths на 192px, fluid, 64px, 164px и задаёт НЕСИММЕТРИЧНУЮ рамку, фон и скругления у пустого avatar сегмента и auth сегмента. На guest выглядит как поломанный стык. Есть каскад в zzz_cafe_mobile_quality.scss и zzz_cafe_auth_account.scss. Не переписывать Devise/authorization ради CSS.
2. app/assets/stylesheets/pages.scss задаёт background-attachment: fixed **только для .menu-page**. Для .home-page/.catering-page/.info-page/.review-page фон задан отдельным image/size без fixed; zz_cafe_layout_reflow.scss делает size:cover/position, но не исправляет scroll. application.scss загружает Sprockets require_tree; проверить порядок assets и Webpacker pack.
3. Сохранить оригинальные фоновые файлы, включая историческое название extereor.jpg; не делать image swap. Визуальные скриншоты пользователя НЕ публиковать в открытый GitHub.

**Новый frontend Draft PR — критерии:**
- Один целостный guest auth widget вместо сломанного split account/avatar background. Для signed-in сохранить avatar/username/signout, для admin не потерять nav и ACL. Хорошее выравнивание, фон, border-radius, контраст, focus-visible, touch targets около 44px, отсутствие horizontal overflow.
- Фон закреплён на Home/Menu/Cart/Info/Catering/Product detail/Devise/Account/Admin и остальных страницах с общим shell; скроллится контент. В Cart может быть fixed gradient; остальные сохраняют собственный image. Desktop проверить background-attachment fixed, для mobile Safari fallback (fixed background layer/pseudo) и stacking, чтобы не блокировать клики/modal/scroll.
- Viewports 320,360,390,768,1024,1440,1648; guest и authenticated; top/middle/bottom scroll. SCSS asset compile в legacy runtime; screenshot/visual smoke и accessibility. No regressions menu/cart/auth, no automatic production/QA restart.
- Работать в новой независимой GitHub ветке, не считать код GitHub точной копией локального dirty app; для реального stage/localhost сравнить source/css владельца read-only до интеграции. Баги подтверждены, но **ещё не исправлены**.

## 4. ПРОДУКТ, СТЕК И СОСТОЯНИЕ GITHUB

Это учебно-портфолийная, не коммерчески действующая кофейня: demo каталог, demo корзина, без реальных платежей и fulfilment. Legacy Ruby 2.5.8 / Rails 6.0.x / ERB / Sprockets Sass / Bootstrap 4 / Webpacker 4 + Node 14 / Devise / CanCanCan / PostgreSQL / CarrierWave-MiniMagick. Глобальные Rails 8/Ruby 3.4 на Linux пользователя не являются стеком этого приложения. Обновление runtime — отдельный рискованный этап после baseline.

Исторические Draft PR #6–#31: Home, menu 20 demo products/categories/search/dietary, six configurable drinks S/M/L/milk/syrup/shot с server-owned prices, Cart qty/update/remove/line consolidation, Product Details, About/FAQ/Catering/footer, Devise account, admin products/categories, branded errors and responsive CSS. PR #32–#50: isolated avatar/upload hardening, Media forensic SHA, headers/CSP report-only, ImageMagick guard; некоторые изменения существуют только в sandbox/QA и **не** в публичном приложении.

**Подтверждённые точные GitHub head/CI на 06.11:**
- [PR #54](https://github.com/TheGor-365/cafe_app/pull/54), head f799021489cdd3787c8278f402a44006b196a091, [CI #42038771784 SUCCESS](https://github.com/TheGor-365/cafe_app/actions/runs/42038771784) — disposable GitHub Postgres schema+fixtures. Старую ошибку missing psql от 05.11 исправили; не начинать с неё.
- [PR #57](https://github.com/TheGor-365/cafe_app/pull/57), head bec85064f37b033783b3635efa61aa482fb3f915, [CI #42106259280 SUCCESS](https://github.com/TheGor-365/cafe_app/actions/runs/42106259280) — статические/negative проверки fifth-only schema writer, НЕ доказательство owner DDL.
- [PR #60](https://github.com/TheGor-365/cafe_app/pull/60) — два тестовых PG после reboot owner restore/verify PASS.
- [PR #61](https://github.com/TheGor-365/cafe_app/pull/61) — 4 isolated Rails boot/verify owner PASS, [CI #42247108023 SUCCESS](https://github.com/TheGor-365/cafe_app/actions/runs/42247108023).
- [PR #62](https://github.com/TheGor-365/cafe_app/pull/62) — fifth empty SCRAM reboot/verify owner PASS, [CI #42254845756 SUCCESS](https://github.com/TheGor-365/cafe_app/actions/runs/42254845756).
- [PR #63](https://github.com/TheGor-365/cafe_app/pull/63) — fifth scoped roles recovery, HEAD a69c18be95cb8d03515fd2d21c77271fb773490a, helper Git blob a02f23a9cd2c982309a1649ea0b314618f9da94a, [CI #42272625914 SUCCESS](https://github.com/TheGor-365/cafe_app/actions/runs/42272625914). Права/пароль локально проверены in-script; отдельный --verify ещё ожидается. Предыдущее «No jobs were run» было вызвано YAML ошибкой имени шага и уже исправлено.
- Вся цепочка остаётся **Draft/open**, НЕ merged, не считать master production release. База, портфолио, CI и UI могут отличаться между PR и локальным работающим контейнером.

## 5. ПЛАН ДО ФИНАЛА — приоритеты и acceptance

**A. Безопасное завершение reboot checkpoint (сейчас):** owner independent fifth-role --verify READ ONLY; после PASS обновить PR #63. Одновременно автономный UI GitHub PR. Не повторять one-shot operations.

**B. Исправление UX (сразу вслед за A):** исправить auth corner и единый fixed backdrop (см. §3). Подтвердить rendered UI на guest/logged-in и разных страницах/viewport, никаких ошибок CSS/HTML, header/nav/cart/Devise работают. Зафиксировать screenshot evidence, no protected mutations.

**C. Fifth-only Rails schema:** старый PR #57 авторский helper содержит зависимость от 05.11 scoped-role script/старого cluster идентификатора и не пригоден напрямую после tmpfs reboot. Автономно переписать совместимый READ-ONLY preflight, привязанный к новым ролям PR #63; exact PG name/cluster ID/network/IP/roles/source blobs, пустую fifth schema/marker, нет доступности protected PG. Отдельный CI PASS, owner один --check. ТОЛЬКО затем отдельно разрешённая one-shot fifth-only schema DDL с новым marker (не db:prepare/reset/drop на live). Independent --verify-schema: 10 таблиц (8 app + Rails metadata/schema_migrations), 8 FK, migration versions, owner-owned objects/default privileges, app DDL denied, 0 rows/users, 4 other PG + media + 3001/3002 unchanged. Не перезапускать старую процедуру при unknown failure.

**D. Fifth demo fixtures:** synthetic-only seeds в пятую schema. Ожидаемые ориентиры из PR #54: 8 categories / 20 products / 18 variants / 30 options / 0 users до auth testing. Проверить фактические counts/absence duplicates, app CRUD grants и отрицательные DDL/membership checks. Не импортировать original QA dump/users/passwords/images.

**E. Fifth isolated writable E2E:** дополнительный приватный Rails контейнер (не fourth-readonly), только fifth private PG, собственные mock users/uploads, без внешних host ports; e2e scenario matrix guest/user/admin ACL, CSRF POST, signup/logout, cart+configuration+price integrity, quantity and stale sessions, file magic/size/extension/CSP/ImageMagick, headers, negative unauthorized mutations, responsive UX. Настоящий POST с valid CSRF, а не только старый 405 read-only. Gate: PASS in isolated test with original services untouched.

**F. Integration/release candidate:** ревизия ВСЕХ stacked PR #1–#63, конфликтов/дублирования, чистая отдельная GitHub release branch, Ruby2.5/Node14 asset compiling, suites and migration integrity, no secret/media/personal-data leaks; сверить локальную dirty ветку read-only до какого-либо интеграционного изменения. Ни автоматического merge master, ни production switch.

**G. Production security/persistence и модернизация:** secure uploads, auth/ACL, dependency advisories, logging, CSP headers, errors, secrets, test suite, backups with actual restore; отдельная persistent PostgreSQL и media для public demo (НЕ fifth tmpfs), healthcheck and rollback. Legacy Ruby/Rails/Node upgrade проектировать отдельной контролируемой веткой после baseline, не смешивать со стабилизацией.

**H. Separate Railway Cafe demo:** лишь после бюджета/конкретного согласования платных/публичных изменений. Использовать Railway connector для фактов, не трогать чужой portfolio Rails проект. Secrets, DB persistence, media storage, SSL, startup, migrations and rollback. Публичный URL после реального HTTP/browser/roles smoke, честная demo-only маркировка и отсутствие реальных транзакций.

**I. Case/portfolio/marketing:** RU/EN README, demo screenshots/video, architecture, features/limits, tests/CI, release evidence; существующая Google Drive Cafe folder, GitHub portfolio, существующие соц/фриланс каналы после проверки. Не пересоздавать профили/Drive и не публиковать customer/QA private data; цель — квалифицированные заявки и платные заказы, а не число PR.

**J. Final acceptance:** running independent public site, testable guest/user/admin, mobile/desktop and fixed scroll/background PASS, backups and restore, secure auth/upload/cart/server prices, QA/production isolated, regression tests, provenance and costs. Создать CAFE_APP_RELEASE_HANDOFF_YYYY-MM-DD.md + CAREER_STATUS update с SHA/PR/CI/URLs/date/source, tested backups, open risks, 1–3 next steps. No fake «ready» declaration before acceptance.

## 6. ПРАВИЛА РАБОТЫ НОВОГО ЧАТА

- GitHub connector: искать свежие PR/files/commits/CI, редактировать новые feature branches и Draft PR, фиксировать чекпоинты по exact head. Google Drive connector: только в существующую Cafe структуру с readback, не выдумывать папки или одинаковые права Gemini/ChatGPT. Railway: только проверенные проекты/ресурсы. Gmail: тематические GitHub оповещения, как вторичное подтверждение, не заменяют job logs.
- Пользователь разрешает максимально автоматизировать подключённые технические операции. Не пытаться делать локальные действия, к которым нет доступа; платные/публичные/опасные/необратимые действия согласовывать по месту. Никаких паролей, токенов, QA dump, реальных идентификаторов/профильных данных в открытых ветках. Старые scripts/markers/volumes нельзя удалять, сбрасывать или обходить для успешного CI.
- На owner Linux — одна конкретная страница / 1–3 действия / вывод или скриншот. Каждому write предшествует отдельный read-only preflight, и после него идёт независимый verify. Нет информации — не выдумывать PASS, не повторять «слепо» одноразовые операции.
- По итогам этапа: дата и источник | verified facts | created PR/commit/CI | status | blocked/unverified | next 1–3 действия. Чаты не синхронизируются автоматически; обновить GitHub/Drive явно с readback.

### Корректный первый ответ нового чата

«Изучил мастер передачи 06.11.2026. Последнее действие — пятая SCRAM PostgreSQL и обе scoped роли успешно восстановлены локально через one-shot --provision; Rails schema и seeds ещё не загружались. Два UX бага на Home/прочих страницах открыты и имеют выявленные ERB/SCSS причины. Автономно начинаю новый Draft PR исправления account corner и fixed background, проверяю GitHub. В текущем терминале cafe_app требуется только независимый read-only: python3 -B "$HOME/.local/share/cafe_app/cafe_p12_fifth_scoped_roles_v1_20261106.py" --verify. После PASS — совместимый P1.2 schema gate для новой пятой БД».
