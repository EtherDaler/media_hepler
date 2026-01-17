"""Роуты для избранного"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_user_id
from api.schemas import (
    FavoriteListResponse, 
    FavoriteResponse,
    ToggleFavoriteRequest, 
    ToggleFavoriteResponse,
    AudioResponse
)
from db.audio_commands import (
    get_user_favorites,
    add_to_favorites,
    remove_from_favorites,
    is_audio_favorite,
    count_user_favorites,
    get_audio_by_id
)


router = APIRouter(prefix="/favorites", tags=["Favorites"])


@router.get("", response_model=FavoriteListResponse)
async def list_favorites(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Получить избранное пользователя"""
    favorites = await get_user_favorites(db, user_id, limit, offset)
    total = await count_user_favorites(db, user_id)
    
    items = []
    for fav in favorites:
        if fav.audio:
            items.append(FavoriteResponse(
                id=fav.id,
                audio=AudioResponse(
                    id=fav.audio.id,
                    file_id=fav.audio.file_id,
                    title=fav.audio.title,
                    artist=fav.audio.artist,
                    duration=fav.audio.duration,
                    source=fav.audio.source,
                    created_at=fav.audio.created_at,
                    is_favorite=True
                ),
                added_at=fav.added_at
            ))
    
    return FavoriteListResponse(items=items, total=total)


@router.post("/toggle", response_model=ToggleFavoriteResponse)
async def toggle_favorite(
    data: ToggleFavoriteRequest,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Добавить/удалить из избранного"""
    # Проверяем, что аудио существует и принадлежит пользователю
    audio = await get_audio_by_id(db, data.audio_id)
    if not audio or audio.user_id != user_id:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    is_fav = await is_audio_favorite(db, user_id, data.audio_id)
    
    if is_fav:
        # Удаляем из избранного
        await remove_from_favorites(db, user_id, data.audio_id)
        return ToggleFavoriteResponse(is_favorite=False, audio_id=data.audio_id)
    else:
        # Добавляем в избранное
        await add_to_favorites(db, user_id, data.audio_id)
        return ToggleFavoriteResponse(is_favorite=True, audio_id=data.audio_id)


@router.delete("/{audio_id}")
async def remove_favorite(
    audio_id: int,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Удалить из избранного"""
    success = await remove_from_favorites(db, user_id, audio_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to remove from favorites")
    
    return {"success": True}

