from __future__ import annotations
import os
import re
import asyncio
from typing import Optional, Tuple

from yt_dlp import YoutubeDL

YOUTUBE_REGEX = re.compile(r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/", re.IGNORECASE)
INSTAGRAM_REGEX = re.compile(r"(?:https?://)?(?:www\.)?instagram\.com/", re.IGNORECASE)

class DownloadError(Exception):
    pass


def detect_platform(url: str) -> str:
    if YOUTUBE_REGEX.search(url):
        return "youtube"
    if INSTAGRAM_REGEX.search(url):
        return "instagram"
    return "unknown"


def _build_ydl_opts(output_dir: str) -> dict:
    # Формируем безопасный темплейт имени файла: <title>.<ext>
    outtmpl = os.path.join(output_dir, "%(title).180s.%(ext)s")
    # Ограничиваем формат до лучшего видео <=720p с аудио, с fallbackом
