import os
import logging
from datetime import time
from zoneinfo import ZoneInfo
from telegram.ext import Application, ContextTypes

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# === ENV ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FOREX_CHANNEL      = os.getenv("FOREX_CHANNEL", os.getenv("TELEGRAM_CHANNEL"))  # совместимость
CRYPTO_CHANNEL     = os.getenv("CRYPTO_CHANNEL", FOREX_CHANNEL)

OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL       = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SCHEDULE_TZ        = os.getenv("SCHEDULE_TZ", "Asia/Jerusalem")

# Время постинга (по таймзоне SCHEDULE_TZ)
FOREX_HOUR         = int(os.getenv("FOREX_HOUR", "9"))
FOREX_MINUTE       = int(os.getenv("FOREX_MINUTE", "0"))
CRYPTO_HOUR        = int(os.getenv("CRYPTO_HOUR", "9"))
CRYPTO_MINUTE      = int(os.getenv("CRYPTO_MINUTE", "5"))

# Промпты
FOREX_PROMPT = os.getenv("FOREX_STATIC_PROMPT", "").strip()
CRYPTO_PROMPT = os.getenv("CRYPTO_STATIC_PROMPT", "").strip()

# Дефолтные тексты (если переменные не заданы)
if not FOREX_PROMPT:
    FOREX_PROMPT = (
        "Сделай анализ по методу Ганна (симметрия времени, углы Ганна, Square of 9) "
        "для следующих пар: USD/CAD, EUR/JPY, EUR/USD, EUR/CHF, USD/CHF, EUR/GBP, "
        "GBP/USD, AUD/CAD, NZD/USD, GBP/CHF, AUD/USD, GBP/JPY, USD/JPY, CHF/JPY, "
        "EUR/CAD, AUD/JPY, EUR/AUD, AUD/NZD. Таймфрейм: H1, Время: UTC+4. "
        "Покажи только те пары, где есть Triple Match (все 3 метода совпадают). "
        "Формат: без воды, чётко, пометки (Monthly/Weekly/Daily/Intraday), Buy/Sell и время разворота. "
        "Никаких упоминаний ChatGPT или источников, только результат."
    )

if not CRYPTO_PROMPT:
    CRYPTO_PROMPT = (
        "Сделай анализ по методу Ганна (симметрия времени, углы Ганна, Square of 9) "
        "для следующих монет: AVAXUSDT, SOLUSDT, AAVEUSDT, PENGUUSDT, SEIUSDT, ARBUSDT, FETUSDT, "
        "TRXUSDT, BTCUSDT, ETHUSDT, XRPUSDT, ADAUSDT, LINKUSDT, SUIUSDT, DOGEUSDT, PEPEUSDT, "
        "NEARUSDT, BNBUSDT, DOTUSDT. Таймфрейм: H1, Время: UTC+4. "
        "Покажи только те монеты, где есть Triple Match (все 3 метода совпадают). "
        "Формат: без воды, чётко, пометки (Monthly/Weekly/Daily/Intraday), Buy/Sell и время разворота. "
        "Никаких упоминаний ChatGPT или источников, только результат."
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
        text = (resp.choices[0].message.content or "").strip()
        for bad in ["ChatGPT", "chatgpt", "GPT", "gpt"]:
            text = text.replace(bad, "")
        return text.strip() or "Пустой ответ от модели."
    except Exception as e:
        log.exception("OpenAI error")
        return f"Ошибка при обращении к OpenAI: {e}"

async def post_text(context: ContextTypes.DEFAULT_TYPE, channel: str, prompt: str, tag: str):
    log.info("Generating %s via OpenAI...", tag)
    text = ask_openai(prompt)
    try:
        await context.bot.send_message(chat_id=channel, text=text, disable_web_page_preview=True)
        log.info("%s posted to %s", tag, channel)
    except Exception:
        log.exception("Failed to post %s to Telegram", tag)

async def job_forex(context: ContextTypes.DEFAULT_TYPE):
    await post_text(context, FOREX_CHANNEL, FOREX_PROMPT, "FOREX")

async def job_crypto(context: ContextTypes.DEFAULT_TYPE):
    await post_text(context, CRYPTO_CHANNEL, CRYPTO_PROMPT, "CRYPTO")

async def on_startup(app: Application) -> None:
    tz = ZoneInfo(SCHEDULE_TZ)
    forex_time = time(hour=FOREX_HOUR, minute=FOREX_MINUTE, tzinfo=tz)
    crypto_time = time(hour=CRYPTO_HOUR, minute=CRYPTO_MINUTE, tzinfo=tz)

    # Требуется python-telegram-bot[job-queue]
    app.job_queue.run_daily(job_forex,  forex_time, name="daily_forex")
    app.job_queue.run_daily(job_crypto, crypto_time, name="daily_crypto")

    log.info("Jobs scheduled: FOREX %02d:%02d, CRYPTO %02d:%02d (%s)",
             FOREX_HOUR, FOREX_MINUTE, CRYPTO_HOUR, CRYPTO_MINUTE, SCHEDULE_TZ)

def main():
    if not TELEGRAM_BOT_TOKEN or not FOREX_CHANNEL:
        raise SystemExit("TELEGRAM_BOT_TOKEN или FOREX_CHANNEL/TELEGRAM_CHANNEL не заданы")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.post_init = on_startup
    application.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
