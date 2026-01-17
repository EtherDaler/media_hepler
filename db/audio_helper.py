"""Хелпер для сохранения аудио в БД после отправки"""

import logging
from typing import Optional
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from db.audio_commands import save_audio, get_audio_by_file_id


logger = logging.getLogger(__name__)


async def save_sent_audio(
    session: AsyncSession,
    message: Message,  # Сообщение с отправленным аудио
    source: Optional[str] = None,
    source_url: Optional[str] = None
):
    """
    Сохранить отправленное аудио в БД.
    
    Args:
        session: Сессия БД
        message: Сообщение, содержащее отправленное аудио (результат answer_audio)
        source: Источник (youtube, soundcloud, etc)
        source_url: Оригинальная ссылка
    
    Returns:
        UserAudio если сохранено успешно, None если уже существует или ошибка
    """
    try:
        if not message or not message.audio:
            logger.warning("Message doesn't contain audio")
            return None
        
        audio = message.audio
        user_id = message.chat.id
        
        # Проверяем, не сохранено ли уже
        existing = await get_audio_by_file_id(session, audio.file_id)
        if existing:
            logger.info(f"Audio already saved: {audio.file_id}")
            return None  # Возвращаем None чтобы обработчик знал, что уже существует
        
        # Извлекаем метаданные
        title = audio.title or audio.file_name or "Unknown"
        artist = audio.performer
        duration = audio.duration
        
        saved = await save_audio(
            session=session,
            user_id=user_id,
            file_id=audio.file_id,
            file_unique_id=audio.file_unique_id,
            title=title,
            artist=artist,
            duration=duration,
            message_id=message.message_id,
            source=source,
            source_url=source_url
        )
        
        if saved:
            logger.info(f"Audio saved: {title} by {artist} for user {user_id}")
            return saved
        else:
            logger.error(f"Failed to save audio for user {user_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error saving audio: {e}")
        return None


async def save_audio_from_api_response(
    session: AsyncSession,
    user_id: int,
    api_response: dict,
    source: Optional[str] = None,
    source_url: Optional[str] = None
) -> bool:
    """
    Сохранить аудио из ответа API (для send_audio_through_api).
    
    Args:
        session: Сессия БД
        user_id: ID пользователя Telegram
        api_response: Ответ API Telegram
        source: Источник
        source_url: Оригинальная ссылка
    
    Returns:
        True если сохранено успешно
    """
    try:
        result = api_response.get('result', {})
        audio_data = result.get('audio', {})
        
        if not audio_data:
            logger.warning("API response doesn't contain audio")
            return False
        
        file_id = audio_data.get('file_id')
        if not file_id:
            return False
        
        # Проверяем, не сохранено ли уже
        existing = await get_audio_by_file_id(session, file_id)
        if existing:
            logger.info(f"Audio already saved: {file_id}")
            return True
        
        saved = await save_audio(
            session=session,
            user_id=user_id,
            file_id=file_id,
            file_unique_id=audio_data.get('file_unique_id'),
            title=audio_data.get('title') or audio_data.get('file_name', 'Unknown'),
            artist=audio_data.get('performer'),
            duration=audio_data.get('duration'),
            message_id=result.get('message_id'),
            source=source,
            source_url=source_url
        )
        
        if saved:
            logger.info(f"Audio from API saved for user {user_id}")
            return True
        else:
            logger.error(f"Failed to save API audio for user {user_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error saving API audio: {e}")
        return False

