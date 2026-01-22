"""
Inline режим бота для скачивания видео в любом чате.
Использование: @bot_username ссылка
"""

import hashlib
import os
import logging
import asyncio

from aiogram import Router
from aiogram.types import (
    InlineQuery, 
    InlineQueryResultArticle, 
    InputTextMessageContent,
    ChosenInlineResult,
    FSInputFile,
    InputMediaVideo,
    InputMediaAudio
)

import worker
from bot_commands import send_video_through_api, send_audio_through_api

logger = logging.getLogger(__name__)

inline_router = Router()


def get_video_dimensions(file_path: str) -> tuple:
    """Получает размеры видео через ffprobe"""
    try:
        import subprocess
        import json
        
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_streams', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        info = json.loads(result.stdout)
        
        for stream in info.get('streams', []):
            if stream.get('codec_type') == 'video':
                return stream.get('width', 1280), stream.get('height', 720)
        
        return 1280, 720
    except Exception:
        return 1280, 720


def detect_platform(url: str) -> str:
    """Определяет платформу по URL"""
    url_lower = url.lower()
    if 'instagram.com' in url_lower or 'instagr.am' in url_lower:
        return 'instagram'
    elif 'tiktok.com' in url_lower or 'vm.tiktok.com' in url_lower:
        return 'tiktok'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'pinterest' in url_lower or 'pin.it' in url_lower:
        return 'pinterest'
    return 'unknown'


def generate_result_id(url: str, content_type: str) -> str:
    """Генерирует уникальный ID для результата"""
    return f"{content_type}_{hashlib.md5(url.encode()).hexdigest()[:16]}"


@inline_router.inline_query()
async def inline_query_handler(inline_query: InlineQuery):
    """Обработчик inline запросов"""
    query = inline_query.query.strip()
    
    # Пустой запрос — показываем подсказку
    if not query:
        results = [
            InlineQueryResultArticle(
                id="help",
                title="📥 Скачать видео",
                description="Вставьте ссылку на YouTube, Instagram, TikTok или Pinterest",
                input_message_content=InputTextMessageContent(
                    message_text="📥 <b>Media Helper - Inline режим</b>\n\n"
                               "Чтобы скачать видео, напишите:\n"
                               "<code>@django_media_helper_bot ссылка</code>\n\n"
                               "Поддерживаются: YouTube, Instagram, TikTok, Pinterest",
                    parse_mode="HTML"
                )
            )
        ]
        await inline_query.answer(results, cache_time=300)
        return
    
    # Проверяем URL
    platform = detect_platform(query)
    
    if platform == 'unknown':
        results = [
            InlineQueryResultArticle(
                id="invalid",
                title="❌ Неподдерживаемая ссылка",
                description="Поддерживаются: YouTube, Instagram, TikTok, Pinterest",
                input_message_content=InputTextMessageContent(
                    message_text="❌ Эта ссылка не поддерживается.\n\n"
                               "Поддерживаются: YouTube, Instagram, TikTok, Pinterest"
                )
            )
        ]
        await inline_query.answer(results, cache_time=60)
        return
    
    # Формируем результаты
    results = []
    
    platform_names = {
        'youtube': 'YouTube',
        'instagram': 'Instagram Reels',
        'tiktok': 'TikTok',
        'pinterest': 'Pinterest'
    }
    
    platform_name = platform_names.get(platform, platform.capitalize())
    
    # Вариант: Скачать видео
    results.append(
        InlineQueryResultArticle(
            id=generate_result_id(query, "video"),
            title=f"🎥 Скачать видео с {platform_name}",
            description="Нажмите — видео появится прямо здесь",
            input_message_content=InputTextMessageContent(
                message_text=f"⏳ Скачиваю видео с {platform_name}...",
                parse_mode="HTML"
            )
        )
    )
    
    # Для YouTube добавляем вариант аудио
    if platform == 'youtube':
        results.append(
            InlineQueryResultArticle(
                id=generate_result_id(query, "audio"),
                title="🎵 Скачать аудио с YouTube",
                description="Нажмите — аудио появится прямо здесь",
                input_message_content=InputTextMessageContent(
                    message_text="⏳ Скачиваю аудио с YouTube...",
                    parse_mode="HTML"
                )
            )
        )
    
    await inline_query.answer(results, cache_time=60, is_personal=True)


