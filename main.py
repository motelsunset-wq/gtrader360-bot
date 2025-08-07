import os
import logging
from datetime import time
from zoneinfo import ZoneInfo

from telegram.ext import Application, ContextTypes

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL   = os.getenv("TELEGRAM_CHANNEL")  # e.g. @gtrader360coil
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL       = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SCHEDULE_TZ        = os.getenv("SCHEDULE_TZ", "Asia/Dubai")  # можно переопределить на Asia/Jerusalem
SCHEDULE_HOUR      = int(os.getenv("SCHEDULE_HOUR", "9"))
SCHEDULE_MINUTE    = int(os.getenv("SCHEDULE_MINUTE", "0"))
STATIC_PROMPT      = os.getenv("STATIC_PROMPT", "").strip()

if not STATIC_PROMPT:
    STATIC_PROMPT = (
        "Сделай анализ по методу Ганна (симметрия времени, углы Ганна, Square of 9) "
        "для следующих пар: USD/CAD, EUR/JPY, EUR/USD, EUR/CHF, USD/CHF, EUR/GBP, "
        "GBP/USD, AUD/CAD, NZD/USD, GBP/CHF, AUD/USD, GBP/JPY, USD/JPY, CHF/JPY, "
        "EUR/CAD, AUD/JPY, EUR/AUD, AUD/NZD. Таймфрейм: H1, Время: UTC+4. "
        "Покажи только те пары, где есть Triple Match (все 3 метода совпадают). "
        "Формат: без воды, чётко, пометки (Monthly/Weekly/Daily/Intraday), "
        "Buy/Sell и время разворота."
    )

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gtrader360")

def ask_openai(prompt: str) -> str:
    if OpenAI is None:
        log.error("OpenAI SDK not installed")
        return "Ошибка: OpenAI SDK не установлен."
    if not OPENAI_API_KEY:
        log.error("OPENAI_API_KEY is missing")
        return "Ошибка: отсутствует OPENAI_API_KEY."

    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Отвечай только чистым текстом, без упоминаний ChatGPT/GPT, "
                        "без вводных и заключительных фраз, без дисклеймеров. "
                        "Структурируй по делу, без воды."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        text = resp.choices[0].message.content or ""
        # Доп. зачистка возможных упоминаний
        for bad in ["ChatGPT", "chatgpt", "GPT", "gpt"]:
            text = text.replace(bad, "")
        return text.strip() or "Пустой ответ от модели."
    except Exception as e:
        log.exception("OpenAI error")
        return f"Ошибка при обращении к OpenAI: {e}"

async def job_send_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    log.info("Generating daily report via OpenAI...")
    text = ask_openai(STATIC_PROMPT)
    try:
        await context.bot.send_message(
            chat_id=TELEGRAM_CHANNEL,
            text=text,
            disable_web_page_preview=True,
        )
        log.info("Report posted to %s", TELEGRAM_CHANNEL)
    except Exception:
        log.exception("Failed to post to Telegram")

async def on_startup(app: Application) -> None:
    tz = ZoneInfo(SCHEDULE_TZ)
    run_time = time(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE, tzinfo=tz)
    # Требует зависимость python-telegram-bot[job-queue]
    app.job_queue.run_daily(job_send_report, run_time, name="daily_gtrader360")
    log.info("Job scheduled daily at %02d:%02d (%s)", SCHEDULE_HOUR, SCHEDULE_MINUTE, SCHEDULE_TZ)

def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL:
        raise SystemExit("TELEGRAM_BOT_TOKEN или TELEGRAM_CHANNEL не заданы")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.post_init = on_startup
    application.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
