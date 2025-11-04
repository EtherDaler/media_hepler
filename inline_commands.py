import hashlib
import re
import os

from aiogram import Bot
from aiogram.types import (
    InlineQuery, InlineQueryResultArticle, 
    InputTextMessageContent, InlineQueryResultVideo, 
    InlineQueryResultAudio, ChosenInlineResult, InputMediaAudio, InputMediaVideo
)
from aiogram.dispatcher.router import Router
from urllib.parse import urlparse

from bot_commands import send_video_through_api, send_audio_through_api
from worker import download_from_youtube, download_instagram_reels, TikTokDownloader, get_audio_from_youtube


# Создаем роутер для инлайн-обработчиков
inline_router = Router()

# Импортируем ваши существующие функции


def detect_platform(url: str) -> str:
    """Определяет платформу по URL"""
    if 'instagram.com' in url or 'instagr.am' in url:
        return 'instagram'
    elif 'tiktok.com' in url or 'vm.tiktok.com' in url:
        return 'tiktok'
    elif 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    return 'unknown'


def is_valid_url(text: str) -> bool:
    """Проверяет, является ли текст валидным URL поддерживаемой платформы"""
    url_pattern = re.compile(
        r'^(https?://)?'  # http:// or https://
        r'((www\.)?)'     # www.
        r'((youtube|youtu|instagram|tiktok)\.)'  # домены
        r'([a-zA-Z0-9-]+)'
        r'(\.[a-zA-Z]{2,})'
        r'(/.*)?$'
    )
    return bool(url_pattern.match(text))


async def download_video_content(url: str, platform: str) -> dict:
    """
    Скачивает видео и возвращает информацию о файле
    Адаптация ваших существующих функций
    """
    try:
        if platform == 'youtube':
            file_name = await download_from_youtube(url)
        elif platform == 'instagram':
            file_name = await download_instagram_reels(url)
        elif platform == 'tiktok':
            downloader = TikTokDownloader(save_path='videos/tiktok')
            file_name = downloader.download_video(url)
        else:
            raise Exception("Unsupported platform")
        file_path = f"./videos/{platform}/{file_name}"

        # Получаем размер файла
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        file_size_mb = file_size / (1024 * 1024)

        return {
            'file_path': file_path,
            'title': os.path.basename(file_path),
            'file_size': file_size,
            'file_size_mb': file_size_mb,
            'is_local': True
        }
            
    except Exception as e:
        raise Exception(f"Download failed: {str(e)}")


async def download_audio_content(url: str, platform: str) -> dict:
    """
    Скачивает аудио и возвращает информацию о файле
    Только для YouTube
    """
    try:
        if platform != 'youtube':
            raise Exception("Audio download only for YouTube")
        
        file_name = await get_audio_from_youtube(url)
        file_path = f"./audio/{platform}/{file_name}"

        # Получаем размер файла
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        file_size_mb = file_size / (1024 * 1024)

        return {
            'file_path': file_path,
            'title': os.path.basename(file_path),
            'file_size': file_size,
            'file_size_mb': file_size_mb,
            'is_local': True
        }
            
    except Exception as e:
        raise Exception(f"Download failed: {str(e)}")
    

async def process_direct_download(inline_query: InlineQuery, url: str, platform: str):
    """Обрабатывает прямую загрузку для Instagram/TikTok"""
    try:
        # Показываем уведомление о загрузке
        await inline_query.answer([], cache_time=1, is_personal=True)
        
        # Скачиваем видео
        video_info = await download_video_content(url, platform)
        
        if not video_info:
            raise Exception("Не удалось скачать видео")
        
        # Для инлайн-режима проверяем размер файла
        file_size_mb = video_info.get('file_size_mb', 0)
        
        if file_size_mb > 50:  # Лимит для обычного бота
            # Используем локальный Bot API для больших файлов
            results = [
                InlineQueryResultArticle(
                    id=f"large_file_{hashlib.md5(url.encode()).hexdigest()}",
                    title="🎥 Большое видео (через API)",
                    description=f"Размер: {file_size_mb:.1f} МБ - отправка через API",
                    input_message_content=InputTextMessageContent(
                        message_text=f"📥 Загружаю большое видео...\n"
                                   f"📏 Размер: {file_size_mb:.1f} МБ\n"
                                   f"⏳ Это может занять некоторое время..."
                    )
                )
            ]
        else:
            # Маленький файл - используем стандартный метод
            file_id = await upload_file_to_telegram(inline_query.bot, video_info['file_path'])
            
            results = [
                InlineQueryResultVideo(
                    id=f"video_{hashlib.md5(url.encode()).hexdigest()}",
                    video_url=file_id,
                    mime_type="video/mp4",
                    thumb_url="https://via.placeholder.com/120x90/0088cc/FFFFFF?text=Video",
                    title=video_info.get('title', f'Видео с {platform.capitalize()}'),
                    description="Нажмите чтобы отправить видео",
                    caption=create_caption(video_info, platform)
                )
            ]
        
        await inline_query.bot.answer_inline_query(
            inline_query.id,
            results,
            cache_time=300,
            is_personal=True
        )
        
    except Exception as e:
        results = [
            InlineQueryResultArticle(
                id="error",
                title="❌ Ошибка",
                description=str(e),
                input_message_content=InputTextMessageContent(
                    message_text=f"❌ Ошибка: {str(e)}"
                )
            )
        ]
        await inline_query.answer(results, cache_time=1)


