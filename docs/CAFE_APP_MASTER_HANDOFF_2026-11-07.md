# CAFE APP — MASTER HANDOFF / ПРОДОЛЖЕНИЕ 2026-11-07

**Проект CAREER · Gor's Coffee · `TheGor-365/cafe_app`**  
**Срез доказательств:** 7 ноября 2026, данные терминала пользователя из текущего чата + GitHub PR/CI + Google Drive (сверены 07.11).  
**Назначение:** новый текстовый чат с подключёнными GitHub, Google Drive и Gmail должен продолжить разработку С ТЕКУЩЕГО БЛОКЕРА, не переигрывая завершённые этапы и не запрашивая сведения, которые уже здесь есть.

> **Команда новому чату:** «Исполняй этот handoff. Начинай с раздела 1 (текущий STOP), сам открой репозиторий, PR и CI, проверь последние SHA, устрани доступные remote-блокеры, затем дай одну безопасную команду для owner Linux. Не начинай проект заново. Не выполняй удаление, миграции, merge или платный deploy по инерции».

---

## 0. Рабочая роль, автономность и источник истины

Ты — senior Ruby on Rails engineer, PostgreSQL/Docker security lead, CI/CD + QA engineer, frontend/browser lead, release manager, technical portfolio lead. KPI — безопасно **работающее и реально проверенное портфолио-демо кафе** с воспроизводимыми тестами, guest/user/admin, отзывчивой мобилкой, настоящими ассетами и отдельно согласованным public demo deploy. Число PR и зелёных CI — вспомогательные метрики.

**Автономно и немедленно** используй подключённые GitHub/Drive/Gmail для чтения актуальных фактов, code review, коммитов в согласованные feature-ветки, Draft PR, исправления CI, ревизии документации, создания и readback checkpoint, расследования ошибок. Не спрашивай разрешения на уже порученную безопасную remote-разработку. Gmail — только адресное чтение релевантных писем CI/сервиса при необходимости; не отправляй письма без отдельного поручения. Если окажутся доступными Railway/другие plugins — используй для **read-only** исследования до платного/публичного действия.

**У тебя нет локального shell пользователя, его Docker, браузера и файлов.** Пользователь сам исполняет согласованные команды в Linux и присылает точный stdout/скриншот. Давай 1–3 действия максимум за итерацию; сначала проверяй GitHub/CI самостоятельно. Никогда не выдавай CI за подтверждение местного запуска или реального браузера. По каждой операции статус: `не начато / CI static PASS / owner-local PASS / блокер / ждём пользователя / production accepted`.

Иерархия: **самый свежий вывод владельца** → real GitHub commit/PR/CI или другие внешние измерения → свежий Drive checkpoint → данный master → исторические мастера 05–06.11. Обязательно перепроверь HEAD, поскольку после создания этого файла коммиты могли измениться. Не доверяй устаревшей первой команде старых мастеров.

## 1. ТОЧНАЯ ТОЧКА ВОЗОБНОВЛЕНИЯ — ПОСЛЕДНИЙ STOP

**ПОСЛЕДНИЙ результат владельца:**

```
D="$HOME/.local/share/cafe_app"
F="$D/cafe_p14_fifth_real_webpacks_20261107.py"
Z="$HOME/Загрузки/cafe-p14-fifth-real-packs-test.zip"
# Сам скрипт SHA-verified (Git blob c04f765145e552a8456c393751f93faa2b455fb0), chmod 600.
python3 -B "$F" --verify-archive --archive "$Z"
P1.4 REAL WEBPACK STOP: artifact owner/mode/size unsafe
Do not touch original four PG/media, restart fifth tmpfs, or replay P1.2/P1.3 one-shot operations.
```

**Что это доказывает:** отказ произошёл **до чтения ZIP, распаковки, обращения к Docker или PostgreSQL**. Код v1 объединял четыре условия в одном `require`: `st.st_uid == os.getuid()`, `0 < st.st_size <= 25 MiB`, `stat.S_ISREG(st.st_mode)`, `not (st.st_mode & 0o022)` (отсутствие групповой/чужой записи). Точный виновник без `stat` не известен. **Не заявляй, что ZIP повреждён.** Ранее пользователь нашёл тот же архив в `/home/gor/Загрузки/cafe-p14-fifth-real-packs-test.zip`; реальная локальная `sha256sum -c` вернула **«ЦЕЛ» = OK** для SHA256 `95cc0c7985b4aba252470aff3493ee64664f371fa7eb9a8127cccd5e551405e3`.

