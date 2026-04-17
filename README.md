
```
      .o.       ooooooooo.     .oooooo.    ooooo     ooo  .oooooo..o
     .888.      `888   `Y88.  d8P'  `Y8b   `888'     `8' d8P'    `Y8
    .8"888.      888   .d88' 888            888       8  Y88bo.
   .8' `888.     888ooo88P'  888            888       8   `"Y8888o.
  .88ooo8888.    888`88b.    888     ooooo  888       8       `"Y88b
 .8'     `888.   888  `88b.  `88.    .88'   `88.    .8'  oo     .d8P
o88o     o8888o o888o  o888o  `Y8bood8P'      `YbodP'    8""88888P'
```

> **CRYPTO ADDRESS INTELLIGENCE ENGINE**
> *by VERES · Intelligence without borders*

---

## ◈ СТРУКТУРА ПРОЕКТА

```
argus/
├── argus.py              ← Основной инструмент — анализ адресов
├── argus_youtube.py      ← Парсер адресов с конкретного YouTube канала
├── argus_yt_monitor.py   ← Глобальный мониторинг YouTube
├── argus_db_update.py    ← Обновление публичных баз данных
├── custom_labels.json    ← Пользовательская база адресов
├── requirements.txt      ← Python зависимости
├── .env                  ← Твои API ключи (создать из .env.example)
└── .env.example          ← Шаблон для ключей
```

---

## ◈ УСТАНОВКА

```bash
# 1. Клонировать / скачать файлы в папку
mkdir argus && cd argus

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Создать .env файл
cp .env.example .env
# Открыть .env и вставить свои ключи

# 4. Запустить
python3 argus.py 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
```

---

## ◈ ARGUS.PY — Анализ адресов

### Поддерживаемые сети
Авто-определение по формату адреса:

| Адрес начинается с | Сеть |
|---|---|
| `0x...` | ETH + BSC + Polygon + Arbitrum + Base |
| `1...` / `3...` / `bc1...` | Bitcoin |
| `T...` | Tron |
| `[1-9A-Z]{43-44}` | Solana |
| `EQ...` / `UQ...` | TON |

### Запуск

```bash
# Ethereum / EVM
python3 argus.py 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Bitcoin
python3 argus.py 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa

# Tron
python3 argus.py TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE

# Solana
python3 argus.py 9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM

# TON
python3 argus.py EQD2NmD_lH5f5u1Kj3KfGyTvhZSX0Eg6qp2a5IQUKXxOG3a
```

### Что показывает отчёт

```
BALANCES BY CHAIN       — баланс на каждой активной сети
SANCTIONS CHECK         — OFAC + EU + UN + UK OFSI
ADDRESS ATTRIBUTION     — кому принадлежит адрес
CLUSTER ANALYSIS        — поведенческие паттерны
TOP COUNTERPARTIES      — с кем чаще всего транзакции
KNOWN ENTITY INTERACTIONS — контакты с биржами/миксерами
WALLET INTELLIGENCE     — профиль, возраст, объём, источник финансирования
PUBLIC MENTIONS         — упоминания на GitHub
SUMMARY                 — итоговый риск
```

### Профили кошельков

```
BOT              — высокая частота, в основном контрактные вызовы
TRADER           — 40%+ DeFi/контракты
BRIDGE/EXCHANGE  — balanced in/out
HOLDER           — мало транзакций, долго держит
DORMANT          — неактивен 365+ дней
FRESH WALLET     — создан недавно
ACTIVE WALLET    — обычная смешанная активность
```

### API ключи

| Ключ | Где получить | Обязательность |
|---|---|---|
| `ETHERSCAN_API_KEY` | etherscan.io/register | Обязательно для EVM |

---

## ◈ CUSTOM_LABELS.JSON — Пользовательская база

Добавляй свои адреса в `custom_labels.json`:

```json
{
  "0xАДРЕС": {
    "name": "Название / описание",
    "category": "person / ngo / exchange / scam / ...",
    "risk": "low"
  },
  "1BTC_АДРЕС": {
    "name": "ФБК Навального",
    "category": "ngo",
    "risk": "low"
  }
}
```

Файл должен лежать **рядом с argus.py**. Приоритет выше всех других источников.

---

## ◈ ARGUS_DB_UPDATE.PY — Публичные базы данных

Скачивает и агрегирует публичные базы:

| Источник | Содержимое | Адресов |
|---|---|---|
| OFAC SDN | Санкции США — ETH/BTC/TRX/SOL/LTC/XMR | ~2000 |
| OpenSanctions | OFAC + EU + UN + UK + 20 списков | ~3000+ |
| Ransomwhere.co | Адреса вымогателей | ~5000+ |
| MetaMask Phishing | Фишинговые ETH адреса | ~10000+ |
| Etherscan Labels | Биржи, DeFi, известные кошельки | ~10000+ |
| CryptoScamDB | Скам адреса | ~5000+ |

```bash
# Посмотреть список источников
python3 argus_db_update.py --list