async def upload_file_to_telegram(bot: Bot, file_path: str, chat_id: int = None) -> str:
    """
    Загружает локальный файл в Telegram и возвращает file_id
    """
    try:
        # Определяем тип файла по расширению
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in ['.mp4', '.avi', '.mov', '.mkv']:
            # Видео файл
            with open(file_path, 'rb') as video_file:
                result = await bot.send_video(
                    chat_id or 123456789,  # временный chat_id
                    video=video_file,
                    caption="Uploading..."
                )
                return result.video.file_id
                
        elif ext in ['.mp3', '.m4a', '.wav']:
            # Аудио файл
            with open(file_path, 'rb') as audio_file:
                result = await bot.send_audio(
                    chat_id or 123456789,  # временный chat_id
                    audio=audio_file,
                    caption="Uploading..."
                )
                return result.audio.file_id
        else:
            raise Exception("Unsupported file format")
            
    except Exception as e:
        raise Exception(f"Upload failed: {str(e)}")


def create_caption(info: dict, platform: str, content_type: str = 'video') -> str:
    """Создает подпись для файла"""
    title = info.get('title', '')
    
    platform_icons = {
        'youtube': '📺',
        'instagram': '📷', 
        'tiktok': '🎵'
    }
    
    content_icons = {
        'video': '🎥',
        'audio': '🎵'
    }
    
    icon = content_icons.get(content_type, '📄')
    platform_icon = platform_icons.get(platform, '🔗')
    
    caption = f"{icon} {title}\n{platform_icon} Скачано via @your_bot_username"
    
    return caption


@inline_router.inline_handler()
async def inline_query_handler(inline_query: InlineQuery):
    query = inline_query.query.strip()
    bot = inline_query.bot
    
    if not query:
        # Показываем инструкцию при пустом запросе
        results = [
            InlineQueryResultArticle(
                id="help",
                title="📹 Скачать видео/аудио",
                description="Введите URL из YouTube, Instagram или TikTok",
                input_message_content=InputTextMessageContent(
                    message_text="🤖 Бот для скачивания видео/аудио\n\n"
                               "Просто введите URL из:\n"
                               "• YouTube - выберите видео или аудио\n"
                               "• Instagram/TikTok - сразу скачается видео\n\n"
                               "Пример: @your_bot https://youtube.com/..."
                )
            )
        ]
        await inline_query.answer(results, cache_time=3600)
        return
    
    if not is_valid_url(query):
        results = [
            InlineQueryResultArticle(
                id="invalid_url",
                title="❌ Неверный URL",
                description="Введите корректный URL YouTube, Instagram или TikTok",
                input_message_content=InputTextMessageContent(
                    message_text="❌ Пожалуйста, введите корректный URL видео"
                )
            )
        ]
        await inline_query.answer(results, cache_time=1)
        return
    
    # Определяем тип платформы
    platform = detect_platform(query)
    
    if platform in ['instagram', 'tiktok']:
        # Для Instagram и TikTok сразу скачиваем видео
        await process_direct_download(inline_query, query, platform)
    elif platform == 'youtube':
        # Для YouTube предлагаем выбор
        await show_youtube_options(inline_query, query)
    else:
        results = [
            InlineQueryResultArticle(
                id="unsupported",
                title="❌ Неподдерживаемая платформа",
                description="Поддерживается только YouTube, Instagram, TikTok",
                input_message_content=InputTextMessageContent(
                    message_text="❌ Поддерживаются только:\nYouTube, Instagram, TikTok"
                )
            )
        ]
        await inline_query.answer(results, cache_time=1)