**Автоматически уже подготовлен безопасный v2 gate** в GitHub Draft PR #68:

- файл GitHub: `scripts/cafe_p14_fifth_real_webpacks_gate_v2_20261107.py`;
- blob **`4011c29bff36544401f99c999173fbb981e203f8`**;
- добавлен commit `861e1b9cb2caac52307081b5077625b4996df7c2`, обвязка CI/negative tests затем обновлена; последний до данного master HEAD был `974374e0b6831da4ddf972a322c9b43022b686c6` (перепроверь);
- v2 **не ослабляет** проверок. Он раздельно сообщает «не обычный файл», «owner UID mismatch», «размер вне диапазона», «group/other write permission present», затем проверяет тот же неизменный SHA256/ZIP и предоставляет оба режима `--verify-archive` и `--check-real-get`;
- последний увиденный push CI #42389158896 **SUCCESS**; PR-run #42389163957 был в работе при последнем просмотре. Прочитай актуальный итог и diff перед действием владельца.

**Первый операционный шаг нового чата:** (A) сам проверь PR #68, HEAD, v2 blob, CI; (B) дай владельцу ТОЛЬКО короткую read-only диагностику локального архива:

```bash
Z="$HOME/Загрузки/cafe-p14-fifth-real-packs-test.zip"
stat -c 'file=%n uid=%u mode=%a size=%s bytes' -- "$Z"
id -u
sha256sum -- "$Z"
```

Никаких секретов эта команда не показывает. Если подтвердится только group/other writable, после ещё раз подтверждённой SHA, корректного владельца и обычного файла предложи безопасный узкий `chmod go-w -- "$Z"` (НЕ `chmod 777`, НЕ sudo, НЕ правка конфигурации, НЕ ослабление валидации) и отдельно запуск v2 после проверки download-source blob 4011... в **новом** приватном пути. Если mismatched UID, размер или тип — разбирать отдельно, без догадок. Не советуй повторять v1 просто так.

**Ожидаемый целевой PASS для read-only архива:**

```
P1.4 GITHUB ARTIFACT SHA256 VERIFIED PASS
P1.4 ZIP ENTRIES/PATHS/UNCOMPRESSED SIZE/NO SYMLINK PASS
P1.4 REAL WEBPACKER TEST MANIFEST/COMPILED JS PASS
P1.4 ARCHIVE VERIFY PASS — NO EXTRACTION OR DB ACCESS
```

Только ПОСЛЕ него — отдельно v2 `--check-real-get --archive "$Z"`; это READONLY пятой БД и временный Rails source, НЕ браузерное JS E2E.

## 2. Защита существующей Linux/Docker среды — неприкосновенные границы

