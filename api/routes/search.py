"""Поиск по библиотеке + YouTube и импорт трека в библиотеку (Mini App)."""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_user_id
from api.routes.audio import get_cover_url_for_audio, get_favorite_audio_ids
from api.schemas import AudioResponse, CombinedSearchResponse, YouTubeImportRequest, YouTubeSearchItem
from api.telegram_upload import send_audio_to_telegram_user
from db.audio_commands import (
    get_audio_by_file_id,
    get_audio_by_user_and_source_url,
    get_user_audio_list,
)
from db.audio_helper import save_audio_from_api_response
import worker

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Search"])


@router.get("/search", response_model=CombinedSearchResponse)
async def combined_search(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(50, ge=1, le=100),
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Треки из библиотеки + результаты поиска YouTube (музыка, до 10 мин)."""
    library_rows = await get_user_audio_list(db, user_id, limit, 0, q.strip())
    favorite_ids = await get_favorite_audio_ids(db, user_id)

    lib_items = [
        AudioResponse(
            id=a.id,
            file_id=a.file_id,
            title=a.title,
            artist=a.artist,
            duration=a.duration,
            source=a.source,
            source_url=a.source_url,
            created_at=a.created_at,
            is_favorite=a.id in favorite_ids,
            thumbnail_url=get_cover_url_for_audio(a),
        )
        for a in library_rows
    ]

    yt_raw = worker.search_youtube_music_candidates(
        q.strip(), max_results=20, max_duration_sec=600, fetch_cap=50
    )
    yt_items = [YouTubeSearchItem(**x) for x in yt_raw]

    return CombinedSearchResponse(library=lib_items, youtube=yt_items)


@router.post("/youtube/import", response_model=AudioResponse)
async def import_youtube_track(
    body: YouTubeImportRequest,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Скачивает аудио через worker (yt-dlp + ffmpeg), отправляет пользователю через Bot API,
    сохраняет трек в БД — отображается в Mini App.
    """
    link = f"https://www.youtube.com/watch?v={body.video_id}"

    existing = await get_audio_by_user_and_source_url(db, user_id, link)
    if existing:
        favorite_ids = await get_favorite_audio_ids(db, user_id)
        return AudioResponse(
            id=existing.id,
            file_id=existing.file_id,
            title=existing.title,
            artist=existing.artist,
            duration=existing.duration,
            source=existing.source,
            source_url=existing.source_url,
            created_at=existing.created_at,
            is_favorite=existing.id in favorite_ids,
            thumbnail_url=get_cover_url_for_audio(existing),
        )

    try:
        result = await worker.get_audio_from_youtube(link)
    except Exception as e:
        logger.exception("get_audio_from_youtube: %s", e)
        raise HTTPException(status_code=502, detail="Не удалось скачать аудио с YouTube") from e

    if not result:
        raise HTTPException(status_code=502, detail="Видео недоступно или ошибка загрузки")

    filename = result["audio"]
    thumb_path = result.get("thumbnail")
    audio_full_path = f"./audio/youtube/{filename}"

    if not os.path.isfile(audio_full_path):
        raise HTTPException(status_code=502, detail="Файл аудио не найден после загрузки")

    title = os.path.splitext(filename)[0].replace("_", " ")
    performer: Optional[str] = None
    try:
        info = worker.get_youtube_video_info(link)
        if info:
            title = info.get("title") or title
            performer = info.get("channel")
    except Exception:
        pass

    try:
        tg_resp = await send_audio_to_telegram_user(
            chat_id=user_id,
            audio_path=audio_full_path,
            thumbnail_path=thumb_path if thumb_path and os.path.isfile(thumb_path) else None,
            title=title,
            performer=performer or "",
        )
    finally:
        try:
            if os.path.isfile(audio_full_path):
                os.remove(audio_full_path)
            if thumb_path and os.path.isfile(thumb_path):
                os.remove(thumb_path)
        except OSError as e:
            logger.warning("cleanup temp audio: %s", e)

    if not tg_resp.get("ok"):
        err = tg_resp.get("description", "Telegram error")
        logger.error("sendAudio failed: %s", tg_resp)
        raise HTTPException(status_code=502, detail=str(err))

    saved_ok = await save_audio_from_api_response(
        db, user_id, tg_resp, source="youtube", source_url=link
    )
    if not saved_ok:
        raise HTTPException(status_code=500, detail="Не удалось сохранить трек в библиотеке")

    file_id = (tg_resp.get("result") or {}).get("audio", {}).get("file_id")
    if not file_id:
        raise HTTPException(status_code=500, detail="Нет file_id в ответе Telegram")

    audio_row = await get_audio_by_file_id(db, file_id)
    if not audio_row:
        raise HTTPException(status_code=500, detail="Трек не найден в БД после сохранения")

    favorite_ids = await get_favorite_audio_ids(db, user_id)
    return AudioResponse(
        id=audio_row.id,
        file_id=audio_row.file_id,
        title=audio_row.title,
        artist=audio_row.artist,
        duration=audio_row.duration,
        source=audio_row.source,
        source_url=audio_row.source_url,
        created_at=audio_row.created_at,
        is_favorite=audio_row.id in favorite_ids,
        thumbnail_url=get_cover_url_for_audio(audio_row),
    )