async def process_youtube_choice(chosen_result: ChosenInlineResult, result_id: str, url: str):
    """Обрабатывает выбор YouTube опции с поддержкой больших файлов"""
    bot = chosen_result.bot
    
    try:
        content_type = 'video' if 'youtube_video' in result_id else 'audio'
        
        # Редактируем сообщение "Скачиваю..."
        loading_text = f"📥 Скачиваю {content_type} с YouTube..."
        await bot.edit_message_text(
            chat_id=chosen_result.from_user.id,
            message_id=chosen_result.inline_message_id,
            text=loading_text
        )
        
        # Скачиваем контент
        if content_type == 'video':
            file_info = await download_video_content(url, 'youtube')
        else:
            file_info = await download_audio_content(url, 'youtube')
        
        if not file_info:
            raise Exception(f"Не удалось скачать {content_type}")
        
        file_size_mb = file_info.get('file_size_mb', 0)
        
        # Проверяем размер файла
        if file_size_mb > 50:  # Большой файл - используем API
            await send_large_file_via_api(chosen_result, file_info, content_type)
        else:
            # Маленький файл - стандартный метод
            await send_small_file_via_inline(bot, chosen_result, file_info, content_type)
            
    except Exception as e:
        error_text = f"❌ Ошибка при скачивании: {str(e)}"
        await bot.edit_message_text(
            chat_id=chosen_result.from_user.id,
            message_id=chosen_result.inline_message_id,
            text=error_text
        )

async def send_large_file_via_api(chosen_result: ChosenInlineResult, file_info: dict, content_type: str):
    """Отправляет большой файл через локальный Bot API"""
    bot = chosen_result.bot
    
    try:
        # Обновляем статус
        await bot.edit_message_text(
            chat_id=chosen_result.from_user.id,
            message_id=chosen_result.inline_message_id,
            text=f"📤 Отправляю {content_type} через API..."
        )
        
        # Запускаем отправку в отдельном потоке (т.к. requests блокирующий)
        loop = asyncio.get_event_loop()
        
        if content_type == 'video':
            # Получаем размеры видео (нужно будет добавить эту функцию)
            width, height = await get_video_dimensions(file_info['file_path'])
            
            success = await loop.run_in_executor(
                None, 
                send_video_through_api,
                chosen_result.from_user.id,
                file_info['file_path'],
                width,
                height
            )
        else:
            # Для аудио нужно создать аналогичную функцию send_audio_through_api
            success = await loop.run_in_executor(
                None,
                send_audio_through_api,
                chosen_result.from_user.id,
                file_info['file_path']
            )
        
        if success:
            # Удаляем инлайн-сообщение после успешной отправки
            await bot.delete_message(
                chat_id=chosen_result.from_user.id,
                message_id=chosen_result.inline_message_id
            )
        else:
            raise Exception("Не удалось отправить файл через API")
            
    except Exception as e:
        error_text = f"❌ Ошибка при отправке через API: {str(e)}"
        await bot.edit_message_text(
            chat_id=chosen_result.from_user.id,
            message_id=chosen_result.inline_message_id,
            text=error_text
        )

async def send_small_file_via_inline(bot: Bot, chosen_result: ChosenInlineResult, file_info: dict, content_type: str):
    """Отправляет маленький файл через инлайн-режим"""
    # Загружаем файл в Telegram
    file_id = await upload_file_to_telegram(bot, file_info['file_path'], chosen_result.from_user.id)
    
    caption = create_caption(file_info, 'youtube', content_type)
    
    # Отправляем файл
    if content_type == 'video':
        await bot.edit_message_media(
            chat_id=chosen_result.from_user.id,
            message_id=chosen_result.inline_message_id,
            media=InputMediaVideo(
                media=file_id,
                caption=caption
            )
        )
    else:
        await bot.edit_message_media(
            chat_id=chosen_result.from_user.id,
            message_id=chosen_result.inline_message_id,
            media=InputMediaAudio(
                media=file_id,
                caption=caption,
                title=file_info.get('title', 'Аудио')
            )
        )

