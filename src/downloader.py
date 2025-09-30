import os
from pathlib import Path
from typing import Tuple

import yt_dlp


DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "/downloads")).resolve()
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

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


def download_video(url: str) -> Tuple[Path, str]:
    ydl_opts = {
        "outtmpl": str(DOWNLOAD_DIR / "%(title).200B-%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        # Предпочитаем mp4, если доступно
        "format": (
            "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"
        ),
        # Иногда нужен ffmpeg для объединения дорожек
        "merge_output_format": "mp4",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # Если это плейлист или информация содержит entries
        if info is None:
            raise RuntimeError("Не удалось получить информацию о видео")
        if "entries" in info:
            # берем первый элемент
            info = info["entries"][0]
        out_path = Path(ydl.prepare_filename(info)).with_suffix(".mp4")
        title = info.get("title") or "Видео"

    if not out_path.exists():
        # если не mp4, используем оригинальное имя
        original = Path(ydl_opts["outtmpl"]).parent
        # fallback: найти файл по id
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
