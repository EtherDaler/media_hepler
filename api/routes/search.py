"""Поиск по библиотеке + YouTube и импорт трека в библиотеку (Mini App)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_user_id
from api.routes.audio import get_cover_url_for_audio, get_favorite_audio_ids
from api.schemas import AudioResponse, CombinedSearchResponse, YouTubeSearchItem
from db.audio_commands import get_user_audio_list
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


@router.post("/youtube/import")
async def import_youtube_track_deprecated():
    """
    Импорт через API отключён: загрузка выполняется в чате с ботом (тот же worker, без ffmpeg в uvicorn).
    В Mini App нажмите «+» — откроется deep link, бот скачает трек и сохранит в библиотеку.
    """
    raise HTTPException(
        status_code=410,
        detail="Используйте кнопку «+» в поиске Mini App — откроется чат с ботом для загрузки.",
    )
