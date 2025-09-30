import os
from pathlib import Path
from typing import Tuple

import yt_dlp


DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "/downloads")).resolve()
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Опциональный путь к cookies.txt (формат Netscape)
COOKIES_FILE = os.getenv("YTDLP_COOKIES", "").strip()
USER_AGENT = os.getenv(
    "YTDLP_UA",
    # Современный десктопный UA по умолчанию
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36",
)

SUPPORTED_DOMAINS = (
    "youtube.com",
    "youtu.be",
    "m.youtube.com",
    "instagram.com",
    "www.instagram.com",
)


def is_supported_url(url: str) -> bool:
    lower = url.lower()
    return any(domain in lower for domain in SUPPORTED_DOMAINS)


def _build_ydl_opts() -> dict:
    ydl_opts: dict = {
        "outtmpl": str(DOWNLOAD_DIR / "%(title).200B-%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        # Предпочитаем mp4, если доступно
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
        # Иногда нужен ffmpeg для объединения дорожек
        "merge_output_format": "mp4",
        # Заголовки запроса
        "http_headers": {
            "User-Agent": USER_AGENT,
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        },
        # Пытаемся использовать Android-клиент YouTube, чтобы обходить некоторые ограничения
        "extractor_args": {
            "youtube": {
                "player_client": ["android"],
            }
        },
    }

    if COOKIES_FILE:
        cookie_path = Path(COOKIES_FILE)
        if cookie_path.exists():
            ydl_opts["cookiefile"] = str(cookie_path)
        else:
            # Если путь задан, но файл не существует — игнорируем, не падаем
            pass
    return ydl_opts


def download_video(url: str) -> Tuple[Path, str]:
    ydl_opts = _build_ydl_opts()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info is None:
            raise RuntimeError("Не удалось получить информацию о видео")
        if "entries" in info:
            info = info["entries"][0]
        out_path = Path(ydl.prepare_filename(info)).with_suffix(".mp4")
        title = info.get("title") or "Видео"

    if not out_path.exists():
        original = Path(ydl_opts["outtmpl"]).parent
        vid_id = info.get("id")
        matches = list(original.glob(f"*{vid_id}.*"))
        if not matches:
            raise FileNotFoundError("Файл после загрузки не найден")
        out_path = matches[0]

    return out_path, title


def cleanup_file(path: Path) -> None:
    try:
        if path.exists():
            path.unlink(missing_ok=True)
    except Exception:
        pass