- Linux Mint, локальный путь **`/home/gor/Рабочий стол/rails_projects/lite/cafe_app`**; owner branch **`feature/cafe-integration-local-20261101`**, dirty `✗`. Не `git checkout`, `reset --hard`, `clean`, `rebase`, overwrite uncommitted код/локальные media/migrations/Gemfiles, не force push.
- Локальное кафе `127.0.0.1:3001` и отдельный QA `127.0.0.1:3002` — рабочие сервисы, не перезапускать и не трогать конфигурации. Не публиковать новые порты без отдельного обсуждения.
- Четыре защищённые PostgreSQL-кластера: исходный `cafe-app-db`, QA `cafe-upload-qa-pg-20261103`, sandbox `cafe-upload-security-sandbox-pg-20261104`, fourth E2E `cafe-upload-security-e2e-pg-20261105`. Второй содержит persistent данные; отдельные tmpfs среды после reboot ранее проходили one-shot восстановление из приватного dump. Никаких прямых schema/seed/fixtures/write команд в эти четыре.
- **Пятая** отдельная PostgreSQL16: контейнер **`cafe-upload-security-synthetic-pg-20261105`**, network **`cafe-upload-security-synthetic-net-20261105`** с internal-only routing, DB **`cafe_synthetic`**, без host-published port, PGDATA **`tmpfs`**, SCRAM, cluster-ID-проверка. **Не останавливать, не перезапускать и не делать Docker cleanup**, иначе каталог и схема будут потеряны; перед новым сеансом только read-only `inspect` и независимая P1.3 проверка при необходимости.
- DB roles: `cafe_synth_owner` NOLOGIN/table owner, `cafe_synth_app` LOGIN/SCRAM restricted CRUD, app не может DDL. Приватные секреты лежат только в `$HOME/.local/share/cafe_app/`, файл/секрет/пароль/IP/DSN нельзя печатать, копировать в GitHub/Drive/чат.
- Пятая БД уже **не пустая**: schema + 8/20/18/30 catalog. Старые `--verify-empty`, `--verify-schema` expecting empty data, `--check` pre-one-shot schema и роль recovery `--provision` нельзя применять повторно. Вместо них только актуальные read-only postflight.
- Маркеры однократных операций нельзя удалять/подменять/обходить, в том числе:
  - `$HOME/.local/share/cafe_app/cafe_p12_fifth_schema_attempt_20261106.json`;
  - `$HOME/.local/share/cafe_app/cafe_p13_fifth_catalog_attempt_20261107.json`;
  - и существующие более ранние P1/P1.1 роли/PG recovery; имена других маркеров получать из SHA-pinned helpers, не угадывать.
- Не применять `db:drop`, `db:reset`, `db:prepare`, `db:schema:load`, `db:seed`, `rails test` с обычным `test_helper.rb` против пятой: `fixtures :all` и scratch DB conventions могут перезагрузить данные. Не импортировать реальных пользователей, аватары, uploads и QA dump в пятую.
- Никаких KYC, customer/private media, банкинга/SMTP/GitHub secrets, Rails master key, открытых DSN или приватных скриншотов в публичной GitHub ветке/общем AI Drive. Не трогать другие Rails-проекты пользователя.

## 3. Результаты, ДОКАЗАННЫЕ пользователем, не повторять

| Этап | Owner terminal evidence, дата 2026-11-07 | Статус |
|---|---|---|
| P1/P1.1 | 5 независимых PG, SCRAM, scoped roles, Linux QA legacy bundle+mount, fake-secret no-network Rails boot, 4 DB/media/web isolated | PASS (исторические owner checks/повторные preflights) |
| P1.2 | `cafe_fifth_schema_cluster_scoped_20261107.py --create-schema --confirm-target cafe_synthetic` выполнился ОДИН РАЗ; `--verify-schema` позже подтвердил 10 total tables, 8 FK, 8 owner sequences, migration versions, app ACL and empty data | **PASS**; DDL НЕ повторять |
| P1.3 | `cafe_p13_fifth_catalog_20261107.py --import --confirm-target cafe_synthetic` выполнен ОДИН РАЗ, затем независимый `--verify`: 8 categories, 20 products, 18 variants, 30 modifier options, 6 configurable drinks, уникальные ключи, 0 users/orders/carts/product images | **PASS**; импорт НЕ повторять |
| P1.4 initial GET | `cafe_p14_fifth_http_readonly_20261107.py --probe` — STOP внутри disposable Rails runner; дополнительный `--diagnose`: `STAGE=get_home`, `KIND=VIEW_ERROR`; `--classify-view`: `ROOT_CAUSE=WEBPACKER_MANIFEST_ENTRY`, `PACK_MANIFEST=MISSING`, `PUBLIC_PACKS=MISSING`, `NODE_MODULES=MISSING` | Инцидент локализован, не скрывать |
| P1.4 isolated HTML shim | `cafe_p14_fifth_html_stub_assets_20261107.py --check-html`: `ALL_GETS_PASS`, `KIND=NONE`, **server-rendered HTML routes/guest ACL PASS**; P1.3 pre/post counts PASS; temporary test-only Webpacker stub, без JS исполнения | **PASS** для backend GET, НЕ frontend |
| P1.4 genuine Webpack | CI #42384029688 под `node:14.21.3`: `yarn install --frozen-lockfile`, 3 JS tests, Webpacker 4.3 test pack built and manifest pointing to compiled `application.js`, artifacts uploaded | **CI PASS**, не owner JS browser |
| ZIP download | GitHub artifact `cafe-p14-fifth-real-packs-test.zip`; локальный SHA256 был проверен и показал «ЦЕЛ» | SHA256 PASS |
| Новый ZIP verifier v1 | `--verify-archive` STOP `artifact owner/mode/size unsafe` до чтения содержимого ZIP/обращения к Docker | **BLOCKED**; v2 gate подготовлен |

