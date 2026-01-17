"""Команды для работы с аудио, плейлистами и избранным"""

from typing import Optional, List
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from models import UserAudio, Playlist, PlaylistTrack, Favorite


# ==================== UserAudio ====================

async def save_audio(
    session: AsyncSession,
    user_id: int,
    file_id: str,
    file_unique_id: Optional[str] = None,
    title: Optional[str] = None,
    artist: Optional[str] = None,
    duration: Optional[int] = None,
    message_id: Optional[int] = None,
    source: Optional[str] = None,
    source_url: Optional[str] = None,
    thumbnail_file_id: Optional[str] = None
) -> Optional[UserAudio]:
    """Сохранить аудио файл в БД"""
    audio = UserAudio(
        user_id=user_id,
        file_id=file_id,
        file_unique_id=file_unique_id,
        title=title,
        artist=artist,
        duration=duration,
        message_id=message_id,
        source=source,
        source_url=source_url,
        thumbnail_file_id=thumbnail_file_id
    )
    session.add(audio)
    try:
        await session.commit()
        await session.refresh(audio)
        return audio
    except IntegrityError:
        await session.rollback()
        return None


async def get_user_audio_list(
    session: AsyncSession,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None
) -> List[UserAudio]:
    """Получить список аудио пользователя с пагинацией и поиском"""
    query = select(UserAudio).where(UserAudio.user_id == user_id)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (UserAudio.title.ilike(search_pattern)) | 
            (UserAudio.artist.ilike(search_pattern))
        )
    
    query = query.order_by(UserAudio.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


async def get_audio_by_id(session: AsyncSession, audio_id: int) -> Optional[UserAudio]:
    """Получить аудио по ID"""
    result = await session.execute(select(UserAudio).where(UserAudio.id == audio_id))
    return result.scalars().first()


async def get_audio_by_file_id(session: AsyncSession, file_id: str) -> Optional[UserAudio]:
    """Получить аудио по file_id"""
    result = await session.execute(select(UserAudio).where(UserAudio.file_id == file_id))
    return result.scalars().first()


async def delete_audio(session: AsyncSession, audio_id: int) -> bool:
    """Удалить аудио (каскадно удалит из плейлистов и избранного)"""
    try:
        await session.execute(delete(UserAudio).where(UserAudio.id == audio_id))
        await session.commit()
        return True
    except Exception:
        await session.rollback()
        return False


async def count_user_audio(session: AsyncSession, user_id: int) -> int:
    """Количество аудио пользователя"""
    result = await session.execute(
        select(func.count(UserAudio.id)).where(UserAudio.user_id == user_id)
    )
    return result.scalar() or 0


# ==================== Playlists ====================

async def create_playlist(
    session: AsyncSession,
    user_id: int,
    name: str,
    description: Optional[str] = None
) -> Optional[Playlist]:
    """Создать плейлист"""
    playlist = Playlist(
        user_id=user_id,
        name=name,
        description=description
    )
    session.add(playlist)
    try:
        await session.commit()
        await session.refresh(playlist)
        return playlist
    except IntegrityError:
        await session.rollback()
        return None


async def get_user_playlists(session: AsyncSession, user_id: int) -> List[Playlist]:
    """Получить все плейлисты пользователя"""
    result = await session.execute(
        select(Playlist)
        .where(Playlist.user_id == user_id)
        .options(selectinload(Playlist.tracks))
        .order_by(Playlist.updated_at.desc())
    )
    return result.scalars().all()


async def get_playlist_by_id(session: AsyncSession, playlist_id: int) -> Optional[Playlist]:
    """Получить плейлист по ID с треками"""
    result = await session.execute(
        select(Playlist)
        .where(Playlist.id == playlist_id)
        .options(
            selectinload(Playlist.tracks).selectinload(PlaylistTrack.audio)
        )
    )
    return result.scalars().first()


async def update_playlist(
    session: AsyncSession,
    playlist_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None
) -> bool:
    """Обновить плейлист"""
    playlist = await get_playlist_by_id(session, playlist_id)
    if not playlist:
        return False
    
    if name is not None:
        playlist.name = name
    if description is not None:
        playlist.description = description
    
    try:
        await session.commit()
        return True
    except Exception:
        await session.rollback()
        return False


async def delete_playlist(session: AsyncSession, playlist_id: int) -> bool:
    """Удалить плейлист"""
    try:
        await session.execute(delete(Playlist).where(Playlist.id == playlist_id))
        await session.commit()
        return True
    except Exception:
        await session.rollback()
        return False


async def add_track_to_playlist(
    session: AsyncSession,
    playlist_id: int,
    audio_id: int
) -> Optional[PlaylistTrack]:
    """Добавить трек в плейлист"""
    # Проверяем, не добавлен ли уже этот трек
    existing = await session.execute(
        select(PlaylistTrack)
        .where(PlaylistTrack.playlist_id == playlist_id)
        .where(PlaylistTrack.audio_id == audio_id)
    )
    if existing.scalars().first():
        return None  # Трек уже в плейлисте
    
    # Получаем текущую максимальную позицию
    result = await session.execute(
        select(func.max(PlaylistTrack.position))
        .where(PlaylistTrack.playlist_id == playlist_id)
    )
    max_position = result.scalar() or 0
    
    track = PlaylistTrack(
        playlist_id=playlist_id,
        audio_id=audio_id,
        position=max_position + 1
    )
    session.add(track)
    try:
        await session.commit()
        await session.refresh(track)
        return track
    except IntegrityError:
        await session.rollback()
        return None


async def remove_track_from_playlist(
    session: AsyncSession,
    playlist_id: int,
    audio_id: int
) -> bool:
    """Удалить трек из плейлиста"""
    try:
        await session.execute(
            delete(PlaylistTrack)
            .where(PlaylistTrack.playlist_id == playlist_id)
            .where(PlaylistTrack.audio_id == audio_id)
        )
        await session.commit()
        return True
    except Exception:
        await session.rollback()
        return False


async def reorder_playlist_tracks(
    session: AsyncSession,
    playlist_id: int,
    audio_ids: List[int]
) -> bool:
    """Переупорядочить треки в плейлисте"""
    from sqlalchemy import update
    try:
        for position, audio_id in enumerate(audio_ids, start=1):
            await session.execute(
                update(PlaylistTrack)
                .where(PlaylistTrack.playlist_id == playlist_id)
                .where(PlaylistTrack.audio_id == audio_id)
                .values(position=position)
            )
        await session.commit()
        return True
    except Exception:
        await session.rollback()
        return False


# ==================== Favorites ====================

async def add_to_favorites(session: AsyncSession, user_id: int, audio_id: int) -> Optional[Favorite]:
    """Добавить в избранное"""
    # Проверяем, не добавлено ли уже
    existing = await session.execute(
        select(Favorite)
        .where(Favorite.user_id == user_id)
        .where(Favorite.audio_id == audio_id)
    )
    if existing.scalars().first():
        return None  # Уже в избранном
    
    favorite = Favorite(user_id=user_id, audio_id=audio_id)
    session.add(favorite)
    try:
        await session.commit()
        await session.refresh(favorite)
        return favorite
    except IntegrityError:
        await session.rollback()
        return None


async def remove_from_favorites(session: AsyncSession, user_id: int, audio_id: int) -> bool:
    """Удалить из избранного"""
    try:
        await session.execute(
            delete(Favorite)
            .where(Favorite.user_id == user_id)
            .where(Favorite.audio_id == audio_id)
        )
        await session.commit()
        return True
    except Exception:
        await session.rollback()
        return False


async def get_user_favorites(
    session: AsyncSession,
    user_id: int,
    limit: int = 50,
    offset: int = 0
) -> List[Favorite]:
    """Получить избранное пользователя"""
    result = await session.execute(
        select(Favorite)
        .where(Favorite.user_id == user_id)
        .options(selectinload(Favorite.audio))
        .order_by(Favorite.added_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


async def is_audio_favorite(session: AsyncSession, user_id: int, audio_id: int) -> bool:
    """Проверить, в избранном ли аудио"""
    result = await session.execute(
        select(Favorite.id)
        .where(Favorite.user_id == user_id)
        .where(Favorite.audio_id == audio_id)
    )
    return result.scalar() is not None


async def count_user_favorites(session: AsyncSession, user_id: int) -> int:
    """Количество избранных треков"""
    result = await session.execute(
        select(func.count(Favorite.id)).where(Favorite.user_id == user_id)
    )
    return result.scalar() or 0

