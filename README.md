# caddy_finder — поиск VW Caddy для JDG

Собирает реальные объявления VW Caddy с польских площадок в одну SQLite-базу.
Помечает цены, которые требуют флоты или финансирования, и считает «реальную»
цену для вашего статуса VAT. Результат: `output/report.html` (адаптирован под
телефон), `output/listings.csv` и короткая сводка в консоли.

Ориентир по умолчанию: Caddy 1.5 TSI 116 KM, MY2027 po lifcie, rozstaw 2755 mm,
флотовая цена 95 053 netto / 116 915 brutto.

## Источники (проверено 2 ноября 2026)

| Площадка | Статус | Как берём данные | robots.txt |
|---|---|---|---|
| **otomoto.pl** | ✅ работает | `requests`, JSON из `__NEXT_DATA__` в поиске и в объявлении. Kombi ищем в `/osobowe/volkswagen/caddy`, Cargo — в `/dostawcze/volkswagen/q-caddy` (в «dostawcze» нет фильтра модели) | `Allow: /`, нужные пути не запрещены |
| **olx.pl** | ✅ работает через API | HTML-поиск отдаёт капчу «Human Verification», его не трогаем. Используем публичный `/api/v1/offers/`: robots.txt **явно разрешает** его (`Allow: /api/v1/offers/`). `requests` получает 403 от CloudFront, поэтому запросы идут через обычный headless Chromium (Playwright), без логина и без решения капчи | `/api/` запрещён, но `/api/v1/offers/` разрешён |
| **autoplac.pl** | ⛔ заблокирован | Cloudflare-челлендж («Cierpliwości…») даже на `robots.txt`, и для requests, и для браузера. Обход не делаем: модуль только проверяет доступность при каждом запуске | недоступен |
| **vehis.pl** | ✅ работает | Онлайн-лизинг со своей витриной авто. JSON из `__NUXT_DATA__`. Есть цена дилера (без условий) и «cena w VEHIS» (ниже, но только с финансированием VEHIS) | пути витрины не запрещены |
| **carleasepolska.pl** | ✅ работает | Брокер najmu: карточки Caddy и Caddy Cargo с ценой авто netto и ставкой netto/мес. | `/wynajem-dlugoterminowy/` разрешён (запрещены `/oferta/`, `/api/`) |
| **ayvens.com/pl-pl** (Ayvens Flex) | ✅ работает | Страница модели Caddy в Ayvens Flex (najem 1–24 мес.), ставка netto | запрещены только `*dostac-wycene*` |

Что проверил и **не** нашёл с Caddy и опубликованной ставкой:

* Ayvens, «oferta dla firm» — в каталоге нет Caddy.
* Otomoto Lease (бывший Carsmile, `otomoto.pl/otomotolease`) — в sitemap есть только VW Crafter, Polo, T-Cross, T-Roc и Taigo.
* Arval (`arval.pl/wynajem-oferty`) — в sitemap Caddy нет.
* VWFS (`vwfs.pl`) — robots.txt отвечает редиректом 301, сайт дальше не исследовал.
* Alphabet — не проверял.

Почти все объявления Caddy на OLX — это экспорт из otomoto: у них
`partner=otomoto_pl_form` и `external_url` ведёт на otomoto. Такие копии
склеиваются с оригиналом, а OLX добавляет к записи VIN (otomoto показывает VIN
только за reCAPTCHA).

## Установка

```bash
git clone <repo> caddy && cd caddy
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium     # нужен для OLX API
```

Нужен Python 3.10 или новее.

## Запуск

```bash
python -m caddy_finder                    # все источники из config.yaml
python -m caddy_finder --sources otomoto  # только otomoto
python -m caddy_finder --offline          # без сети, только по кэшу (удобно для отладки отчёта)
python -m caddy_finder -v                 # подробный лог
```

Результаты:

* `output/report.html` — откройте в браузере или на телефоне. Есть фильтры по
  площадке, версии, макс. цене, «скрыть флот», «только FV 23%» и «только 1.5 TSI»,
  а также сортировка. Бейджи: «флотовая цена / финанс.», «снижение цены», «новое».
  Блок топ-10 по совпадению с ориентиром. Отдельный блок najmu/leasingu со ставками.
* `output/listings.csv` — разделитель `;`, кодировка UTF-8 с BOM (открывается в Excel).
* `data/caddy.sqlite` — таблицы `listings`, `price_history`, `runs`, `source_status`.

## Фильтры (`config.yaml`)

