"""Pydantic схемы для API"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== Audio ====================

class AudioBase(BaseModel):
    title: Optional[str] = None
    artist: Optional[str] = None
    duration: Optional[int] = None
    source: Optional[str] = None


class AudioResponse(AudioBase):
    id: int
    file_id: str
    created_at: Optional[datetime] = None
    is_favorite: bool = False
    
    class Config:
        from_attributes = True


class AudioListResponse(BaseModel):
    items: List[AudioResponse]
    total: int
    limit: int
    offset: int


class AudioStreamUrlResponse(BaseModel):
    """
    Временный URL для стриминга аудио.
    
    ⚠️ URL действителен примерно 1 час!
    После истечения нужно запросить новый через /refresh-url
    """
    url: str  # Временный URL для скачивания/стриминга
    expires_in: int = 3600  # Время жизни URL в секундах (~1 час)
    file_id: str  # Telegram file_id для использования с ботом
    audio_id: int
    title: Optional[str] = None
    artist: Optional[str] = None
    duration: Optional[int] = None


# ==================== Playlists ====================

class PlaylistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)


class PlaylistUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)


class PlaylistResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    cover_file_id: Optional[str] = None
    track_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PlaylistWithTracksResponse(PlaylistResponse):
    tracks: List[AudioResponse] = []


class PlaylistListResponse(BaseModel):
    items: List[PlaylistResponse]


# ==================== Favorites ====================

class FavoriteResponse(BaseModel):
    id: int
    audio: AudioResponse
    added_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class FavoriteListResponse(BaseModel):
    items: List[FavoriteResponse]
    total: int


# ==================== Actions ====================

class AddToPlaylistRequest(BaseModel):
    audio_id: int


class ReorderTracksRequest(BaseModel):
    audio_ids: List[int]


class ToggleFavoriteRequest(BaseModel):
    audio_id: int


class ToggleFavoriteResponse(BaseModel):
    is_favorite: bool
    audio_id: int


# ==================== Stats ====================

class UserStatsResponse(BaseModel):
    total_tracks: int
    total_playlists: int
    total_favorites: int

