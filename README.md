# Gor's Coffee — Rails portfolio demo

[Русский](#русский) · [English](#english)

> **Portfolio demonstration only.** This is not an operating coffee shop. Prices and products are sample data. The app does **not** accept payments, process real orders, guarantee fulfilment or represent actual customers.

## Русский

### Назначение и статус

Gor's Coffee — учебно-портфолийный веб-сервис кофейни с демонстрационным каталогом, конструктором напитков и корзиной. Цель: показать клиенту реальные навыки Ruby on Rails, PostgreSQL, серверной проверки цен, адаптивной вёрстки и тестирования.

**Статус на 2 ноября 2026:** разработка ведётся цепочкой **Draft PR** (#6–#23), поверх исторического `master`. Ветка `master` сама по себе **не содержит всех описанных ниже улучшений**. Смотрите [PR #23](https://github.com/TheGor-365/cafe_app/pull/23) (публичные страницы), [PR #20](https://github.com/TheGor-365/cafe_app/pull/20) (управление количеством), [PR #19](https://github.com/TheGor-365/cafe_app/pull/19) (панель настройки) и [план доведения проекта](https://github.com/TheGor-365/cafe_app/issues/21). Изображения и действия, отмеченные как «запланировано», не считаются реализованными.

### Реализованные сценарии в ветке PR #23

- Главная `/`: категории, популярные товары, переход в меню.
- Каталог `/menu`: поиск по названию, категория, пищевой фильтр, пустые результаты.
- 20 демонстрационных позиций в каталоге; база может содержать старые учебные позиции. Данные формируются только локальными dev/test seeds.
- Шесть конфигурируемых напитков: размеры S/M/L, опциональное молоко, сироп, дополнительный шот эспрессо.
- Компактные карточки и панель настройки, в том числе HTML `<details>` как fallback при отключённом JavaScript.
- Динамический предварительный расчёт цены на JavaScript **только для отображения**; окончательная цена и доступность проверяются сервером.
- Корзина `/cart`: добавление, редактирование количества, удаление, объединение совпадающих конфигураций, сохранение снимка цены и добавок. В PR #20 добавлены кнопки `−` и `+` (1–20), но сохранён ручной ввод. В корзине изменение сохраняется только по `Update`.
- Rails Devise: базовые аккаунты и административные операции; создание/изменение/удаление товаров и категорий проверяет права на сервере.

Дополнение PR #23: публичные `/products/:id` переиспользуют настоящий конфигуратор и добавление в корзину; `/info` содержит About, FAQ, контакт разработчика и честно обозначенный декоративный блок карты без адреса; `/catering` описывает концепцию без приёма заказов; общий подвал ведёт на все эти разделы. Дизайн Devise и административных экранов ещё не выровнен. Полная проверка реального Android/клавиатуры не завершена. В рамках этой ветки обновлены брендированные статические страницы `404`, `422`, `500`, метатеги и SVG favicon, однако это **ещё не протестированный публичный релиз**. Checkout, email-доставка, реальные цены, CRM и платежи отсутствуют.

### Стек

| Слой | Текущая ветка |
| --- | --- |
| Backend | Ruby **2.5.8**, Ruby on Rails **6.0.x** |
| Database | PostgreSQL (локальный/CI — 16) |
| Frontend | ERB, Sprockets/SassC, Bootstrap 4, JavaScript, Turbolinks |
| Build | Webpacker 4 / Webpack 4, Node.js 14 для воспроизведения старой сборки |
| Authentication | Devise; роли `admin` проверяются в контроллерах |
| QA | Minitest / ActionDispatch integration, Node.js assertion tests, GitHub Actions |
| Images | CarrierWave; локальные/проектные файлы, права на медиа требуют проверки |

> **Поддержка и безопасность:** Ruby 2.5 достиг EOL в 2021 году, Rails 6.0 также вне официальной поддержки. Не размещать этот legacy-стек в открытом интернете без отдельного обновления и проверки безопасности. Официальные ссылки: [Ruby 2.5 EOL](https://www.ruby-lang.org/en/news/2021/04/05/ruby-2-5-9-released/) и [Rails maintenance policy](https://rubyonrails.org/maintenance). Обновление зависимостей — отдельная задача, а не часть визуального редизайна.

### Архитектура и источники данных

```text
Browser ── Rails routes/controllers ── ActiveRecord ── PostgreSQL
   │               │
   ├── ERB + Sprockets CSS
   ├── Webpacker JS (price preview, dialog, quantity controls)
   └── Session cookie → Order → OrderItems → saved option/price snapshots
```

Ключевые файлы:
- `config/routes.rb`, `app/controllers/{pages,menu,cart,order_items,products,categories}_controller.rb`;
- `app/views/pages/`, `app/views/menu/`, `app/views/cart/`, `app/views/products/`, `app/views/devise/`;
- `app/models/{product,product_variant,product_modifier_option,order,order_item,order_item_modifier}.rb`;
- `app/services/cart_line_consolidator.rb`;
- `app/javascript/{coffee_price_preview,coffee_config_panel,coffee_quantity_stepper}.js`;
- `db/migrate/20261102000100_create_cafe_drink_options.rb` и `db/seeds.rb`.

**Сервер — источник истины по цене.** Клиент не может задать `unit_price` или `total`; Rails подбирает доступные размеры/добавки и пересчитывает сумму. Количество ограничено проверкой модели, независимо от кнопок браузера.

### Локальная разработка

Проект исторический. Используйте изолированный контейнер или окружение с версиями Ruby/Node, указанными выше. **Готовый Docker Compose и Dockerfile в этой ветке не включены**: рабочая локальная инфраструктура владельца создана отдельно и не должна считаться воспроизводимой «одной командой» из GitHub. Детали Docker/backup и проверенных задач описаны в `docs/` и [Issue #21](https://github.com/TheGor-365/cafe_app/issues/21).

Безопасная последовательность **только для новой временной тестовой базы, никогда не для существующей локальной базы**:

1. Подготовить Ruby 2.5.8, совместимый Bundler, PostgreSQL и Node.js 14 / Yarn 1.x в изоляции.
2. Создать новую пустую БД и настроить `DATABASE_URL` для **этой временной БД**. Не использовать реквизиты рабочего `cafe`, `production` или чужих баз.
3. Установить зависимости `bundle _2.2.13_ install`, `yarn install --frozen-lockfile`.
4. Применить схему/миграции только в этой БД. Убедиться, что версия схемы соответствует выбранной feature-ветке.
5. Выполнять `db:seed` **только осознанно в development/test на временной БД**: seed обновляет демонстрационные товары и категории.
6. Собрать `./node_modules/.bin/webpack --config config/webpack/development.js`, запустить Rails и проверить `/`, `/menu`, `/cart`.

Для разработки владельца: **не запускать `db:drop`, `db:reset`, `git reset --hard`, `git clean`, массовую замену файлов или повторные seeds**. Рабочий checkout содержит незакоммиченные изменения, приватные uploads и отдельный PostgreSQL. Перед импортом новой ветки нужен приватный backup и пофайловая сверка Git-хешей; bundle/assets собираются в staging Docker volume.

### Тестирование и CI

GitHub Actions на PR #20 (Ruby / Node.js / Webpack) проверяет интеграцию с временным PostgreSQL и настоящую сборку JavaScript. Подтверждённый запуск PR #22: **86 runs / 566 assertions / 0 failures / 0 errors / 0 skips**, Node unit tests и Webpack PASS. Итоговые CI результаты PR #23 проверяются отдельно.

```sh
# Только в подготовленном временном test-окружении:
RAILS_ENV=test bundle _2.2.13_ exec rails test
node test/javascript/coffee_price_preview.test.js
node test/javascript/coffee_config_panel.test.js
node test/javascript/coffee_quantity_stepper.test.js
./node_modules/.bin/webpack --config config/webpack/development.js
```

В **CI** используется контролируемый список Rails integration suites из `.github/workflows/coffee-quantity-stepper.yml`. Команда `rails test` над **всем** старым набором и browser/system suite отдельно ещё должна пройти аудит; зелёная выборка не доказывает их работоспособность. Для browser QA нужны Chrome/Android или другой реальный мобильный браузер, viewport 320/360/390/768/1024/1440, отсутствие горизонтального скролла, Tab/Shift+Tab/Escape, no-JS fallback, формы и раздельные гостевые сессии.

### Безопасность, приватность, права на медиа

- Подмена цены и чужой корзины должна отвергаться сервером; не доверяйте цене с JavaScript.
- Никогда не публикуйте `config/master.key`, `.env`, секреты, клиентские данные, дампы БД или приватные `public/uploads/user/`.
- Фотографии из старого проекта и `public/uploads/product/` требуют подтверждения происхождения/лицензий перед внешней публикацией.
- Devise `mailer_sender` всё ещё содержит placeholder, а dev email URL настроен на localhost:3000 — восстановление пароля по email не подтверждено.
- Оригинальные `favicon.ico` и `apple-touch-icon*.png` сохранены; новая SVG-иконка собственная и подключена явно.
- Страницы 404/422/500 независимы от Rails layouts и Webpacker, поэтому могут отображаться при отказе приложения.

### План завершения

Полная матрица страниц, приоритеты и условия принятия: [GitHub Issue #21](https://github.com/TheGor-365/cafe_app/issues/21). Критические этапы: локальная приёмка PR #23 (новые публичные страницы) → оформление Devise/админки и mobile → browser regression и security → разрешённые медиа, двуязычные скриншоты, проверенный deploy → отдельная миграция с устаревшего стека.

### Публикация

Коммерческий сайт не запущен, реальные клиенты/заказы/платежи не заявлены. Публиковать демо только после обновления legacy-зависимостей, проверки данных/медиа, заполнения всех страниц, тестового развёртывания, backup и явного решения владельца.

---

## English

### What this project demonstrates

**Gor's Coffee** is a Ruby on Rails portfolio demo, not a real café. It shows product browsing and filters, configurable coffee sizes/add-ons, instant estimated pricing and a session-based demo cart. Rails validates each selection and calculates final line prices on the server. No real checkout, payment, delivery or customers.

### Project status

The latest functionality lives in stacked **unmerged Draft PRs**, culminating in [PR #23](https://github.com/TheGor-365/cafe_app/pull/23); `master` is not yet this complete version. Source audit and acceptance plan: [Issue #21](https://github.com/TheGor-365/cafe_app/issues/21). On PR #22, Ruby CI verified **86 runs / 566 assertions, zero failures**, plus successful Node tests and Webpack 4 build. CI on PR #23 is checked independently. Browser/mobile acceptance and independent clean-install verification remain open.

### Stack and setup

Legacy **Ruby 2.5.8 / Rails 6.0**, PostgreSQL, ERB, Bootstrap 4/Sprockets, Webpacker 4, Node 14, Turbolinks, Devise, CarrierWave and Minitest. These Ruby/Rails series are unsupported and require a dedicated upgrade before public exposure.

The repository **does not provide a complete Docker Compose or Dockerfile**. Use a disposable database and isolated legacy environment; avoid running migrations/seeds against any existing checkout/database. See the Russian sections above for the exact cautionary workflow and CI commands.

### Current route inventory

- `/`: home and featured catalogue
- `/menu`, `/search`: filters, catalogue and accessible drink options
- `/cart`: demo cart, quantity controls, explicit updates and removal
- `/products/:id`: redesigned demo product details reusing the same configurable form and server-owned price logic
- `/info`: About / FAQ / location disclaimer / developer project contact; `/catering`: concept showcase (no bookings)
- `/users/sign_in` etc.: Devise auth screens, legacy layout, email delivery not verified
- `/products`, `/categories`: technical/admin lists requiring UI separation
- `public/404.html`, `422.html`, `500.html`: standalone branded static error pages; all ordinary pages include a shared footer in PR #23

### Release and attribution policy

No real checkout or fake reviews. Media licensing, admin UX, accessibility, mobile QA, security, README evidence, and Ruby/Rails upgrades must be checked before deployment. Images and videos used in a public portfolio must be real captures of the finished demo; never publish private avatars, credentials or user uploads.