### P1.4 backend GET/ACL scope (это уже проверено в fifth DB)
- `GET /`, `/menu`, `/menu?search=Espresso`, `/cart`, `/info`, `/catering`, `/products/:id` (Cappuccino), `/users/sign_in`, `/users/sign_up`, `/users/password/new`.
- Guest GET `/account`, `/products`, `/categories` должен редиректить на sign-in; тест подтвердил этот уровень ACL.
- Все операции только GET через `ActionDispatch::Integration::Session`; no host ports; `cafe_synth_app`, PGOPTIONS `-c default_transaction_read_only=on -c search_path=public`; pre/post Catalog+four PG protected.
- Это НЕ доказательство CSRF POST, регистрации с сохранением, логина сессий, админских CRUD, загрузок, browser JS, CSS, mobile QA. `RAILS_ENV=test` в этой сборке отключает стандартную forgery protection — нужен отдельный явно включённый CSRF test для real writable E2E.

## 4. Ключевые исходники, Git SHA, CI и ссылки

**Репозиторий:** https://github.com/TheGor-365/cafe_app ; default branch **`master`**, исторический HEAD **`06f66f3d318e1a3fe3e5683baf541f5fec8b4c01`** (проверен 07.11; не слит с Draft chain). Никаких автоматических merges в master.

**Замороженный Rails source snapshot пятой:** commit **`090b9d37419fcd9f393d8b686ac0f4563ef7b613`**. Canonical `db/seeds.rb` Git blob `dae2eed43c78ff79a14e3bf3e83d59a649803cd4`, `config/webpacker.yml` Git blob `83615b0f9ac0ca5508548621150789c7dad71071` (`test compile: true`, `public_output_path: packs-test`, `extract_css: false`). Разрыв: временный readonly staging не содержит node_modules/packs-test; оригинальный layout использует `javascript_pack_tag 'application'`.

**Основная цепочка Draft PR (все пока open/unmerged по GitHub 07.11):**

