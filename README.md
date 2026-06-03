# Habit Tracker Bot (A-Moral Track)

Telegram-бот для отказа от вредных привычек: **курение**, **алкоголь**, свои привычки.

## Возможности

- Счётчик дней, часов, минут и streak (текущий + лучший рекорд)
- Экономия денег, цель «коплю на…», учёт потраченного из сэкономленного
- Мотивация по слотам + **вечерний дайджест** одним сообщением
- **SOS /urge**: HALT-чеклист, таймер 10 мин, Radio Gram, плейлист по типу привычки
- «Почему бросил» — напоминание в SOS
- Заморозка streak (1× в месяц), триггеры после срыва
- Челлендж с другом (`/challenge`, `/buddy`)
- Карточка streak для шаринга (`/share`)
- Недельный отчёт (воскресенье)
- Тихие часы, настройка слотов, `/edit` для ₽/день
- Анонимный счётчик «держатся сегодня»
- Быстрый старт для пресетов (⚡)

## Быстрый старт

1. Создай бота через [@BotFather](https://t.me/BotFather)
2. Скопируй токен:

```bash
set TELEGRAM_BOT_TOKEN=123456:ABC...
```

3. Запуск локально:

```bash
npm run bot:habit-tracker
```

4. Self-test (без Telegram):

```bash
npm run bot:habit-tracker:self-test
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `TELEGRAM_BOT_TOKEN` | Токен бота | обязательно |
| `BOT_USERNAME` | Username для ссылок челленджа | `amoraltrack_bot` |
| `PORT` | HTTP health-check | `8788` |
| `BOT_STATE_PATH` | Путь к state.json | `data/state.json` |
| `BOT_DATA_DIR` / `DATA_DIR` | Папка state (**Bothost: `/app/data`**) | `data` |
| `BOT_CONFIG_DIR` | motivation, articles, playlists | `config` |
| `RADIO_GRAM_URL` | Ссылка на плеер | `https://player.radiogram.su/` |
| `REMINDER_*` | Часы слотов напоминаний | 9, 13, 17, 20 |

## Деплой на Bothost

Bothost монтирует **пустой persistent volume** на `/app/data`. Туда пишется **только** `state.json` — пользователи и streak **не теряются** при перезапуске.

```
bot.js
lib/
  extras.js
config/
  motivation.json
  replacements.json
  articles.json
  savings-ideas.json
  playlists.json
  images.json
  images/          ← опционально, картинки мотивации
```

Env на Bothost:
- `TELEGRAM_BOT_TOKEN`
- `BOT_DATA_DIR=/app/data`
- `PORT=8080`
- Entry: `bot.js`

> **Важно:** не клади `config/` в volume — при пустом mount конфиги пропадут. Config — в репозитории/файлах деплоя, state — в volume.

## Команды

| Команда | Действие |
|---------|----------|
| `/start` | Главное меню |
| `/stats` | Прогресс, streak, цель |
| `/urge` | SOS: HALT, таймер, Radio Gram |
| `/edit` | Изменить ₽/день |
| `/goal` | Цель «коплю на…» |
| `/spent` | Потратил из сэкономленного |
| `/share` | Карточка streak |
| `/freeze` | Заморозка streak (1×/мес) |
| `/challenge` | Челлендж с другом |
| `/buddy` | Сравнение с другом |
| `/relapse` | Записать срыв + триггер |
| `/settings` | Напоминания, тихие часы, дайджест |
| `/help` | Справка |

## Дисклеймер

Бот — поддерживающий инструмент, **не заменяет** врача. При тяжёлой зависимости обращайтесь к специалистам.
