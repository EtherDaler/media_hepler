"""Роуты для аудио"""

import httpx
from typing import Optional, Set
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.deps import get_db, get_user_id
from api.schemas import AudioListResponse, AudioResponse, AudioStreamUrlResponse
from db.audio_commands import (
    get_user_audio_list, 
    get_audio_by_id, 
    delete_audio, 
    count_user_audio,
    is_audio_favorite
)
from models import Favorite
from data.config import BOT_TOKEN


router = APIRouter(prefix="/audio", tags=["Audio"])

# Telegram Bot API base URL
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
TELEGRAM_FILE_URL = f"https://api.telegram.org/file/bot{BOT_TOKEN}"


async def get_favorite_audio_ids(db: AsyncSession, user_id: int) -> Set[int]:
    """Получить множество ID избранных аудио пользователя (один запрос)"""
    result = await db.execute(
        select(Favorite.audio_id).where(Favorite.user_id == user_id)
    )
    return set(result.scalars().all())


@router.get("", response_model=AudioListResponse)
async def list_audio(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Получить список аудио пользователя"""
    audio_list = await get_user_audio_list(db, user_id, limit, offset, search)
    total = await count_user_audio(db, user_id)
    
    # Получаем все избранные ID одним запросом
    favorite_ids = await get_favorite_audio_ids(db, user_id)
    
    items = [
        AudioResponse(
            id=audio.id,
            file_id=audio.file_id,
            title=audio.title,
            artist=audio.artist,
            duration=audio.duration,
            source=audio.source,
            created_at=audio.created_at,
            is_favorite=audio.id in favorite_ids
        )
        for audio in audio_list
    ]
    
    return AudioListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{audio_id}", response_model=AudioResponse)
async def get_audio(
    audio_id: int,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Получить аудио по ID"""
    audio = await get_audio_by_id(db, audio_id)
    
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    if audio.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    is_fav = await is_audio_favorite(db, user_id, audio.id)
    
    return AudioResponse(
        id=audio.id,
        file_id=audio.file_id,
        title=audio.title,
        artist=audio.artist,
        duration=audio.duration,
        source=audio.source,
        created_at=audio.created_at,
        is_favorite=is_fav
    )


@router.delete("/{audio_id}")
async def remove_audio(
    audio_id: int,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Удалить аудио"""
    audio = await get_audio_by_id(db, audio_id)
    
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    if audio.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    success = await delete_audio(db, audio_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete audio")
    
    return {"success": True}


@router.get("/{audio_id}/stream-url", response_model=AudioStreamUrlResponse)
async def get_stream_url(
    audio_id: int,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить временный URL для стриминга аудио.
    
    ⚠️ **URL действителен ~1 час!**
    
    ## Гибридный плеер:
    
    - **Свой плеер**: используйте `url` для воспроизведения через `<audio>` элемент
    - **Telegram плеер**: используйте `file_id` для пересылки аудио через бота
    
    ## Обработка истекших URL:
    
    При ошибке воспроизведения (403/404) вызовите `/refresh-url` для получения нового URL.
    """
    audio = await get_audio_by_id(db, audio_id)
    
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    if audio.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Получаем file_path через Telegram Bot API
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TELEGRAM_API_URL}/getFile",
                params={"file_id": audio.file_id},
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=502, 
                    detail="Failed to get file from Telegram"
                )
            
            data = response.json()
            
            if not data.get("ok"):
                raise HTTPException(
                    status_code=502, 
                    detail=f"Telegram API error: {data.get('description', 'Unknown error')}"
                )
            
            file_path = data["result"]["file_path"]
            stream_url = f"{TELEGRAM_FILE_URL}/{file_path}"
            
            return AudioStreamUrlResponse(
                url=stream_url,
                expires_in=3600,  # ~1 час
                file_id=audio.file_id,
                audio_id=audio.id,
                title=audio.title,
                artist=audio.artist,
                duration=audio.duration
            )
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502, 
            detail=f"Failed to connect to Telegram API: {str(e)}"
        )


@router.post("/{audio_id}/refresh-url", response_model=AudioStreamUrlResponse)
async def refresh_stream_url(
    audio_id: int,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновить URL для стриминга (если предыдущий истёк).
    
    То же самое что и GET /stream-url, но POST для удобства фронтенда
    при обработке истекших URL.
    """
    return await get_stream_url(audio_id, user_id, db)

