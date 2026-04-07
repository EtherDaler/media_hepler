"""Отправка аудио пользователю через Telegram Bot API (для импорта из Mini App)."""

import asyncio
import logging
import os
from typing import Any, Dict, Optional

import requests

from data.config import BOT_TOKEN, DEV_CHANEL_ID, LOCAL_BOT_API_URL

logger = logging.getLogger(__name__)


def _telegram_send_message_sync(chat_id, text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(
        url,
        json={"chat_id": chat_id, "text": text[:4096]},
        timeout=30,
    )
    data = r.json()
    if not data.get("ok"):
        logger.warning("sendMessage failed: %s", data)


async def notify_dev_channel(text: str) -> None:
    """Служебное сообщение в DEV_CHANEL_ID (как уведомления из бота)."""
    if not DEV_CHANEL_ID:
        return
    try:
        cid = int(str(DEV_CHANEL_ID).strip())
    except (TypeError, ValueError):
        logger.warning("notify_dev_channel: invalid DEV_CHANEL_ID=%r", DEV_CHANEL_ID)
        return
    try:
        await asyncio.to_thread(_telegram_send_message_sync, cid, text)
    except Exception as e:
        logger.warning("notify_dev_channel: %s", e)


def _telegram_send_audio_sync(
    api_base: str,
    chat_id: int,
    audio_path: str,
    thumbnail_path: Optional[str],
    title: str,
    performer: str,
) -> Dict[str, Any]:
    url = f"{api_base}/bot{BOT_TOKEN}/sendAudio"
    data: Dict[str, Any] = {"chat_id": chat_id}
    if title:
        data["title"] = title[:200]
    if performer:
        data["performer"] = performer[:200]

    audio_f = open(audio_path, "rb")
    files: Dict[str, Any] = {"audio": audio_f}
    thumb_f = None
    try:
        if thumbnail_path and os.path.isfile(thumbnail_path):
            thumb_f = open(thumbnail_path, "rb")
            files["thumbnail"] = thumb_f
        r = requests.post(url, data=data, files=files, timeout=(30, 600))
        return r.json()
    finally:
        audio_f.close()
        if thumb_f:
            thumb_f.close()


async def send_audio_to_telegram_user(
    chat_id: int,
    audio_path: str,
    thumbnail_path: Optional[str],
    title: str,
    performer: str,
) -> Dict[str, Any]:
    """
    Отправляет аудио в чат пользователя. Сначала облачный api.telegram.org,
    при большом файле — повтор через LOCAL_BOT_API_URL (если задан).
    """
    bases = ["https://api.telegram.org"]
    if LOCAL_BOT_API_URL:
        bases.append(LOCAL_BOT_API_URL)

    last: Dict[str, Any] = {}
    for base in bases:
        last = await asyncio.to_thread(
            _telegram_send_audio_sync,
            base,
            chat_id,
            audio_path,
            thumbnail_path,
            title,
            performer,
        )
        if last.get("ok"):
            return last

        desc = str(last.get("description", "")).lower()
        if "too large" in desc or "too big" in desc or "request entity too large" in desc:
            logger.warning("Audio too large for %s, trying next Bot API base…", base)
            continue
        break

    return last