| PR | Назначение | Проверенный head / evidence |
|---|---|---|
| [#63](https://github.com/TheGor-365/cafe_app/pull/63) | пятая DB scoped roles и восстановление | owner one-shot PASS 06.11; отдельные исходники читать в PR |
| [#64](https://github.com/TheGor-365/cafe_app/pull/64) | handoff 06.11 | отдельная историческая документация, не source of truth для текущей схемы |
| [#65](https://github.com/TheGor-365/cafe_app/pull/65) | единый guest account box + fixed backdrop + локальный sticky header SCSS | head `d1037615c2928641d5676a0a18160bdd546f2ec5`; owner one-file CSS apply + independent SHA verify PASS; **полный браузерный scroll/auth/mobile screenshot smoke НЕ выполнен** |
| [#66](https://github.com/TheGor-365/cafe_app/pull/66) | fifth scoped Rails schema writer | head `d0f547dd62080b6ae494b2d7f35dd9bde9ede743`; owner schema DDL+verify PASS |
| [#67](https://github.com/TheGor-365/cafe_app/pull/67) | fifth demo catalog fixtures | head `95eb2079e92436b85410290314cbb6a2924f94eb`; owner importer+postflight PASS |
| [#68](https://github.com/TheGor-365/cafe_app/pull/68) | fifth-only read-only HTTP/ACL, asset diagnostics, real Webpack, ZIP validator | перед созданием handoff HEAD `974374e0b6831da4ddf972a322c9b43022b686c6`; **перечитать текущий HEAD**; draft, base #67 branch; CI run #42389158896 push SUCCESS, PR run #42389163957 был ещё in progress на последнем readback |

GitHub PR #68 может снова обновиться при публикации данного документа. История остальных Draft #6–#62, source/QA/CI содержится в старом `docs/CAFE_APP_MASTER_HANDOFF_2026-11-05.md` и `docs/CAFE_APP_MASTER_HANDOFF_2026-11-06.md` (на отдельной PR64 ветке), в `docs/PRODUCT_ROADMAP_COFFEE_2026-11-01.md`. В старых файлах **первый шаг и «schema empty» УСТАРЕЛИ**. Нельзя слить PR #65–#68 независимо без анализа base/stack, duplicate file conflicts и owner dirty tree.

**SHA-pinned приватные helper-исходники, уже установленные владельцем в `$HOME/.local/share/cafe_app/`:**

| Имя | Git blob SHA | Что не повторять / статус |
|---|---|---|
| `cafe_fifth_schema_cluster_scoped_20261107.py` | `a0d2ac4546f19ab8d6c92b5b0f465269fbd4e08f` | `--create-schema` **ONE-SHOT DONE** |
| `cafe_fifth_schema_cluster_guard_20261107.rb` | `a95f8d95a9a4af9853f418756ffa517f99f6efe4` | fifth cluster/role guard, source only |
| `cafe_p13_fifth_catalog_20261107.py` | `8dbf42b86a4c617fb69c986e9103fce631d3a49e` | `--import` **ONE-SHOT DONE**; `--verify` safe if baseline still empty users/orders |
| `cafe_p14_fifth_http_readonly_20261107.py` | `426414d64584231df380c9588c9e0b80e32589c7` | старый GET `--probe` упал без Webpacker manifest; не повторять без новой среды |
| `cafe_p14_fifth_http_readonly_20261107.rb` | `299de6d74f55fe04c222875ca424b6c2c7443b5f` | GET-only Rack script |
| `cafe_p14_fifth_http_fault_diagnostic_20261107.py` | `1aee748857e42a13df316858f763aaeadaf02328` | первая диагностика VIEW_ERROR |
| `cafe_p14_fifth_http_fault_diagnostic_20261107.rb` | `e7738e20f8d8656a685d0084f31f19a5e04bed64` | fixed stage/kind |
| `cafe_p14_fifth_view_error_cause_20261107.py` | `d0c3544f8eacc7c4940bc5c2d1fdcd0a7621b349` | classified WEBPACKER_MANIFEST_ENTRY |
| `cafe_p14_fifth_view_error_cause_20261107.rb` | `7609ff9cef7e5fe2b116b2cde769f91498d15262` | nested ActionView cause classifier |
| `cafe_p14_fifth_html_stub_assets_20261107.py` | `215312d18949745695b4fcc70d2485271386ea2f` | owner HTML SSR+ACL PASS с заглушкой |
| `cafe_p14_fifth_real_webpacks_20261107.py` | `c04f765145e552a8456c393751f93faa2b455fb0` | v1 ZIP mode STOP, сохранять для аудита, НЕ заменять на месте |
| `cafe_p14_fifth_real_webpacks_gate_v2_20261107.py` | `4011c29bff36544401f99c999173fbb981e203f8` | **только GitHub, ещё НЕ скачан владельцем**; отдельный приватный filename; `--verify-archive` после проверки владельца/Unix mode |

**GitHub genuine asset artifact:** run https://github.com/TheGor-365/cafe_app/actions/runs/42384029688, ID **13578972029**, name `cafe-p14-fifth-real-packs-test`, 2,002,488 compressed bytes, SHA256 **`95cc0c7985b4aba252470aff3493ee64664f371fa7eb9a8127cccd5e551405e3`**, archive expiration **2026-11-14 14:58 UTC**. ZIP хранится в `~/Загрузки/` — не перескачивать без причины. Он содержит настоящую сборку test Webpacker, без node_modules; content безопасности ещё нужно проверить v2. CI #42384029688 SUCCESS 6 jobs; `fifth-real-webpack-test-assets` реальные `yarn install`, JS tests и build; это не браузер E2E.

### Почему нужен pinned source даже при успешном CI
- GitHub Actions runner ephemeral и не имеет реальных owner Linux volumes/PG credentials.
- fifth-only Docker читает исходник в отдельном временном каталоге через `git archive` reviewed Rails SHA; gems mounted read-only `/bundle`; writer/reader scripts используют отдельные приватные SHA-pinned helper files и scoped internal PostgreSQL.
- ZIP не может напрямую монтировать произвольные файлы. Safe flow: exact SHA → ZIP structural inspect → temp extraction + test-only `compile: false` overlay → fifth-only restricted read-only GET → независимая проверка четырех PG/схемы/каталога.
- НЕ считать реальный Webpack build доказательством, что CSS, JS и DOM взаимодействия работают в реальном Chrome; для этого нужен browser E2E и screenshots.

## 5. Что реализовано в продукте, но требует разных уровней приёмки

**Demo (не настоящая кофейня):** исторический Ruby 2.5.8, Rails 6.0.x, PostgreSQL, ERB, Sprockets/SassC, Webpacker 4.3/Node14, Bootstrap4, Devise, CanCanCan, CarrierWave/MiniMagick, Turbolinks. Глобальные Ruby 3.4/Rails8 пользователя — НЕ совместимое окружение этого проекта по умолчанию.

**В GitHub stacked Draft PR уже разработано (НЕ повторять создание функций):** demo storefront, 8 категорий/20 продуктов и поиск/filter, six configurable drinks S/M/L + milk/syrup/shot with **server-owned** price and snapshot, live JS price preview, quantity and cart line consolidation/deduplication, responsive product detail, account/Devise, admin products/categories, HTML escaping, branded errors/favicon, footer/about/FAQ/catering, upload validation, sandbox CarrierWave/ImageMagick headers/CSP report-only, isolated PG QA and CI. Все эти функции есть в разных ветках/кандидатах; не утверждать, что они уже собраны в одной проверенной production версии.

**UI PR65:** исправление неровного guest Sign In/Sign up блока, unified fixed backdrop across pages + SCSS sticky-header layer было написано/CI; пользователь локально применил **только один новый header SCSS** с SHA verify, но UX acceptance на реальном браузере для desktop/mobile, top/middle/bottom scroll, signed-in avatar/username, z-index, 320/390/768/1440 не подтверждено. Не делать повторное «исправление» без сравнительного source audit и новых screenshots.

**Старый подтверждённый browser test:** Cart line consolidation из PR18, две разные конфигурации не объединяются; одинаковые объединяются, Cart(6)=$37.35. Это отдельный historical owner/browser PASS, не равен нынешнему P1.4 writable E2E в пятой БД. Сохранить как evidence, но не подменять отсутствующие проверки.

## 6. Открытые этапы: roadmap до готового портфолио-продукта

### A — сейчас: P1.4 real-assets GET
1. Разобраться с архивным `owner/mode/size` через `stat`, без логов/секретов. Применить только минимальное chmod, если подтверждено отсутствие каких-либо других причин, SHA/owner/regular file сохраняются; не менять ограничения валидатора.
2. Скачать v2 из immutable GitHub commit, сравнить Git blob **4011...**, положить в НОВЫЙ отдельный owner-private path с `chmod 600`, выполнить `--verify-archive` (ни PostgreSQL, ни extraction), получить четыре PASS.
3. После PASS — отдельно разрешённый `--check-real-get`, readonly fifth-only + genuine JS asset staging. Ожидается `P1.4 REAL WEBPACK TEST ASSETS / SERVER GET ROUTES/ACL PASS`. Не путать с browser JS acceptance. При BLOCKED — исследовать fixed stage/kind; никаких перезапусков.

### B — frontend/browser визуальная приёмка
- Настоящие CSS/JS в отдельном browser preview (владелец Chrome Linux / поддерживаемый browser workflow), DOM/HTTP 200/asset network status, console errors, CSP and click paths. Реальные размеры 320/360/390/768/1024/1440/1648 и scroll top-middle-bottom. Fixed background на Home/Menu/Cart/Info/Catering/Devise/admin, no click interception, layout account card and sticky header, keyboard and 44px touch targets, mobile nav, modal/drawer, no horizontal overflow.
- Снимать только реальные скриншоты, не фейковые изображения вместо UI. Не изменять localhost:3001/3002 без согласованного плана интеграции, если для проверки требуется новая изолированная browser preview — согласовать exact host port и безопасность.

### C — P2 isolated writable E2E (Пока НЕ начато)
- Спроектировать в ОТДЕЛЬНОМ Draft PR независимый fifth-only write plan, 1-time marker, exact target cluster/role, fail-closed preflight; сначала CI/mock, потом пользователь отдельно подтверждает одну операцию. Никаких `rails test`/`fixtures :all` в пятой DB.
- Важный нюанс: существующий `cafe_p13_fifth_catalog_20261107.py --verify` требует **ноль users/orders**. После первых synthetic user/order writes эта старшая проверка перестанет применяться. До записи нужен новый immutable **baseline snapshot и новый postflight** с ожидаемыми synthetic-only count, не переносить предыдущий `p13.verify()` в post-write без изменения логики. Не менять локальные one-shot markers P1.2/P1.3.
- Матрица: guest/registered/admin, real CSRF enabled for POST (test environment ordinarily disables), sign-up/sign-in/sign-out, ACL isolation, account, admin CRUD, scoped roles, quantity/prices/variants/dedup/inventory, 2-session race/foreign order protection, file MIME/magic/size/avatar, CarrierWave path and upload, bad requests, headers and CSP, no outbound email, no real money. Mock data and uploads ONLY, fifth-only temp runtime, no host ports.
- Отдельная независимая verification PASS и неизменность original 4 PG/media before-after.

### D — интеграция и release candidate
- Review entire stacked chain #1–#68, actual bases and duplicate patches, PR64 separate docs and PR65 separate UI, frozen Rails source vs owner dirty working tree. Сформировать новую чистую **release-candidate branch** в GitHub без прямого изменения owner локального каталога. Ruby/Node/Webpack lock compat, CI rails + JS, auth/security/upload, DB migration reproducibility, no secrets/licenses violations. Перед owner local integration — read-only diff/checksum, backup plan, owner confirmation. Не merge `master`, пока нет финального approval и acceptance.
- Риски: legacy Ruby2.5/Rails6 / carrierwave / webpack4, imagemagick, secrets, video/media rights; обновлять legacy deps только после green baseline и отдельного плана.

### E — безопасный публичный demo deployment
- НЕ использовать fifth `tmpfs` как production. Отдельные persistent PostgreSQL/media, app healthcheck, backup + tested restore, SSL, monitoring, rollback, release hash, access control, isolation. Railway или иной провайдер только после реального расчёта цены/ресурсов и явного согласования платных/публичных операций. Никакого настоящего приёма платежей, исполнения заказов или ложного адреса кафе.

### F — portfolio & коммерческое использование
- RU/EN README с датами/точным stack/архитектурой, видео и настоящие desktop/mobile screenshots, CI report, features/limitations и deployment evidence. Существующий Google Drive `06_CAFE_APP_CANDIDATE` с пятью папками: `01_FACTS_AND_COPY_RU_EN` (ID `1JPC6jG5U174_xU70IaluEVSKvH8x5NVr`), `02_SCREENSHOTS_VERIFIED` (`1hug5g6WOE7RnLO8vi0kEjJOEDjDbW3Ts`), `03_VIDEO_RAW_AND_AUDIO` (`18l_HTwd7znNh4P1ifQ4i9I56QizEYjPv`), `04_MOTION_DESIGN_STORYBOARD` (`1dWzJd0ZxgHWGWhixHdDH69nmybGVBgvN`), `05_EXPORTS_READY` (`1jza739-XbgFn3ZvEr9oJ4Y8cuHl6mRTE`). Папку не пересоздавать, источники/лицензии указать.
- Кейс честно обозначать demo/учебным. Обязательный link на GitHub source и реальное deployed demo при готовности. Цель CAREER — реальные лиды и заказы, а не число социальных публикаций.

## 7. Drive/GitHub/Gmail — что читать и куда писать

**Drive master/checkpoint на 07.11:** https://docs.google.com/document/d/11dn_PJIvEROmcgp9AKP6lF6NLKc7H5NmTqVYdk5i9fc/edit ; это накопительный лог с датами, содержит ранние устаревшие строки, **последние дописанные checkpoint важнее первых**. Устаревшие `CAFE_APP_MASTER_HANDOFF_2026-11-05` и `2026-11-06` — исторические мастер-срезы, не исполнять первый шаг из них. Старые UX/security checkpoint сохранять как evidence, не очищать случайно.

**GitHub:** https://github.com/TheGor-365/cafe_app/pull/68 — текущая техническая workstream. Соседние Draft #65 (UI), #66 (schema), #67 (catalog), #64 (historical docs) читать, но не закрывать/мержить без проверки dependency graph. Продолжай в существующем PR68 или новой stacked feature ветке, не делай новых независимых PR на старые основы без необходимости.

**Gmail:** можно адресно проверить уведомления от GitHub Actions по `cafe_app` и Railway, но первичное доказательство кода/CI — GitHub job/commit. Ничего не отправлять автоматически на внешние адреса без конкретной задачи.

**Передача статуса:** по окончании существенного этапа обнови PR body и актуальный Drive checkpoint (readback) с `дата | факт | owner vs CI evidence | SHA/PR/URL | статус | блокер | следующий gate`; если создаёшь новый MASTER, отмечай старый `SUPERSEDED` и аккуратно сверяй связь/права. Не удаляй доказательные PR, старые технические checkpoint, uploads или client/private media. User просил удалить неактуальные *мастера* — cleanup только после идентификации точных устаревших документов и сохранения нового verified canonical. Не применять удаление к другим CAREER-проектам.

## 8. Строгие критерии готовности

**Сделано:** source и CI, fifth PG schema/fixtures, изолированный backend GET/guest ACL, реальная Webpack сборка в GitHub, целостность ZIP на Linux.

**Осталось:** верификация структуры ZIP, fifth-only GET с настоящими assets, браузерный JS/CSS/viewport/accessibility, пятая DB writable E2E с реальным CSRF/ACL, admin credentials recovery, upload hardening acceptance, объединение stacked PR, release code freeze+full CI, persistent deploy+backup/restore, public URL, evidence/screenshots/video, case RU/EN в Drive, опциональный marketing handoff.

**Не считать выполненным:** все приложения/PR merged, браузер исправлен, Stripe/реальные платежи подключены, клиентские заказы существуют, IP/bank status изменён, все сервисы автоматически синхронизированы с Drive/GitHub, или публичный сайт успешно развёрнут. Никаких обманных коммерческих тезисов.

## 9. Как начать НОВЫЙ чат (операционная инструкция)

1. Прочитать этот файл; самостоятельно `GitHub get_pr_info` #68, текущие changes/CI, Drive continuation checkpoint и PR #65; проверить SHA/браузерные статусы на дату нового запуска.
2. Автономно продолжить исследование/исправления remote PR/CI. Если v2 gate CI уже зелёный, нужен **один** локальный read-only вывод `stat/id/sha256sum` из раздела 1. Не предлагать удалять старый архив или скачивать его повторно без причины.
3. Если file UID/permissions подтвердят безопасное точечное исправление — сначала объяснить его, затем выполнить в новом файле v2 `--verify-archive`, и только после PASS переходить к separate `--check-real-get` и roadmap.

**Формат первой реплики:** коротко сообщить, что P1.2/P1.3 и P1.4 серверный GET/ACL выполнены, реальный Webpack build CI PASS, а последний локальный блокер — избыточно обобщённая проверка metadata ZIP. Указать, что сам проверяешь GitHub и Drive, что no code/repo/DB reset. Затем дать одну безопасную read-only команду после GitHub аудита.

**Формула успеха:** настоящее, проверяемое приложение и оплачиваемое портфолио, а не зелёные PR ради зелёных PR. При неясности — STOP, диагностика read-only, независимая ветка работы и evidence; не обходить защитные маркеры.
