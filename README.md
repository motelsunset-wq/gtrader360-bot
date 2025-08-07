
# GTRADER360 Daily Bot

Ежедневно публикует анализ в Telegram-канал в **09:00 по UTC+4** (таймзона по умолчанию `Asia/Dubai`).

## Переменные окружения
- `TELEGRAM_BOT_TOKEN` — токен бота
- `TELEGRAM_CHANNEL` — ID канала или `@username`
- `OPENAI_API_KEY` — ключ OpenAI
- `OPENAI_MODEL` — (опц.) модель, по умолчанию `gpt-4o-mini`
- `SCHEDULE_TZ` — (опц.) таймзона, по умолчанию `Asia/Dubai` (UTC+4)
- `SCHEDULE_HOUR` — (опц.) час (по таймзоне), по умолчанию `9`
- `SCHEDULE_MINUTE` — (опц.) минуты, по умолчанию `0`
- `STATIC_PROMPT` — (опц.) запрос к модели, если не указать — используется дефолт из кода

## Запуск локально
```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=xxx
export TELEGRAM_CHANNEL=@gtrader360coil
export OPENAI_API_KEY=sk-...
python main.py
```

## Railway (или любой PaaS)
1. Создай новый проект и подключи репозиторий/загрузку из ZIP.
2. В Variables добавь:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHANNEL` (например, `@gtrader360coil`)
   - `OPENAI_API_KEY`
   - (опц.) `SCHEDULE_TZ=Asia/Dubai`
3. Тип процесса: `worker` (Procfile уже настроен).
4. Задеплой и проверь логи. Бот должен написать в канал в назначенное время.

## Важно
- Сделай бота админом канала с правом *Post messages*.
- Если нужна фиксация времени именно 09:00 по Израилю (UTC+3), задай `SCHEDULE_TZ=Asia/Jerusalem`.
- Если твоё целевое время — **09:00 по UTC+4**, оставь `Asia/Dubai`.