```yaml
search:
  year_from: 2025
  year_to: 2027
  price_min: null
  price_max: 200000        # brutto, как на сайте
  fuel: [petrol]           # petrol | diesel | hybrid | cng | lpg | electric; [] = любое
  gearbox: []              # manual | automatic
  power_min: null
  power_max: null
  versions: [Kombi, Cargo] # добавьте Maxi, чтобы видеть длинную базу (2970 mm), и California для кемпера
  max_mileage: 30000
  include_used: true

company:
  vat_status: czynny       # czynny → сравнение netto; zwolniony → brutto
  vat_deduction_pct: 100   # 50 — для легкового Kombi при смешанном использовании
```

Остальные секции:

* `reference` — ориентир для топ-10.
* `sources` — включение и выключение площадок.
* `politeness` — паузы, лимит страниц, сроки кэша.

## Логика

* **Вежливость.** Пауза 3–6 с со случайным разбросом между запросами к одному
  домену. Не больше `max_pages` (200) сетевых запросов за запуск. Поиск кэшируется
  на 6 ч, страницы объявлений — на 30 дней. Детальные страницы otomoto: не больше 80
  новых за запуск, сначала самые дешёвые. User-Agent — обычный Chrome. Перед первым
  запросом к домену читается robots.txt; запрещённый путь не скачивается, источник
  получает статус `robots`. Если robots.txt недоступен или в ответе капча, статус —
  `blocked`.
* **netto/brutto.** brutto = netto × 1,23 только при Faktura VAT 23%. Без FV
  (частник, VAT marża) netto не считается.
* **Флот и финансирование.** В описании ищутся фразы-условия: «cena dla firm
  posiadających flotę», «rabat flotowy», «Small Fleet», «cena uwarunkowana…
  przy finansowaniu», «cena w leasingu», «z finansowaniem» и т.п. Рекламные
  фразы вроде «Zapytaj o rabaty flotowe» или «Promocyjne finansowanie VWFS» флаг
  не ставят. Если в тексте есть цена «bez finansowania / za gotówkę / dla firm bez
  floty», она становится реальной ценой. Если нет — запись помечается «уточнить
  у продавца», а в заметку попадает cena katalogowa как потолок.
* **Цена «для меня».** Для czynny — netto при FV 23% (или netto плюс невычитаемая
  часть VAT, если `vat_deduction_pct` < 100). Без FV — полная сумма. Для zwolniony —
  всегда brutto.
* **Дедупликация.** Сначала VIN. Затем ссылка OLX → otomoto (`external_url`).
  Затем отпечаток «год + мощность + пробег + цена + город», но только между
  разными площадками: у дилера бывает несколько одинаковых машин по одной цене.
* **Совпадение с ориентиром (0–100).** 1.5 TSI +30, 116 KM +20, MY2027 +20
  (или год 2026/2027 +10), «po lifcie» +5, база 2755 mm +10, Kombi +5, новый +5,
  близость цены к 95 053 netto — до +5.
* **История.** Каждое изменение цены пишется в `price_history`. В консоли видно,
  что появилось, подешевело, подорожало и исчезло с прошлого запуска.

## Запуск по расписанию

`schedule.interval_hours` в конфиге — подсказка. Само расписание задаётся системой.

**cron (Linux/macOS)** — каждые 12 часов в 7:17 и 19:17:

```cron
17 7,19 * * * cd /path/to/caddy && .venv/bin/python -m caddy_finder >> data/run.log 2>&1
```

**launchd (macOS)** — `~/Library/LaunchAgents/pl.caddy.finder.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>pl.caddy.finder</string>
  <key>WorkingDirectory</key><string>/Users/YOU/caddy</string>
  <key>ProgramArguments</key><array>
    <string>/Users/YOU/caddy/.venv/bin/python</string><string>-m</string><string>caddy_finder</string>
  </array>
  <key>StartInterval</key><integer>43200</integer>
  <key>StandardOutPath</key><string>/Users/YOU/caddy/data/run.log</string>
  <key>StandardErrorPath</key><string>/Users/YOU/caddy/data/run.log</string>
</dict></plist>
```

```bash
launchctl load ~/Library/LaunchAgents/pl.caddy.finder.plist
launchctl start pl.caddy.finder     # запустить сразу
```

Чаще раза в несколько часов запускать смысла нет: объявления обновляются
медленно, а площадкам лишняя нагрузка ни к чему.

## Ограничения

* Скрипт не придумывает цены: всё берётся из данных площадок. Цены «od» у
  najmu — стартовые ставки площадки, а не персональная оферта.
* Распознавание флотовых условий работает по тексту и может ошибаться. Найденные
  фразы видны в отчёте, финальные условия уточняйте у дилера.
* Рок модельный берётся только из явных упоминаний в описании («Rok modelowy
  2027», «MY27»). Если продавец его не указал, поле пустое.
* Если площадка поменяет структуру JSON, источник получит статус `error` с
  причиной в отчёте, остальные продолжат работать.