@inline_router.chosen_inline_result()
async def chosen_inline_handler(chosen: ChosenInlineResult):
    """
    Обработчик выбранного inline результата.
    Скачивает контент и заменяет сообщение на медиафайл.
    """
    result_id = chosen.result_id
    url = chosen.query.strip()
    user_id = chosen.from_user.id
    inline_message_id = chosen.inline_message_id
    
    logger.info(f"=== CHOSEN INLINE RESULT ===")
    logger.info(f"result_id: {result_id}")
    logger.info(f"url: {url}")
    logger.info(f"user_id: {user_id}")
    logger.info(f"inline_message_id: {inline_message_id}")
    
    if not url or result_id in ['help', 'invalid']:
        logger.info("Skipping: help or invalid result")
        return
    
    if not inline_message_id:
        # Без inline_message_id не можем редактировать
        logger.warning("No inline_message_id received. Enable /setinlinefeedback in @BotFather!")
        return
    
    platform = detect_platform(url)
    logger.info(f"Platform detected: {platform}")
    is_audio = result_id.startswith("audio_")
    
    file_path = None
    thumbnail_path = None
    
    try:
        # Скачиваем контент
        if is_audio and platform == 'youtube':
            result = await worker.get_audio_from_youtube(url)
            if result and result.get('audio'):
                file_path = f"./audio/youtube/{result['audio']}"
                thumbnail_path = result.get('thumbnail')
        else:
            # Видео
            if platform == 'youtube':
                filename = await worker.download_from_youtube(url)
                if filename:
                    file_path = f"./videos/youtube/{filename}"
            elif platform == 'instagram':
                filename = await worker.download_instagram_reels(url)
                if filename:
                    file_path = f"./videos/reels/{filename}"
            elif platform == 'tiktok':
                downloader = worker.TikTokDownloader(save_path='videos/tiktok')
                filename = downloader.download_video(url)
                if filename:
                    file_path = f"./videos/tiktok/{filename}"
            elif platform == 'pinterest':
                try:
                    import pinterest
                    filename = await pinterest.download_pinterest_video(url)
                    if filename:
                        file_path = f"./videos/pinterest/{filename}"
                except Exception:
                    pass
        
        if not file_path or not os.path.isfile(file_path):
            await chosen.bot.edit_message_text(
                inline_message_id=inline_message_id,
                text="❌ Не удалось скачать. Попробуйте отправить ссылку боту напрямую."
            )
            return
        
        file_size = os.path.getsize(file_path)
        is_large_file = file_size > 50 * 1024 * 1024  # > 50 МБ
        
        # Загружаем файл в Telegram через личку пользователю, получаем file_id
        if is_audio:
            if is_large_file:
                # Большой файл — через локальный Bot API
                api_result = await asyncio.to_thread(
                    send_audio_through_api,
                    user_id,
                    file_path,
                    thumbnail_path,
                    False  # delete_after
                )
                if not api_result.get('success'):
                    await chosen.bot.edit_message_text(
                        inline_message_id=inline_message_id,
                        text="❌ Не удалось отправить большой файл."
                    )
                    return
                
                # Извлекаем file_id из ответа API
                response = api_result.get('response', {})
                result_data = response.get('result', {})
                audio_data = result_data.get('audio', {})
                file_id = audio_data.get('file_id')
                temp_message_id = result_data.get('message_id')
            else:
                # Маленький файл — через aiogram
                temp_msg = await chosen.bot.send_audio(
                    chat_id=user_id,
                    audio=FSInputFile(file_path),
                    thumbnail=FSInputFile(thumbnail_path) if thumbnail_path and os.path.isfile(thumbnail_path) else None,
                    caption="🎵 via @django_media_helper_bot"
                )
                file_id = temp_msg.audio.file_id
                temp_message_id = temp_msg.message_id
            
            if not file_id:
                await chosen.bot.edit_message_text(
                    inline_message_id=inline_message_id,
                    text="❌ Не удалось загрузить файл."
                )
                return
            
            # Редактируем inline сообщение — заменяем текст на аудио
            await chosen.bot.edit_message_media(
                inline_message_id=inline_message_id,
                media=InputMediaAudio(
                    media=file_id,
                    caption="🎵 via @django_media_helper_bot"
                )
            )
            
            # Удаляем временное сообщение из лички
            if temp_message_id:
                await chosen.bot.delete_message(chat_id=user_id, message_id=temp_message_id)
            
        else:
            # Видео
            if is_large_file:
                # Большой файл — через локальный Bot API
                # Получаем размеры видео
                width, height = await asyncio.to_thread(get_video_dimensions, file_path)
                
                api_result = await asyncio.to_thread(
                    send_video_through_api,
                    user_id,
                    file_path,
                    width,
                    height
                )
                if not api_result:
                    await chosen.bot.edit_message_text(
                        inline_message_id=inline_message_id,
                        text="❌ Не удалось отправить большой файл."
                    )
                    return
                
                # send_video_through_api возвращает True/False, нужно получить file_id другим способом
                # Ждём и ищем последнее сообщение — это не идеально, но работает
                # Лучше переделать send_video_through_api чтобы возвращал response
                await chosen.bot.edit_message_text(
                    inline_message_id=inline_message_id,
                    text="✅ Видео отправлено в личные сообщения бота.\nФайл слишком большой для inline."
                )
                return
            else:
                # Маленький файл — через aiogram
                temp_msg = await chosen.bot.send_video(
                    chat_id=user_id,
                    video=FSInputFile(file_path),
                    caption="🎥 via @django_media_helper_bot"
                )
                file_id = temp_msg.video.file_id
                temp_message_id = temp_msg.message_id
            
            # Редактируем inline сообщение — заменяем текст на видео
            await chosen.bot.edit_message_media(
                inline_message_id=inline_message_id,
                media=InputMediaVideo(
                    media=file_id,
                    caption="🎥 via @django_media_helper_bot"
                )
            )
            
            # Удаляем временное сообщение из лички
            await chosen.bot.delete_message(chat_id=user_id, message_id=temp_message_id)
        
        logger.info(f"Inline download success: {platform} {'audio' if is_audio else 'video'} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Inline download error: {e}")
        try:
            await chosen.bot.edit_message_text(
                inline_message_id=inline_message_id,
                text="❌ Ошибка при скачивании. Попробуйте отправить ссылку боту напрямую."
            )
        except Exception:
            pass
    finally:
        # Удаляем временные файлы
        if file_path and os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        if thumbnail_path and os.path.isfile(thumbnail_path):
            try:
                os.remove(thumbnail_path)
            except Exception:
                pass
