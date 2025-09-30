import logging
import os
import re
import asyncio
from contextlib import suppress
from pathlib import Path

from telegram import Update
from telegram.constants import ChatType
from telegram.error import BadRequest, TimedOut, NetworkError
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest

from .downloader import download_video, cleanup_file, is_supported_url


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("tg_video_bot")


URL_REGEX = re.compile(r"https?://[^\s]+", re.IGNORECASE)

# Таймауты и ретраи отправки в Telegram
TG_CONNECT_TIMEOUT = float(os.getenv("TELEGRAM_CONNECT_TIMEOUT", "10"))
TG_READ_TIMEOUT = float(os.getenv("TELEGRAM_READ_TIMEOUT", "60"))
TG_WRITE_TIMEOUT = float(os.getenv("TELEGRAM_WRITE_TIMEOUT", "60"))
TG_POOL_TIMEOUT = float(os.getenv("TELEGRAM_POOL_TIMEOUT", "10"))
TG_SEND_RETRIES = int(os.getenv("TELEGRAM_SEND_RETRIES", "3"))
TG_SEND_BACKOFF_BASE = float(os.getenv("TELEGRAM_SEND_BACKOFF_BASE", "2"))


async def send_with_retries(callable_coro, *args, **kwargs):
    last_exc: Exception | None = None
    for attempt in range(1, TG_SEND_RETRIES + 1):
        try:
            return await callable_coro(*args, **kwargs)
        except NetworkError as e:
            last_exc = e
            if attempt < TG_SEND_RETRIES:
                await asyncio.sleep(min(TG_SEND_BACKOFF_BASE ** attempt, 20))
                continue
            raise
        except Exception as e:
            # Для прочих ошибок не крутим длинные ретраи
            last_exc = e
            if attempt < TG_SEND_RETRIES:
                await asyncio.sleep(1)
                continue
            raise


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.message.text is None:
        return

    text = update.message.text.strip()
    urls = URL_REGEX.findall(text)
    if not urls:
        return

    # Берем первую ссылку
    url = urls[0]
    if not is_supported_url(url):
        return

    chat = update.effective_chat
    message = update.message

    # В группах пробуем удалить исходное сообщение пользователя
    if chat and chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        with suppress(BadRequest, TimedOut):
            await message.delete()

    # Сообщаем, что скачиваем
    status_msg = None
    try:
        status_msg = await message.reply_text("Скачиваю видео... Это может занять немного времени ⏳")
    except Exception:
        pass

    file_path: Path | None = None
    title: str | None = None

    try:
        loop = asyncio.get_running_loop()
        file_path, title = await loop.run_in_executor(None, lambda: download_video(url))
        caption = title or "Видео"

        # Пытаемся отправить как видео с ретраями
        try:
            await send_with_retries(
                context.bot.send_video,
                chat_id=chat.id if chat else message.chat_id,
                video=file_path.open("rb"),
                caption=caption,
            )
        except BadRequest as e:
            logger.warning("Send video failed: %s", e)
            await send_with_retries(
                context.bot.send_message,
                chat_id=chat.id if chat else message.chat_id,
                text=(
                    "Не удалось отправить видео (возможно слишком большое). "
                    "Вот ссылка: " + url
                ),
            )
    except Exception as e:
        logger.exception("Download failed: %s", e)
        with suppress(Exception):
            await send_with_retries(
                context.bot.send_message,
                chat_id=chat.id if chat else message.chat_id,
                text="Не получилось скачать видео. Попробуйте другую ссылку.",
            )
    finally:
        if status_msg:
            with suppress(Exception):
                await status_msg.delete()
        if file_path:
            cleanup_file(file_path)


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

    request = HTTPXRequest(
        connect_timeout=TG_CONNECT_TIMEOUT,
        read_timeout=TG_READ_TIMEOUT,
        write_timeout=TG_WRITE_TIMEOUT,
        pool_timeout=TG_POOL_TIMEOUT,
        http_version="1.1",
    )

    app = ApplicationBuilder().token(token).request(request).build()

    # В ЛС и группах одинаковая логика: на любое текстовое сообщение проверяем URL
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Starting bot with polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