async def get_video_dimensions(file_path: str) -> tuple:
    """Получает размеры видео файла"""
    try:
        # Используем ffmpeg или другую библиотеку для получения размеров
        # Это упрощенный пример - нужно реализовать получение реальных размеров
        import subprocess
        import json
        
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', 
            '-show_format', '-show_streams', file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        info = json.loads(result.stdout)
        
        for stream in info.get('streams', []):
            if stream.get('codec_type') == 'video':
                return stream.get('width', 1280), stream.get('height', 720)
        
        return 1280, 720  # значения по умолчанию
    except Exception:
        return 1280, 720  # значения по умолчанию в случае ошибки

    """Показывает варианты для YouTube"""
    try:
        results = []
        
        # Вариант 1: Скачать видео
        results.append(
            InlineQueryResultArticle(
                id=f"youtube_video_{hashlib.md5(url.encode()).hexdigest()}",
                title="🎥 Скачать видео",
                description="Скачать видео с YouTube",
                input_message_content=InputTextMessageContent(
                    message_text=f"🔄 Скачиваю видео с YouTube...\nURL: {url}"
                ),
                thumb_url="https://via.placeholder.com/64/FF0000/FFFFFF?text=VID"
            )
        )
        
        # Вариант 2: Скачать аудио
        results.append(
            InlineQueryResultArticle(
                id=f"youtube_audio_{hashlib.md5(url.encode()).hexdigest()}",
                title="🎵 Скачать аудио",
                description="Скачать аудио с YouTube",
                input_message_content=InputTextMessageContent(
                    message_text=f"🔄 Скачиваю аудио с YouTube...\nURL: {url}"
                ),
                thumb_url="https://via.placeholder.com/64/00FF00/FFFFFF?text=MP3"
            )
        )
        
        await inline_query.answer(results, cache_time=300, is_personal=True)
        
    except Exception as e:
        results = [
            InlineQueryResultArticle(
                id="error",
                title="❌ Ошибка",
                description=str(e),
                input_message_content=InputTextMessageContent(
                    message_text=f"❌ Ошибка: {str(e)}"
                )
            )
        ]
        await inline_query.answer(results, cache_time=1)


@inline_router.chosen_inline_handler()
async def chosen_inline_result_handler(chosen_result: ChosenInlineResult):
    """Обрабатывает выбор опции в инлайн-режиме"""
    result_id = chosen_result.result_id
    query = chosen_result.query
    
    # Проверяем, это YouTube запрос?
    if result_id.startswith('youtube_'):
        await process_youtube_choice(chosen_result, result_id, query)


async def process_youtube_choice(chosen_result: ChosenInlineResult, result_id: str, url: str):
    """Обрабатывает выбор YouTube опции"""
    bot = chosen_result.bot
    
    try:
        # Определяем тип выбора (видео или аудио)
        content_type = 'video' if 'youtube_video' in result_id else 'audio'
        
        # Редактируем сообщение "Скачиваю..."
        loading_text = f"📥 Скачиваю {content_type} с YouTube..."
        await bot.edit_message_text(
            chat_id=chosen_result.from_user.id,
            message_id=chosen_result.inline_message_id,
            text=loading_text
        )
        
        # Скачиваем контент
        if content_type == 'video':
            file_info = await download_video_content(url, 'youtube')
        else:
            file_info = await download_audio_content(url, 'youtube')
        
        if not file_info:
            raise Exception(f"Не удалось скачать {content_type}")
        
        # Если файл локальный, загружаем его в Telegram
        if file_info.get('is_local'):
            file_id = await upload_file_to_telegram(bot, file_info['file_path'], chosen_result.from_user.id)
            file_url = file_id
        else:
            file_url = file_info['file_url']
        
        caption = create_caption(file_info, 'youtube', content_type)
        
        # Отправляем файл
        if content_type == 'video':
            await bot.edit_message_media(
                chat_id=chosen_result.from_user.id,
                message_id=chosen_result.inline_message_id,
                media=InputMediaVideo(
                    media=file_url,
                    caption=caption
                )
            )
        else:
            await bot.edit_message_media(
                chat_id=chosen_result.from_user.id,
                message_id=chosen_result.inline_message_id,
                media=InputMediaAudio(
                    media=file_url,
                    caption=caption,
                    title=file_info.get('title', 'Аудио')
                )
            )
            
    except Exception as e:
        error_text = f"❌ Ошибка при скачивании: {str(e)}"
        await bot.edit_message_text(
            chat_id=chosen_result.from_user.id,
            message_id=chosen_result.inline_message_id,
            text=error_text
        )