# Обновить всё
python3 argus_db_update.py

# Только санкционные списки
python3 argus_db_update.py --sources ofac opensanctions

# Только высокий риск (санкции + мошенники)
python3 argus_db_update.py --sources ofac ransomwhere phishing scam

# Слить с существующим custom_labels.json
python3 argus_db_update.py --merge

# Сохранить в другой файл
python3 argus_db_update.py --out my_db.json
```

Результат сохраняется в `custom_labels.json` → автоматически используется в `argus.py`.

---

## ◈ ARGUS_YOUTUBE.PY — Парсер канала

Собирает крипто-адреса из описаний видео конкретного канала.

### Нужен ключ

```
YOUTUBE_API_KEY=...  # в .env
```

Получить: console.cloud.google.com → APIs → **YouTube Data API v3** → Credentials → API Key

### Запуск

```bash
# Парсить канал по @handle
python3 argus_youtube.py @channelname

# Парсить последние 50 видео
python3 argus_youtube.py @channelname --max 50

# Также парсить закреплённые комментарии
python3 argus_youtube.py @channelname --comments

# Без Solana адресов (меньше ложных срабатываний)
python3 argus_youtube.py @channelname --no-sol

# Сохранить в другой файл
python3 argus_youtube.py @channelname --out fbk_labels.json
```

Результат автоматически добавляется в `custom_labels.json`.

---

## ◈ ARGUS_YT_MONITOR.PY — Глобальный мониторинг YouTube

Ищет крипто-адреса по всему YouTube через поисковые запросы.

### Нужны ключи

```
YOUTUBE_API_KEY=...   # обязательно
GOOGLE_CSE_KEY=...    # опционально — расширяет охват
GOOGLE_CSE_CX=...     # Search Engine ID от cse.google.com
```

**Google CSE настройка:**
1. Зайти на cse.google.com
2. Create engine → в поле сайты написать `youtube.com`
3. Скопировать Search Engine ID → в `.env` как `GOOGLE_CSE_CX`

### Запуск

```bash
# Стандартный запуск — все языки, 100 запросов
python3 argus_yt_monitor.py

# Только русскоязычный YouTube
python3 argus_yt_monitor.py --lang ru

# Видео за последние 7 дней
python3 argus_yt_monitor.py --days 7

# Без Solana (меньше мусора)
python3 argus_yt_monitor.py --no-sol

# Пропускать уже виденные видео
python3 argus_yt_monitor.py --new-only

# Полный режим
python3 argus_yt_monitor.py --lang ru --days 30 --no-sol --new-only
```

**Квоты YouTube API (бесплатно):**
- 10,000 units/день
- Search = 100 units/запрос → 100 запросов → ~5,000 видео/день

---

## ◈ РЕКОМЕНДУЕМЫЙ WORKFLOW

```bash
# 1. Первый запуск — заполнить базу публичными данными
python3 argus_db_update.py

# 2. Найти адреса на интересующих каналах
python3 argus_youtube.py @channelname --comments

# 3. Глобальный мониторинг (раз в день/неделю)
python3 argus_yt_monitor.py --lang ru --no-sol --new-only

# 4. Проверить конкретный адрес
python3 argus.py <ADDRESS>
```

---

## ◈ ЧАСТЬ ЭКОСИСТЕМЫ VERES

```
VERES ──────────────────────────────────────────────────
  ├── VELES     · 1300+ OSINT tool directory
  ├── ARGUS     · Crypto address intelligence  ◄ YOU ARE HERE
  └── MURAMASA  · [in development]
```

---

## ◈ DISCLAIMER

```
Инструмент предназначен только для OSINT и compliance исследований.
Используй ответственно и в соответствии с применимым законодательством.
Автор не несёт ответственности за неправомерное использование.
```

---

*ARGUS · VERES · Yerevan · 2026*
