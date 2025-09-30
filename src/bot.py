import asyncio
import logging
import os
import re
from contextlib import suppress
from pathlib import Path

from telegram import Update
from telegram.constants import ChatType
from telegram.error import BadRequest, TimedOut
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from .downloader import download_video, cleanup_file, is_supported_url


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("tg_video_bot")


URL_REGEX = re.compile(r"https?://[^\s]+", re.IGNORECASE)


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
        loop = asyncio.get_event_loop()
        file_path, title = await loop.run_in_executor(None, lambda: download_video(url))
        caption = title or "Видео"

        # Пытаемся отправить как видео
        try:
            await context.bot.send_video(
                chat_id=chat.id if chat else message.chat_id,
                video=file_path.open("rb"),
                caption=caption,
            )
        except BadRequest as e:
            # Если слишком большой файл или другое ограничение
            logger.warning("Send video failed: %s", e)
            await context.bot.send_message(
                chat_id=chat.id if chat else message.chat_id,
                text=(
                    "Не удалось отправить видео (возможно слишком большое). "
                    "Вот ссылка: " + url
                ),
            )
    except Exception as e:
        logger.exception("Download failed: %s", e)
        try:
            await context.bot.send_message(
                chat_id=chat.id if chat else message.chat_id,
                text="Не получилось скачать видео. Попробуйте другую ссылку.",
            )
        except Exception:
            pass
    finally:
        if status_msg:
            with suppress(Exception):
                await status_msg.delete()
        if file_path:
            cleanup_file(file_path)


async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

    app = ApplicationBuilder().token(token).build()

    # В ЛС и группах одинаковая логика: на любое текстовое сообщение проверяем URL
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Starting bot with polling...")
    await app.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False)


if __name__ == "__main__":
    try:
        import uvloop  # type: ignore

        uvloop.install()
    except Exception:
        pass
    asyncio.run(main())
