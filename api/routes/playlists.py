"""Роуты для плейлистов"""

from typing import Set
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.deps import get_db, get_user_id
from api.schemas import (
    PlaylistCreate, 
    PlaylistUpdate, 
    PlaylistResponse, 
    PlaylistWithTracksResponse,
    PlaylistListResponse,
    AddToPlaylistRequest,
    ReorderTracksRequest,
    AudioResponse
)
from api.routes.audio import get_thumbnail_url
from db.audio_commands import (
    create_playlist,
    get_user_playlists,
    get_playlist_by_id,
    update_playlist,
    delete_playlist,
    add_track_to_playlist,
    remove_track_from_playlist,
    reorder_playlist_tracks,
    get_audio_by_id,
    is_audio_favorite
)
from models import Favorite


async def get_favorite_audio_ids(db: AsyncSession, user_id: int) -> Set[int]:
    """Получить множество ID избранных аудио пользователя"""
    result = await db.execute(
        select(Favorite.audio_id).where(Favorite.user_id == user_id)
    )
    return set(result.scalars().all())


router = APIRouter(prefix="/playlists", tags=["Playlists"])


@router.get("", response_model=PlaylistListResponse)
async def list_playlists(
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Получить все плейлисты пользователя"""
    playlists = await get_user_playlists(db, user_id)
    
    return PlaylistListResponse(
        items=[
            PlaylistResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                cover_file_id=p.cover_file_id,
                track_count=len(p.tracks) if p.tracks else 0,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in playlists
        ]
    )


@router.post("", response_model=PlaylistResponse)
async def create_new_playlist(
    data: PlaylistCreate,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Создать новый плейлист"""
    playlist = await create_playlist(db, user_id, data.name, data.description)
    
    if not playlist:
        raise HTTPException(status_code=500, detail="Failed to create playlist")
    
    return PlaylistResponse(
        id=playlist.id,
        name=playlist.name,
        description=playlist.description,
        track_count=0,
        created_at=playlist.created_at,
        updated_at=playlist.updated_at
    )


@router.get("/{playlist_id}", response_model=PlaylistWithTracksResponse)
async def get_playlist(
    playlist_id: int,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Получить плейлист с треками"""
    playlist = await get_playlist_by_id(db, playlist_id)
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    if playlist.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Получаем все избранные ID одним запросом
    favorite_ids = await get_favorite_audio_ids(db, user_id)
    
    tracks = [
        AudioResponse(
            id=pt.audio.id,
            file_id=pt.audio.file_id,
            title=pt.audio.title,
            artist=pt.audio.artist,
            duration=pt.audio.duration,
            source=pt.audio.source,
            source_url=pt.audio.source_url,
            created_at=pt.audio.created_at,
            is_favorite=pt.audio.id in favorite_ids,
            thumbnail_url=get_thumbnail_url(pt.audio.source, pt.audio.source_url)
        )
        for pt in playlist.tracks if pt.audio
    ]
    
    return PlaylistWithTracksResponse(
        id=playlist.id,
        name=playlist.name,
        description=playlist.description,
        cover_file_id=playlist.cover_file_id,
        track_count=len(tracks),
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
        tracks=tracks
    )


@router.patch("/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist_info(
    playlist_id: int,
    data: PlaylistUpdate,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Обновить плейлист"""
    playlist = await get_playlist_by_id(db, playlist_id)
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    if playlist.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    success = await update_playlist(db, playlist_id, data.name, data.description)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update playlist")
    
    # Получаем обновленный плейлист
    playlist = await get_playlist_by_id(db, playlist_id)
    
    return PlaylistResponse(
        id=playlist.id,
        name=playlist.name,
        description=playlist.description,
        cover_file_id=playlist.cover_file_id,
        track_count=len(playlist.tracks) if playlist.tracks else 0,
        created_at=playlist.created_at,
        updated_at=playlist.updated_at
    )


@router.delete("/{playlist_id}")
async def delete_playlist_endpoint(
    playlist_id: int,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Удалить плейлист"""
    playlist = await get_playlist_by_id(db, playlist_id)
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    if playlist.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    success = await delete_playlist(db, playlist_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete playlist")
    
    return {"success": True}


@router.post("/{playlist_id}/tracks")
async def add_track(
    playlist_id: int,
    data: AddToPlaylistRequest,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Добавить трек в плейлист"""
    playlist = await get_playlist_by_id(db, playlist_id)
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    if playlist.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Проверяем, что аудио принадлежит пользователю
    audio = await get_audio_by_id(db, data.audio_id)
    if not audio or audio.user_id != user_id:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    track = await add_track_to_playlist(db, playlist_id, data.audio_id)
    
    if not track:
        raise HTTPException(status_code=400, detail="Track already in playlist or error occurred")
    
    return {"success": True, "position": track.position}


@router.delete("/{playlist_id}/tracks/{audio_id}")
async def remove_track(
    playlist_id: int,
    audio_id: int,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Удалить трек из плейлиста"""
    playlist = await get_playlist_by_id(db, playlist_id)
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    if playlist.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    success = await remove_track_from_playlist(db, playlist_id, audio_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to remove track")
    
    return {"success": True}


@router.put("/{playlist_id}/reorder")
async def reorder_tracks(
    playlist_id: int,
    data: ReorderTracksRequest,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Переупорядочить треки в плейлисте"""
    playlist = await get_playlist_by_id(db, playlist_id)
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    if playlist.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    success = await reorder_playlist_tracks(db, playlist_id, data.audio_ids)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reorder tracks")
    
    return {"success": True}

