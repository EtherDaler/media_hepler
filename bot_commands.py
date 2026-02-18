import os
import subprocess
import worker
import metadata
import mimetypes
import logging
import pinterest
import requests
import re

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, ContentType, FSInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramEntityTooLarge, TelegramForbiddenError, TelegramBadRequest
from aiogram.enums.chat_action import ChatAction

from sqlalchemy.ext.asyncio import AsyncSession
from db import db_commands
from db.audio_helper import save_sent_audio, save_audio_from_api_response
from db.download_log import log_download, should_add_watermark, get_today_stats
from data import config
from models import User
from link_handler import handle_instagram_link, handle_youtube_link, handle_pinterest_link, handle_tiktok_link


router = Router()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
BOT_TOKEN = config.BOT_TOKEN


def check_bot_api_health():
    """
    Проверка доступности локального Bot API
    """
    try:
        # Используем тот же URL, что и в curl
        health_url = f"http://127.0.0.1:8081/bot{BOT_TOKEN}/getMe"
        headers = {
            'Connection': 'close',
            'Expect': ''   # попытка убрать Expect: 100-continue
        }
        response = requests.get(health_url, headers=headers, timeout=10)
        
        logger.info(f"Bot API Health Check - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            is_ok = data.get('ok', False)
            logger.info(f"Bot API is OK: {is_ok}")
            return is_ok
        else:
            logger.error(f"Bot API Health Check failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Bot API ConnectionError: {e}")
        return False
    except requests.exceptions.Timeout as e:
        logger.error(f"Bot API Timeout: {e}")
        return False
    except Exception as e:
        logger.error(f"Bot API Health Check error: {e}")
        return False
    

def send_video_through_api(chat_id, file_path, width, height):
    """
    Отправка видео в Telegram через API.

    :param chat_id: ID чата (получателя)
    :param file_path: Путь к видеофайлу
    :param width: Ширина видео
    :param height: Высота видео
    :return: True, если успешно отправлено, иначе False
    """
    # Telegram API URL
    url = f"http://127.0.0.1:8081/bot{BOT_TOKEN}/sendVideo"
    response = None

    # Проверяем существование файла
    if not os.path.isfile(file_path):
        logger.error(f"Файл {file_path} не найден.")
        return False
    
    if not check_bot_api_health():
        logger.error("Локальный API не доступен")
        return False

    # Отправка запроса
    try:
        with open(file_path, 'rb') as video:
            files = {
                # явно указываем имя файла и mime
                'video': (os.path.basename(file_path), video, mimetypes.guess_type(file_path)[0] or 'application/octet-stream')
            }
            headers = {
                'Connection': 'close',
                'Expect': ''   # попытка убрать Expect: 100-continue
            }
            data = {
                'chat_id': chat_id,
                'caption': 'Ваше видео готово!\n@django_media_helper_bot',
                'width': width,
                'height': height,
                'supports_streaming': True
            }
            response = requests.post(url, headers=headers, data=data, files=files, timeout=(30, 300))
            logger.info(f"API Response: {response.status_code}, {response.text}")
    except requests.exceptions.Timeout:
        logger.error("Таймаут при отправке видео")
        return False
    except Exception as e:
        logger.error(f"Ошибка при отправке видео: {e}")
        return False

    # Удаляем файл после отправки
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Файл {file_path} успешно удален после отправки.")
        except Exception as e:
            logger.warning(f"Не удалось удалить файл {file_path}: {e}")

    # Проверяем статус ответа
    if response.status_code == 200:
        logger.info("Видео успешно отправлено!")
        return True
    else:
        logger.error(f"Ошибка при отправке видео: {response.status_code}, {response.text}")
        return False


def send_audio_through_api(chat_id: int, file_path: str, thumbnail_path: str = None, delete_after: bool = False) -> dict:
    """
    Отправка аудио в Telegram через API (аналогично send_video_through_api)
    
    Args:
        chat_id: ID чата
        file_path: Путь к аудио файлу
        thumbnail_path: Путь к обложке (опционально)
        delete_after: Удалить файл после отправки
    
    Returns:
        dict с ключами 'success' и 'response' (JSON ответ API)
    """
    url = f"http://127.0.0.1:8081/bot{BOT_TOKEN}/sendAudio"
    
    if not os.path.isfile(file_path):
        logger.error(f"Файл {file_path} не найден.")
        return {'success': False, 'response': None}
    
    try:
        files = {}
        
        with open(file_path, 'rb') as audio_file:
            files['audio'] = (os.path.basename(file_path), audio_file.read(), 'audio/mpeg')
        
        # Добавляем thumbnail если есть
        if thumbnail_path and os.path.isfile(thumbnail_path):
            with open(thumbnail_path, 'rb') as thumb_file:
                files['thumbnail'] = (os.path.basename(thumbnail_path), thumb_file.read(), 'image/jpeg')
        
        headers = {
            'Connection': 'close',
            'Expect': ''
        }
        data = {
            'chat_id': chat_id,
            'caption': 'Ваше аудио готово!\n@django_media_helper_bot',
            'title': os.path.basename(file_path)
        }
        response = requests.post(url, headers=headers, data=data, files=files, timeout=(30, 300))
        logger.info(f"Audio API Response: {response.status_code}")
    except Exception as e:
        logger.error(f"Ошибка при отправке аудио: {e}")
        return {'success': False, 'response': None}
    
    # Удаляем файлы после отправки если указано
    if delete_after:
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Не удалось удалить файл {file_path}: {e}")
        if thumbnail_path and os.path.isfile(thumbnail_path):
            try:
                os.remove(thumbnail_path)
            except Exception as e:
                logger.warning(f"Не удалось удалить thumbnail {thumbnail_path}: {e}")
    
    if response.status_code == 200:
        return {'success': True, 'response': response.json()}
    else:
        return {'success': False, 'response': None}


class YoutubeState(StatesGroup):
    link = State()
    command_type = State()

class VideoState(StatesGroup):
    video = State() 

class MetaDataState(StatesGroup):
    file = State()

class SendAllState(StatesGroup):
    message = State()

class ReplaceAudioState(StatesGroup):
    video = State()
    audio = State()

class AnswerState(StatesGroup):
    tg_id = State()
    message = State()

class YoutubeSearchState(StatesGroup):
    select_action = State()
    select_format = State()

class ShazamState(StatesGroup):
    confirm_download = State()

@router.message(CommandStart())
async def command_start_handler(message: Message, session: AsyncSession) -> None:
    file = "./texts/start_text.txt"
    status = True
    user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
    if user is None:
        status = await db_commands.db_register_user(message, session)
        if status:
            user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
        else:
            await message.answer("Произошла ошибка, повторите попытку позже!")
    if status:
        with open(file, "r", encoding="utf-8") as f:
            command_start_text = f.read()
            await message.answer(command_start_text.format(message.from_user.full_name))

@router.message(Command("donate"))
async def command_donate(message: Message) -> None:
    await message.answer("https://boosty.to/daler_hojimatov/donate \nhttps://www.donationalerts.com/r/etherdaler \nссылки для оплаты.\nСпасибо за поддержку, ваши средства помогут поддерживать проект.")
    

@router.message(Command("youtube_video"))
async def command_youtube_video(message: Message, state: FSMContext, session: AsyncSession) -> None:
    status = True
    user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
    if user is None:
        status = await db_commands.db_register_user(message, session)
        if status:
            user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
        else:
            await message.answer("Произошла ошибка, повторите попытку позже!")
    if status:
        await state.update_data(command_type="video")
        await message.answer("Отправь мне ссылку на видео")
        await state.set_state(YoutubeState.link)

@router.message(Command("youtube_audio"))
async def command_youtube_audio(message: Message, state: FSMContext, session: AsyncSession) -> None:
    status = True
    user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
    if user is None:
        status = await db_commands.db_register_user(message, session)
        if status:
            user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
        else:
            await message.answer("Произошла ошибка, повторите попытку позже!")
    if status:
        await state.update_data(command_type="audio")
        await message.answer("Отправь мне ссылку на видео")
        await state.set_state(YoutubeState.link)

@router.message(Command("reel"))
async def command_reel(message: Message, state: FSMContext, session: AsyncSession) -> None:
    status = True
    user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
    if user is None:
        status = await db_commands.db_register_user(message, session)
        if status:
            user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
        else:
            await message.answer("Произошла ошибка, повторите попытку позже!")
    if status:
        await state.update_data(command_type="reel")
        await message.answer("Отправь мне ссылку на видео")
        await state.set_state(YoutubeState.link)

@router.message(Command("pinterest_video"))
async def command_pinterest_video(message: Message, state: FSMContext, session: AsyncSession) -> None:
    status = True
    user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
    if user is None:
        status = await db_commands.db_register_user(message, session)
        if status:
            user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
        else:
            await message.answer("Произошла ошибка, повторите попытку позже!")
    if status:
        await state.update_data(command_type="pinterest")
        await message.answer("Отправь мне ссылку на видео")
        await state.set_state(YoutubeState.link)

@router.message(Command("tiktok"))
async def command_tiktok_video(message: Message, state: FSMContext, session: AsyncSession) -> None:
    status = True
    user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
    if user is None:
        status = await db_commands.db_register_user(message, session)
        if status:
            user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
        else:
            await message.answer("Произошла ошибка, повторите попытку позже!")
    if status:
        await state.update_data(command_type="tiktok")
        await message.answer("Отправь мне ссылку на видео")
        await state.set_state(YoutubeState.link)

@router.message(Command("convert_to_audio"))
async def command_convert_to_audio(message: Message, state: FSMContext, session: AsyncSession) -> None:
    status = True
    user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
    if user is None:
        status = await db_commands.db_register_user(message, session)
        if status:
            user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
        else:
            await message.answer("Произошла ошибка, повторите попытку позже!")
    if status:
        await message.answer("Отправь мне видео")
        await state.set_state(VideoState.video)

@router.message(Command("replace_audio"))
async def command_replace_audio(message: Message, state: FSMContext, session: AsyncSession) -> None:
    status = True
    user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
    if user is None:
        status = await db_commands.db_register_user(message, session)
        if status:
            user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
        else:
            await message.answer("Произошла ошибка, повторите попытку позже!")
    if status:
        await message.answer("Отправь мне видео")
        await state.set_state(ReplaceAudioState.video)

@router.message(Command("get_metadata"))
async def command_get_metadata(message: Message, state: FSMContext, session: AsyncSession) -> None:
    status = True
    user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
    if user is None:
        status = await db_commands.db_register_user(message, session)
        if status:
            user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
        else:
            await message.answer("Произошла ошибка, повторите попытку позже!")
    if status:
        await message.answer("Отправь мне файл (jpg, jpeg, heic, png), а так же можешь отправить файл видео или аудио.\n ВАЖНО: ОТПРАВЛЯЙТЕ ФАЙЛОМ!")
        await state.set_state(MetaDataState.file)


@router.message(Command('count_users'))
async def count_users(message: Message, session: AsyncSession) -> None:
    user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
    if user is not None:
        if user.is_admin:
            users = await db_commands.db_get_items(User, message, session)
            await message.answer(f"Количесвто пользователей, использующих бот: {len(users)}")
        else:
            await message.answer("У вас нет прав!")
    else:
        await message.answer("У вас нет прав!")


@router.message(Command('stats'))
async def stats_command(message: Message, session: AsyncSession) -> None:
    """Статистика загрузок за сегодня (только для админов)"""
    user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
    if user is None or not user.is_admin:
        await message.answer("У вас нет прав!")
        return
    
    # Получаем статистику
    stats = await get_today_stats(session)
    
    # Формируем сообщение
    platform_icons = {
        'youtube': '🎬',
        'shorts': '📱',
        'reels': '📸',
        'tiktok': '🎵',
        'pinterest': '📌',
        'audio': '🎧',
        'instagram': '📷'
    }
    
    # Заголовок
    text = "📊 **Статистика за сегодня**\n\n"
    
    # DAU и общие загрузки
    text += f"👥 DAU (уникальных пользователей): **{stats['dau']}**\n"
    text += f"📥 Всего загрузок: **{stats['total_downloads']}**\n"
    text += f"❌ Ошибок: **{stats['errors']}**\n\n"
    
    # По платформам
    if stats['by_platform']:
        text += "📈 **По платформам:**\n"
        for platform, count in sorted(stats['by_platform'].items(), key=lambda x: x[1], reverse=True):
            icon = platform_icons.get(platform, '📦')
            text += f"  {icon} {platform}: {count}\n"
        text += "\n"
    else:
        text += "📈 Загрузок пока нет\n\n"
    
    # Топ 3 пользователя
    if stats['top_users']:
        text += "🏆 **Топ 3 пользователя:**\n"
        medals = ['🥇', '🥈', '🥉']
        for i, (user_id, count) in enumerate(stats['top_users']):
            medal = medals[i] if i < len(medals) else f"{i+1}."
            text += f"  {medal} ID: `{user_id}` — {count} загрузок\n"
    
    await message.answer(text, parse_mode='Markdown')

@router.message(Command('send_all'))
async def send_all(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
    if user is not None:
        if user.is_admin:
            await message.answer("Напишите сообщение")
            await state.set_state(SendAllState.message)
        else:
            await message.answer("У вас нет прав!")
    else:
        await message.answer("У вас нет прав!")

@router.message(Command('answer'))
async def answer(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
    if user is not None:
        if user.is_admin:
            await message.answer("Укажите tg_id пользователя")
            await state.set_state(AnswerState.tg_id)
        else:
            await message.answer("У вас нет прав!")
    else:
        await message.answer("У вас нет прав!")


@router.message(YoutubeState.link)
async def get_link(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.update_data(link = message.text)
    state_info = await state.get_data()
    link = state_info['link']
    user_id = message.from_user.id
    username = message.from_user.username
    if state_info["command_type"] == 'video':
        await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
        await message.answer("Подождите загружаем видео...")
        
        # Проверяем, нужен ли водяной знак
        add_wm = await should_add_watermark(session, user_id)
        
        try:
            filename = await worker.download_from_youtube(link)
        except Exception as e:
            logger.error(e)
            filename = None
        if filename:
            video_path = f"./videos/youtube/{filename}"
            # Добавляем водяной знак если нужно
            final_path = worker.add_watermark_if_needed(video_path, add_wm)
            
            width, height = worker.get_video_resolution_moviepy(final_path)
            file_size = os.path.getsize(final_path)
            logger.info(f"Размер файла: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
            try:
                doc = await message.bot.send_video(message.chat.id, FSInputFile(final_path), caption='Ваше видео готово!\n@django_media_helper_bot', supports_streaming=True, width=width, height=height)
                await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #YouTube")
                await log_download(session, user_id, 'youtube', link, status=True)
                if not doc:
                    await message.answer("Извините, произошла ошибка. Видео недоступно, либо указана неверная ссылка!")
                    await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #YouTube")
            except TelegramEntityTooLarge:
                logger.info("Обнаружен TelegramEntityTooLarge, переходим к отправке через API")
                sended = send_video_through_api(message.chat.id, final_path, width, height)
                if not sended:
                    await message.answer("Извините, размер файла слишком большой для отправки по Telegram.")
                    await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #YouTube, размер файла слишком большой")
                    await log_download(session, user_id, 'youtube', link, status=False)
                else:
                    await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #YouTube")
                    await log_download(session, user_id, 'youtube', link, status=True)
            except Exception as e:
                logger.error(f"Другая ошибка при отправке: {e}")
                await message.answer("Извините, произошла неизвестная ошибка при отправке видео.")
                await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #YouTube, {e}")
                await log_download(session, user_id, 'youtube', link, status=False)
            finally:
                if os.path.isfile(final_path):
                    os.remove(final_path)
                if final_path != video_path and os.path.isfile(video_path):
                    os.remove(video_path)
        else:
            await message.answer("Извините, произошла ошибка. Видео недоступно, либо указана неверная ссылка!")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #YouTube")
            await log_download(session, user_id, 'youtube', link, status=False)
            try:
                if filename and os.path.isfile(f"./videos/youtube/{filename}"):
                    os.remove(f"./videos/youtube/{filename}")
            except Exception as e:
                logger.error(e)

    elif state_info["command_type"] == 'audio':
        await message.answer("Подождите загружаем аудио...")
        await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VOICE)
        try:
            result = await worker.get_audio_from_youtube(link)
        except Exception as e:
            logger.error(e)
            result = None    
        if result:
            filename = result['audio']
            thumbnail_path = result.get('thumbnail')
            try:
                thumbnail = FSInputFile(thumbnail_path) if thumbnail_path and os.path.isfile(thumbnail_path) else None
                
                doc = await message.answer_audio(
                    audio=FSInputFile(f"./audio/youtube/{filename}"),
                    thumbnail=thumbnail,
                    caption="Ваше аудио готово!\n@django_media_helper_bot"
                )
                await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал аудио из #YouTube")
                await log_download(session, user_id, 'audio', link, status=True)
                if doc:
                    await save_sent_audio(session, doc, source='youtube', source_url=link)
            except TelegramEntityTooLarge:
                logger.info("Обнаружен TelegramEntityTooLarge, переходим к отправке через API")
                api_result = send_audio_through_api(
                    message.chat.id, 
                    f"./audio/youtube/{filename}",
                    thumbnail_path=thumbnail_path,
                    delete_after=True
                )
                if not api_result['success']:
                    await message.answer("Извините, размер файла слишком большой для отправки по Telegram.")
                    await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать аудио из #YouTube, размер файла слишком большой")
                    await log_download(session, user_id, 'audio', link, status=False)
                else:
                    await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал аудио из #YouTube")
                    await log_download(session, user_id, 'audio', link, status=True)
                    if api_result['response']:
                        await save_audio_from_api_response(session, user_id, api_result['response'], source='youtube', source_url=link)
            except Exception as e:
                logger.error(f"Другая ошибка при отправке: {e}")
                await message.answer("Извините, произошла неизвестная ошибка при отправке аудио.")
                await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать аудио из #YouTube, {e}")
                await log_download(session, user_id, 'audio', link, status=False)
            finally:
                if os.path.isfile(f"./audio/youtube/{filename}"):
                    os.remove(f"./audio/youtube/{filename}")
                if thumbnail_path and os.path.isfile(thumbnail_path):
                    os.remove(thumbnail_path)
        else:
            await message.answer("Извините, произошла ошибка. Видео недоступно!")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать аудио из #YouTube")
            await log_download(session, user_id, 'audio', link, status=False)
    elif state_info["command_type"] == 'reel':
        await message.answer("Подождите загружаю reels...")
        await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
        
        # Проверяем, нужен ли водяной знак
        add_wm = await should_add_watermark(session, user_id)
        
        try:
            path = await worker.download_instagram_reels(link)
        except Exception as e:
            logger.error(e)
            path = None
        if path:
            # Добавляем водяной знак если нужно
            final_path = worker.add_watermark_if_needed(path, add_wm)
            
            try:
                doc = await message.answer_video(video=FSInputFile(final_path), caption="Ваш reels готов!\n@django_media_helper_bot")
                await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #reels")
                await log_download(session, user_id, 'reels', link, status=True)
            except TelegramEntityTooLarge:
                logger.info("Обнаружен TelegramEntityTooLarge, переходим к отправке через API")
                width, height = worker.get_video_resolution_moviepy(final_path)
                sended = send_video_through_api(message.chat.id, final_path, width, height)
                if not sended:
                    await message.answer("Извините, размер файла слишком большой для отправки по Telegram.")
                    await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #reels, размер файла слишком большой")
                    await log_download(session, user_id, 'reels', link, status=False)
                else:
                    await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #reels")
                    await log_download(session, user_id, 'reels', link, status=True)
            except Exception as e:
                logger.error(f"Другая ошибка при отправке: {e}")
                await message.answer("Извините, произошла неизвестная ошибка при отправке видео.")
                await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #reels, {e}")
                await log_download(session, user_id, 'reels', link, status=False)
            finally:
                if os.path.isfile(final_path):
                    os.remove(final_path)
                if final_path != path and os.path.isfile(path):
                    os.remove(path)
        else:
            await message.answer("Произошла ошибка при загрузке reels. Попробуйте воспользоваться функцией позже.")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #reels")
            await log_download(session, user_id, 'reels', link, status=False)

    elif state_info["command_type"] == 'pinterest':
        await message.answer("Подождите загружаем видео...")
        await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
        
        # Проверяем, нужен ли водяной знак
        add_wm = await should_add_watermark(session, user_id)
        
        try:
            filename = pinterest.download_pin(link)
        except Exception as e:
            logger.error(e)
            filename = None
        if filename:
            video_path = f"./videos/pinterest/{filename}.mp4"
            # Добавляем водяной знак если нужно
            final_path = worker.add_watermark_if_needed(video_path, add_wm)
            
            try:
                doc = await message.answer_video(video=FSInputFile(final_path),
                                                    caption="Ваше видео готово!\n@django_media_helper_bot")
                await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #Pinterest")
                await log_download(session, user_id, 'pinterest', link, status=True)
                if doc:
                    if os.path.isfile(final_path):
                        os.remove(final_path)
                    if final_path != video_path and os.path.isfile(video_path):
                        os.remove(video_path)
            except Exception as e:
                logger.error(e)
                await log_download(session, user_id, 'pinterest', link, status=False)
                if os.path.isfile(final_path):
                    os.remove(final_path)
                if final_path != video_path and os.path.isfile(video_path):
                    os.remove(video_path)
        else:
            await message.answer("Извините, произошла ошибка. Видео недоступно, либо указана неверная ссылка!")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #Pinterest")
            await log_download(session, user_id, 'pinterest', link, status=False)

    elif state_info["command_type"] == 'tiktok':
        await message.answer("Подождите загружаем видео...")
        await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
        
        # Проверяем, нужен ли водяной знак
        add_wm = await should_add_watermark(session, user_id)
        
        tiktok_downloader = worker.TikTokDownloader("./videos/tiktok")
        try:
            filename = tiktok_downloader.download_video(link)
        except Exception as e:
            logger.error(e)
            filename = None
        if filename:
            video_path = f"./videos/tiktok/{filename}"
            # Добавляем водяной знак если нужно
            final_path = worker.add_watermark_if_needed(video_path, add_wm)
            
            try:
                doc = await message.answer_video(video=FSInputFile(final_path),
                                                    caption="Ваш tiktok готов!\n@django_media_helper_bot")
                await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #tiktok")
                await log_download(session, user_id, 'tiktok', link, status=True)
                if doc:
                    if os.path.isfile(final_path):
                        os.remove(final_path)
                    if final_path != video_path and os.path.isfile(video_path):
                        os.remove(video_path)
            except Exception as e:
                logger.error(e)
                await log_download(session, user_id, 'tiktok', link, status=False)
                if os.path.isfile(final_path):
                    os.remove(final_path)
                if final_path != video_path and os.path.isfile(video_path):
                    os.remove(video_path)
        else:
            await message.answer("Извините, произошла ошибка. Видео недоступно, либо указана неверная ссылка!")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #tiktok")
            await log_download(session, user_id, 'tiktok', link, status=False)

    await state.clear()

@router.message(VideoState.video)
async def process_video(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.content_type == ContentType.VIDEO:
        user_id = message.from_user.id
        username = message.from_user.username
        await message.answer("Видео получено. Извлекаем аудио...")
        await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VOICE)
        video_id = message.video.file_id
        video_name = message.video.file_name
        rev = video_name[::-1]
        tmp = rev.find('.')
        filename = rev[:tmp:-1]
        format = rev[tmp-1::-1]
        video_file = await message.bot.get_file(video_id)
        video_path = video_file.file_path  # Путь к загруженному видео
        os.makedirs("./videos/for_convert/", exist_ok=True)
        # Генерируем уникальное имя файла
        ind = 1
        while os.path.isfile(f"./videos/for_convert/{filename}.{format}"):
            filename = filename + f"({ind})"
            ind += 1
        await message.bot.download_file(video_path, f"./videos/for_convert/{filename}.{format}")
        video_path = f"./videos/for_convert/{filename}.{format}"
        filename = await worker.convert_to_audio(video_path, filename=filename)
        # Отправляем извлечённое аудио обратно пользователю
        doc = await message.answer_audio(audio=FSInputFile(f"./audio/converted/{filename}"), caption="Вот ваше аудио!\n@django_media_helper_bot")
        await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно извлек аудио #audio_cut")
        if doc:
            # Сохраняем аудио в БД для Mini App
            await save_sent_audio(session, doc, source='converted')
            if os.path.isfile(f"./audio/converted/{filename}"):
                os.remove(f"./audio/converted/{filename}")
            if os.path.isfile(f"{video_path}"):
                os.remove(f"{video_path}")
        await state.clear()
    else:
        await message.answer("Загрузите видео")

@router.message(MetaDataState.file)
async def process_metadata(message: Message, state: FSMContext) -> None:
    if message.content_type == ContentType.DOCUMENT:
        user_id = message.from_user.id
        username = message.from_user.username
        condition = message.document.mime_type.startswith('image/') \
            or message.document.mime_type.startswith('video/') \
            or message.document.mime_type.startswith('audio/')
        # Проверка на изображение, видео или аудио
        if condition:
            os.makedirs("./metadata/", exist_ok=True)
            file_id = message.document.file_id
            file_name = message.document.file_name
            rev = file_name[::-1]
            tmp = rev.find('.')
            filename = rev[:tmp:-1]
            format = rev[tmp-1::-1]
            file_tg = await message.bot.get_file(file_id)
            file_path = file_tg.file_path  # Путь к загруженному видео
            ind = 1
            while os.path.isfile(f"./metadata/{filename}.{format}"):
                filename = filename + f"({ind})"
                ind += 1
            await message.bot.download_file(file_path, f"./metadata/{filename}.{format}")
            file_path = f"./metadata/{filename}.{format}"
            print(file_path)
            meta = metadata.get_metadata(file_path)
            print(meta)
            if meta:
                strings = list(map(lambda x: f"{x}: {meta[x]}", meta.keys()))
                result = "\n".join(strings)
                result += "\n@django_media_helper_bot"
                await message.answer("Метаданные готовы, если их нет, значит у файла изначально их небыло")
                await message.answer(result)
                await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно извлек метаданные #meta")
                await state.clear()
            else:
                await message.answer("Произошла ошибка, возможно файл пока не поддерживается.")
                await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог извлечь метаданные #meta")
                await state.clear()
            if os.path.isfile(f"{file_path}"):
                os.remove(f"{file_path}")
        else:
            await message.answer("Отправьте фото, видео или аудио файлом!")

@router.message(SendAllState.message)
async def process_sendall(message: Message, session: AsyncSession, state: FSMContext) -> None:
    users = await db_commands.db_get_items(User, message, session)
    state_message = message.text
    for user in users:
        if user.tg_id != message.from_user.id:
            try:
                await message.bot.send_message(user.tg_id, state_message)
            except TelegramForbiddenError:
                continue
            except:
                continue
    await message.answer("Сообщение отправлено")
    await state.clear()

@router.message(ReplaceAudioState.video)
async def replace_audio_video(message: Message, state: FSMContext) -> None:
    if message.content_type == ContentType.VIDEO:
        await message.answer("Видео получено. Обрабатываем...")
        video_id = message.video.file_id
        video_name = message.video.file_name
        rev = video_name[::-1]
        tmp = rev.find('.')
        filename = rev[:tmp:-1]
        format = rev[tmp-1::-1]
        video_file = await message.bot.get_file(video_id)
        video_path = video_file.file_path  # Путь к загруженному видео
        os.makedirs("./videos/for_replace/", exist_ok=True)
        # Генерируем уникальное имя файла
        ind = 1
        while os.path.isfile(f"./videos/for_replace/{filename}.{format}"):
            filename = filename + f"({ind})"
            ind += 1
        filename = filename.strip()
        await message.bot.download_file(video_path, f"./videos/for_replace/{filename}.{format}")
        video_path = f"./videos/for_replace/{filename}.{format}"
        await state.update_data(video=video_path)
        await message.answer("Теперь отправь аудио.")
        await state.set_state(ReplaceAudioState.audio)
    else:
        await message.answer("Отправьте видео.")

@router.message(ReplaceAudioState.audio)
async def replace_audio_audio(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    username = message.from_user.username
    cond1 = message.content_type == ContentType.DOCUMENT and message.document.mime_type.startswith('audio/')
    cond2 = message.content_type == ContentType.AUDIO
    if cond1:
        context =  message.document
    else:
        context = message.audio
    if cond1 or cond2:
        await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
        await message.answer("Аудио получено. Обрабатываем...")
        os.makedirs("./audio/for_replace/", exist_ok=True)
        audio_id = context.file_id
        audio_name = context.file_name
        rev = audio_name[::-1]
        tmp = rev.find('.')
        filename = rev[:tmp:-1]
        format = rev[tmp-1::-1]
        audio_tg = await message.bot.get_file(audio_id)
        audio_path = audio_tg.file_path  # Путь к загруженному видео
        ind = 1
        while os.path.isfile(f"./audio/for_replace/{filename}.{format}"):
            filename = filename + f"({ind})"
            ind += 1
        filename = filename.strip()
        await message.bot.download_file(audio_path, f"./audio/for_replace/{filename}.{format}")
        audio_path = f"./audio/for_replace/{filename}.{format}"
        await state.update_data(audio=audio_path)
        data = await state.get_data()
        result_path = worker.replace_audio(data.get('video'), data.get('audio'))
        if result_path:
            await message.answer_video(video=FSInputFile(result_path), caption="Ваше видео готово!\n@django_media_helper_bot")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно заменил аудио в видео #replace_audio")
            if os.path.isfile(result_path):
                os.remove(result_path)
        else:
            await message.answer("Произошла ошибка, повторите попытку позже.")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог заменить аудио в видео #replace_audio")
        if os.path.isfile(data['video']):
            os.remove(data['video'])
        if os.path.isfile(data['audio']):
            os.remove(data['audio'])
        await state.clear()
    else:
        await message.answer("Отправьте аудио.")

@router.message(AnswerState.tg_id)
async def process_tg_id(message: Message, state: FSMContext) -> None:
    await state.update_data(tg_id = message.text)
    await message.answer("Отправьте сообщение пользователю")
    await state.set_state(AnswerState.message)


@router.message(AnswerState.message)
async def process_answer(message: Message, state: FSMContext) -> None:
    await state.update_data(message = message.text)
    state_info = await state.get_data()
    try:
        await message.bot.send_message(state_info['tg_id'], state_info['message'])
        await message.answer("Сообщение успешно отправлено пользователю")
    except TelegramForbiddenError:
        await message.answer("Пользователь заблокировал бота")
    await state.clear()


@router.message(Command("cancel"))
@router.message(F.text.casefold() == "отмена")
async def cancel_handler(message: Message, state: FSMContext):
    """Отмена текущего действия с очисткой состояния"""
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.clear()
    await message.answer("Действие отменено. Начните заново с /start", reply_markup=None)


@router.message(Command("reset"))
async def reset_handler(message: Message, state: FSMContext):
    """Полный сброс состояния"""
    await state.clear()
    await message.answer("✅ Состояние сброшено. Начните новый поиск.")


# ============================================
# Синхронизация аудио для Mini App
# ============================================

@router.message(Command("sync"))
async def sync_audio_handler(message: Message, session: AsyncSession):
    """
    Команда для синхронизации аудио с Mini App.
    Показывает инструкцию по синхронизации.
    """
    keyboard = [
        [InlineKeyboardButton(text="📱 Открыть плеер", web_app={"url": config.MINI_APP_URL})]
    ] if hasattr(config, 'MINI_APP_URL') and config.MINI_APP_URL else []
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    await message.answer(
        "🔄 **Синхронизация аудио с плеером**\n\n"
        "Чтобы добавить ваши существующие аудио в плеер Mini App:\n\n"
        "1️⃣ Перейдите в чат со мной\n"
        "2️⃣ Найдите аудио, которые хотите добавить\n"
        "3️⃣ **Перешлите** их мне (Forward)\n\n"
        "Я автоматически добавлю каждый трек в вашу библиотеку.\n\n"
        "💡 Можно пересылать несколько аудио за раз!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


@router.message(F.text)
async def handle_search_query(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка поискового запроса"""

    # Очищаем предыдущие данные перед новым поиском
    await state.update_data(
        search_results=None,
        current_video=None,
        video_formats=None
    )

    query = message.text
    user_id = message.from_user.id
    username = message.from_user.username
    # Проверяем, не является ли сообщение YouTube ссылкой
    if "youtube.com" in query or "youtu.be" in query:
        await handle_youtube_link(message, state, session)
        return

    # tiktok.com, www.tiktok.com, m.tiktok.com, vm.tiktok.com, vt.tiktok.com
    if re.search(r"(?:^|\.)(tiktok\.com)$", query) or any(d in query for d in ("tiktok.com", "vm.tiktok.com", "vt.tiktok.com")):
        await handle_tiktok_link(message, session)
        return

    # домены: instagram.com, www.instagram.com, instagram.reel (rare), i.instagram.com
    if "instagram.com" in query or "i.instagram.com" in query or "instagr.am" in query:
        await handle_instagram_link(message, session)
        return

    # домены: pinterest.com, www.pinterest.com, pin.it (short)
    if "pinterest.com" in query or "pin.it" in query:
        await handle_pinterest_link(message, session)
        return

    await message.answer("🔍 Ищу видео...")

    # Выполняем поиск
    results = worker.search_videos(query)
    if not results:
        await message.answer("❌ По вашему запросу ничего не найдено.")
        await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) искал: {query}, но не смог ничего найти. из #YouTube")
        return

    # Сохраняем результаты в состоянии
    await state.update_data(search_results=results, search_query=query)

    # Создаем клавиатуру с результатами
    keyboard = []
    for i, video in enumerate(results, 1):
        title = video['title']
        if len(title) > 35:
            title = title[:32] + "..."
            
        keyboard.append([
            InlineKeyboardButton(
                text=f"{i}. {title}",
                callback_data=f"select_{i-1}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await message.answer(
        "🔍 **Найденные видео:**\n\nВыберите видео из списка:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

    await state.set_state(YoutubeSearchState.select_action)


@router.callback_query(F.data.startswith("select_"), YoutubeSearchState.select_action)
async def handle_video_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора видео из списка"""
    choice_index = int(callback.data.split("_")[1])
    
    # Получаем данные из состояния
    data = await state.get_data()
    results = data.get('search_results', [])
    
    if not results or choice_index >= len(results):
        await callback.message.edit_text("❌ Ошибка: видео не найдено.")
        return
    
    # Сохраняем выбранное видео
    selected_video = results[choice_index]
    await state.update_data(selected_video=selected_video)
    
    # Создаем клавиатуру действий
    keyboard = [
        [
            InlineKeyboardButton(text="◀️ Назад к списку", callback_data="back_to_list"),
            InlineKeyboardButton(text="🎵 Скачать аудио", callback_data="download_audio"),
        ],
        [
            InlineKeyboardButton(text="🎥 Скачать видео", callback_data="download_video"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Редактируем сообщение
    await callback.message.edit_text(
        f"🎬 **Выбрано:** {selected_video['title']}\n"
        f"📺 Канал: {selected_video['channel']}\n"
        f"⏱ Длительность: {selected_video['duration']}\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    await callback.answer()


@router.callback_query(F.data == "back_to_list", YoutubeSearchState.select_action)
async def handle_back_to_list(callback: CallbackQuery, state: FSMContext):
    """Возврат к списку результатов"""
    data = await state.get_data()
    results = data.get('search_results', [])
    
    # Создаем клавиатуру с результатами
    keyboard = []
    for i, video in enumerate(results, 1):
        title = video['title']
        if len(title) > 35:
            title = title[:32] + "..."
            
        keyboard.append([
            InlineKeyboardButton(
                text=f"{i}. {title}",
                callback_data=f"select_{i-1}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "🔍 **Найденные видео:**\n\nВыберите видео из списка:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    await callback.answer()


@router.callback_query(F.data == "download_audio", YoutubeSearchState.select_action)
async def handle_download_audio(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработка загрузки аудио"""
    try:
        await callback.answer()
    except TelegramBadRequest as e:
        logger.warning(f"Can't answer callback_query (may be expired): {e}")
    except Exception as e:
        logger.exception(f"Unexpected error while answering callback_query: {e}")

    data = await state.get_data()
    selected_video = data.get('selected_video')

    user_id = callback.from_user.id
    username = callback.from_user.username

    if not selected_video:
        await callback.message.edit_text("❌ Ошибка: видео не выбрано.")
        await state.clear()  # Очищаем состояние при ошибке
        return
    
    video_id = selected_video['id']
    
    # Меняем сообщение на "загрузка"
    await callback.message.edit_text(
        f"⏬ Загружаю аудио...\n\n"
        f"🎬 {selected_video['title']}\n"
        "Пожалуйста, подождите ⏳"
    )
    
    # Загружаем аудио
    link = f"https://www.youtube.com/watch?v={video_id}"
    await callback.bot.send_chat_action(callback.message.chat.id, ChatAction.UPLOAD_VOICE)
    try:
        result = await worker.get_audio_from_youtube(link)
    except Exception as e:
        logger.error(e)
        result = None    
    if result:
        filename = result['audio']
        thumbnail_path = result.get('thumbnail')
        try:
            # Подготавливаем thumbnail если есть
            thumbnail = FSInputFile(thumbnail_path) if thumbnail_path and os.path.isfile(thumbnail_path) else None
            
            doc = await callback.message.answer_audio(
                audio=FSInputFile(f"./audio/youtube/{filename}"),
                thumbnail=thumbnail,
                caption="Ваше аудио готово!\n@django_media_helper_bot"
            )
            await callback.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) искал: {data.get('search_query', '')} и успешно скачал аудио из #YouTube")
            await log_download(session, user_id, 'audio', link, status=True)
            # Сохраняем аудио в БД для Mini App
            if doc:
                await save_sent_audio(session, doc, source='youtube', source_url=link)
        except TelegramEntityTooLarge:
            logger.info("Обнаружен TelegramEntityTooLarge, переходим к отправке через API")
            api_result = send_audio_through_api(
                callback.message.chat.id, 
                f"./audio/youtube/{filename}",
                thumbnail_path=thumbnail_path,
                delete_after=True
            )
            if not api_result['success']:
                await callback.message.edit_text("Извините, размер файла слишком большой для отправки по Telegram.")
                await callback.message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) искал: {data.get('search_query', '')}, но не смог скачать аудио из #YouTube, размер файла слишком большой")
                await log_download(session, user_id, 'audio', link, status=False)
            else:
                await callback.message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) искал: {data.get('search_query', '')} и успешно скачал аудио из #YouTube")
                await log_download(session, user_id, 'audio', link, status=True)
                # Сохраняем аудио в БД для Mini App
                if api_result['response']:
                    await save_audio_from_api_response(session, user_id, api_result['response'], source='youtube', source_url=link)
        except Exception as e:
            logger.error(f"Другая ошибка при отправке: {e}")
            await callback.message.edit_text("Извините, произошла неизвестная ошибка при отправке аудио.")
            await callback.message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) искал: {data.get('search_query', '')}, но не смог скачать аудио из #YouTube, {e}")
            await log_download(session, user_id, 'audio', link, status=False)
        finally:
            # Удаляем аудио файл
            if os.path.isfile(f"./audio/youtube/{filename}"):
                os.remove(f"./audio/youtube/{filename}")
            # Удаляем thumbnail
            if thumbnail_path and os.path.isfile(thumbnail_path):
                os.remove(thumbnail_path)
    else:
        await callback.message.edit_text("Извините, произошла ошибка. Видео недоступно!")
        await callback.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) искал: {data.get('search_query', '')}, но не смог скачать аудио из #YouTube")
        await log_download(session, user_id, 'audio', link, status=False)
    
    await state.clear()


@router.callback_query(F.data == "download_video", YoutubeSearchState.select_action)
async def handle_download_video(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработка выбора загрузки видео - показ форматов"""
    user_id = callback.from_user.id
    username = callback.from_user.username or str(user_id)
    
    data = await state.get_data()
    selected_video = data.get('selected_video')
    
    if not selected_video:
        await callback.message.edit_text("❌ Ошибка: видео не выбрано.")
        return
    
    video_id = selected_video['id']
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Получаем доступные форматы
    await callback.message.edit_text("🔄 Получаю доступные форматы...")
    
    formats = worker.get_video_formats(video_id)
    
    if not formats:
        await callback.message.edit_text("❌ Не удалось получить форматы для этого видео.")
        await log_download(session, user_id, 'youtube', link=youtube_url, status=False)
        try:
            await callback.bot.send_message(
                chat_id=config.DEV_CHANEL_ID,
                text=f"❌ @{username} (ID: {user_id}) не смог получить форматы для видео: {selected_video.get('title', video_id)} #YouTube #error"
            )
        except Exception:
            pass
        return
    
    # Создаем клавиатуру с форматами
    keyboard = []
    for i, fmt in enumerate(formats, 1):
        keyboard.append([
            InlineKeyboardButton(
                text=f"{i}. {fmt['resolution']} ({fmt['format_note']}) - {fmt['filesize']}",
                callback_data=f"format_{fmt['format_id']}"
            )
        ])
    
    # Добавляем кнопку "Назад"
    keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_actions")
    ])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        f"🎬 **{selected_video['title']}**\n\n"
        "📹 **Доступные форматы:**\n"
        "Выберите качество видео:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    await state.set_state(YoutubeSearchState.select_format)
    await callback.answer()


@router.callback_query(F.data.startswith("format_"), YoutubeSearchState.select_format)
async def handle_format_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработка выбора формата видео"""
    try:
        await callback.answer()
    except TelegramBadRequest as e:
        logger.warning(f"Can't answer callback_query (may be expired): {e}")
    except Exception as e:
        logger.exception(f"Unexpected error while answering callback_query: {e}")

    format_id = callback.data.split("_")[1]

    user_id = callback.from_user.id
    username = callback.from_user.username
    
    data = await state.get_data()
    selected_video = data.get('selected_video')
    
    if not selected_video:
        await callback.message.edit_text("❌ Ошибка: видео не выбрано.")
        await state.clear()
        return
    
    link = f"https://www.youtube.com/watch?v={selected_video['id']}"
    
    # Меняем сообщение на "загрузка"
    await callback.message.edit_text(
        f"⏬ Загружаю видео...\n\n"
        f"🎬 {selected_video['title']}\n"
        "Пожалуйста, подождите ⏳"
    )
    
    # Загружаем видео
    try:
        filename = await worker.download_from_youtube(link, format_id=format_id)
    except Exception as e:
        logger.error(e)
        filename = None
    if filename:
        width, height = worker.get_video_resolution_moviepy(f"./videos/youtube/{filename}")
        file_size = os.path.getsize(f"./videos/youtube/{filename}")
        logger.info(f"Размер файла: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
        try:
            doc = await callback.message.bot.send_video(callback.message.chat.id, FSInputFile(f"./videos/youtube/{filename}"), caption='Ваше видео готово!\n@django_media_helper_bot', supports_streaming=True, width=width, height=height)
            await callback.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) искал: {data.get('search_query', '')} и успешно скачал видео из #YouTube")
            await log_download(session, user_id, 'youtube', link, status=True)
            if not doc:
                await callback.message.edit_text("Извините, произошла ошибка. Видео недоступно, либо указана неверная ссылка!")
                await callback.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) искал: {data.get('search_query', '')}, но не смог скачать видео из #YouTube")
        except TelegramEntityTooLarge:
            logger.info("Обнаружен TelegramEntityTooLarge, переходим к отправке через API")
            sended = send_video_through_api(callback.message.chat.id, f"./videos/youtube/{filename}", width, height)
            if not sended:
                await callback.message.edit_text("Извините, размер файла слишком большой для отправки по Telegram.")
                await callback.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) искал: {data.get('search_query', '')}, но не смог скачать видео из #YouTube, размер файла слишком большой")
                await log_download(session, user_id, 'youtube', link, status=False)
            else:
                await callback.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) искал: {data.get('search_query', '')} и успешно скачал видео из #YouTube")
                await log_download(session, user_id, 'youtube', link, status=True)
        except Exception as e:
            logger.error(f"Другая ошибка при отправке: {e}")
            await callback.message.edit_text("Извините, произошла неизвестная ошибка при отправке видео.")
            await log_download(session, user_id, 'youtube', link, status=False)
        finally:
            if os.path.isfile(f"./videos/youtube/{filename}"):
                os.remove(f"./videos/youtube/{filename}")
    else:
        await callback.message.edit_text("Извините, произошла ошибка. Видео недоступно, либо указана неверная ссылка!")
        await callback.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) искал: {data.get('search_query', '')}, но не смог скачать видео из #YouTube")
        await log_download(session, user_id, 'youtube', link, status=False)
        try:
            if os.path.isfile(f"./videos/youtube/{filename}"):
                os.remove(f"./videos/youtube/{filename}")
        except Exception as e:
            logger.error(e)
    
    await state.clear()


@router.callback_query(F.data == "back_to_actions", YoutubeSearchState.select_format)
async def handle_back_to_actions(callback: CallbackQuery, state: FSMContext):
    """Возврат к действиям после выбора видео"""
    data = await state.get_data()
    selected_video = data.get('selected_video', {})

    # Создаем клавиатуру действий
    keyboard = [
        [
            InlineKeyboardButton(text="◀️ Назад к списку", callback_data="back_to_list"),
            InlineKeyboardButton(text="🎵 Скачать аудио", callback_data="download_audio"),
        ],
        [
            InlineKeyboardButton(text="🎥 Скачать видео", callback_data="download_video"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await callback.message.edit_text(
        f"🎬 **Выбрано:** {selected_video.get('title', 'Неизвестно')}\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

    await state.set_state(YoutubeSearchState.select_action)
    await callback.answer()



# ============================================
# Распознавание музыки (Shazam)
# ============================================

def escape_markdown(text: str) -> str:
    """Экранирует спецсимволы Markdown"""
    if not text:
        return text
    for char in ['_', '*', '`', '[', ']', '(', ')']:
        text = text.replace(char, f'\\{char}')
    return text


@router.message(F.voice)
async def handle_voice_recognition(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработчик голосовых сообщений для распознавания музыки.
    Пользователь отправляет голосовое с отрывком песни — бот распознаёт и предлагает скачать.
    """
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    voice_path = None
    
    # Очищаем предыдущее состояние чтобы избежать конфликтов
    await state.clear()
    
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    status_msg = await message.reply("🎵 Распознаю музыку...")
    
    try:
        # Скачиваем голосовое сообщение
        voice = message.voice
        voice_file = await message.bot.get_file(voice.file_id)
        
        os.makedirs("./audio/recognition/", exist_ok=True)
        voice_path = f"./audio/recognition/{user_id}_{voice.file_unique_id}.ogg"
        await message.bot.download_file(voice_file.file_path, voice_path)
        
        # Распознаём музыку
        recognized = await worker.recognize_music(voice_path)
        
        if not recognized:
            await status_msg.edit_text(
                "❌ Не удалось распознать музыку.\n\n"
                "Попробуйте:\n"
                "• Записать более чёткий отрывок\n"
                "• Убедиться, что музыка хорошо слышна\n"
                "• Записать хотя бы 5-10 секунд"
            )
            try:
                await message.bot.send_message(
                    chat_id=config.DEV_CHANEL_ID,
                    text=f"❌ @{username} (ID: {user_id}) не смог распознать музыку из голосового #shazam #error"
                )
            except Exception:
                pass
            return
        
        # Формируем сообщение с результатом (экранируем спецсимволы)
        title = recognized['title']
        artist = recognized['artist']
        album = recognized.get('album') or ''
        year = recognized.get('year') or ''
        
        title_escaped = escape_markdown(title)
        artist_escaped = escape_markdown(artist)
        album_escaped = escape_markdown(album)
        
        info_parts = [f"🎵 *{title_escaped}*", f"👤 {artist_escaped}"]
        if album:
            info_parts.append(f"💿 {album_escaped}")
        if year:
            info_parts.append(f"📅 {year}")
        
        # Кнопки действий
        keyboard = [
            [InlineKeyboardButton(text="⬇️ Скачать трек", callback_data="shazam_download")]
        ]
        
        # Добавляем ссылки если есть
        links_row = []
        if recognized.get('shazam_url'):
            links_row.append(InlineKeyboardButton(text="🎧 Shazam", url=recognized['shazam_url']))
        if recognized.get('spotify_url'):
            # Конвертируем spotify:track:xxx в https URL
            spotify_uri = recognized['spotify_url']
            if spotify_uri.startswith('spotify:track:'):
                track_id = spotify_uri.split(':')[-1]
                links_row.append(InlineKeyboardButton(text="🟢 Spotify", url=f"https://open.spotify.com/track/{track_id}"))
        
        if links_row:
            keyboard.append(links_row)
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Сохраняем данные для скачивания
        await state.update_data(
            shazam_result=recognized,
            shazam_query=recognized['youtube_query']
        )
        await state.set_state(ShazamState.confirm_download)
        
        # Отправляем результат с обложкой если есть
        if recognized.get('cover_url'):
            try:
                await status_msg.delete()
                await message.answer_photo(
                    photo=recognized['cover_url'],
                    caption="\n".join(info_parts),
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception:
                # Если не получилось отправить фото — отправляем текст
                await status_msg.edit_text(
                    "\n".join(info_parts),
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        else:
            await status_msg.edit_text(
                "\n".join(info_parts),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        # Логируем в dev канал (игнорируем ошибки)
        try:
            await message.bot.send_message(
                chat_id=config.DEV_CHANEL_ID,
                text=f"🎵 @{username} (ID: {user_id}) распознал: {artist} - {title} #shazam"
            )
        except Exception:
            pass
        
    except Exception as e:
        logger.error(f"Error in voice recognition: {e}")
        try:
            await status_msg.edit_text("❌ Произошла ошибка при распознавании. Попробуйте позже.")
        except Exception:
            pass
        try:
            await message.bot.send_message(
                chat_id=config.DEV_CHANEL_ID,
                text=f"❌ @{username} (ID: {user_id}) ошибка при распознавании голосового: {str(e)[:100]} #shazam #error"
            )
        except Exception:
            pass
    finally:
        # Гарантированно удаляем временный файл
        if voice_path and os.path.isfile(voice_path):
            try:
                os.remove(voice_path)
            except Exception:
                pass


@router.message(F.video | F.video_note)
async def handle_video_recognition(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработчик видео для распознавания музыки.
    Пользователь отправляет видео — бот извлекает аудио, распознаёт и предлагает скачать.
    """
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    video_path = None
    audio_path = None
    
    # Очищаем предыдущее состояние чтобы избежать конфликтов
    await state.clear()
    
    # Получаем видео (video или video_note)
    video = message.video or message.video_note
    if not video:
        return
    
    # Ограничение на размер файла (50 МБ)
    if video.file_size and video.file_size > 50 * 1024 * 1024:
        await message.reply(
            "❌ Видео слишком большое.\n"
            "Максимальный размер для распознавания: 50 МБ"
        )
        return
    
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    status_msg = await message.reply("🎵 Извлекаю аудио и распознаю музыку...")
    
    try:
        # Скачиваем видео
        video_file = await message.bot.get_file(video.file_id)
        
        os.makedirs("./audio/recognition/", exist_ok=True)
        video_path = f"./audio/recognition/{user_id}_{video.file_unique_id}.mp4"
        await message.bot.download_file(video_file.file_path, video_path)
        
        # Извлекаем аудио из видео через ffmpeg
        audio_path = f"./audio/recognition/{user_id}_{video.file_unique_id}.ogg"
        
        ffmpeg_cmd = [
            'ffmpeg', '-i', video_path,
            '-vn',  # Без видео
            '-acodec', 'libopus',
            '-b:a', '128k',
            '-y',  # Перезаписывать
            audio_path
        ]
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode != 0 or not os.path.isfile(audio_path):
            await status_msg.edit_text("❌ Не удалось извлечь аудио из видео")
            try:
                await message.bot.send_message(
                    chat_id=config.DEV_CHANEL_ID,
                    text=f"❌ @{username} (ID: {user_id}) не удалось извлечь аудио из видео #shazam_video #error"
                )
            except Exception:
                pass
            return
        
        # Удаляем видео сразу после извлечения аудио
        if video_path and os.path.isfile(video_path):
            try:
                os.remove(video_path)
                video_path = None
            except Exception:
                pass
        
        # Распознаём музыку
        recognized = await worker.recognize_music(audio_path)
        
        if not recognized:
            await status_msg.edit_text(
                "❌ Не удалось распознать музыку в видео.\n\n"
                "Попробуйте:\n"
                "• Видео с более громкой музыкой\n"
                "• Видео без посторонних звуков\n"
                "• Более длинный отрывок (5-10 секунд)"
            )
            try:
                await message.bot.send_message(
                    chat_id=config.DEV_CHANEL_ID,
                    text=f"❌ @{username} (ID: {user_id}) не смог распознать музыку из видео #shazam_video #error"
                )
            except Exception:
                pass
            return
        
        # Формируем сообщение с результатом (экранируем спецсимволы)
        title = recognized['title']
        artist = recognized['artist']
        album = recognized.get('album') or ''
        year = recognized.get('year') or ''
        
        title_escaped = escape_markdown(title)
        artist_escaped = escape_markdown(artist)
        album_escaped = escape_markdown(album)
        
        info_parts = [f"🎵 *{title_escaped}*", f"👤 {artist_escaped}"]
        if album:
            info_parts.append(f"💿 {album_escaped}")
        if year:
            info_parts.append(f"📅 {year}")
        
        # Кнопки действий
        keyboard = [
            [InlineKeyboardButton(text="⬇️ Скачать трек", callback_data="shazam_download")]
        ]
        
        # Добавляем ссылки если есть
        links_row = []
        if recognized.get('shazam_url'):
            links_row.append(InlineKeyboardButton(text="🎧 Shazam", url=recognized['shazam_url']))
        if recognized.get('spotify_url'):
            # Конвертируем spotify:track:xxx в https URL
            spotify_uri = recognized['spotify_url']
            if spotify_uri.startswith('spotify:track:'):
                track_id = spotify_uri.split(':')[-1]
                links_row.append(InlineKeyboardButton(text="🟢 Spotify", url=f"https://open.spotify.com/track/{track_id}"))
        
        if links_row:
            keyboard.append(links_row)
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Сохраняем данные для скачивания
        await state.update_data(
            shazam_result=recognized,
            shazam_query=recognized['youtube_query']
        )
        await state.set_state(ShazamState.confirm_download)
        
        # Отправляем результат с обложкой если есть
        if recognized.get('cover_url'):
            try:
                await status_msg.delete()
                await message.answer_photo(
                    photo=recognized['cover_url'],
                    caption="\n".join(info_parts),
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception:
                # Если не получилось отправить фото — отправляем текст
                await status_msg.edit_text(
                    "\n".join(info_parts),
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        else:
            await status_msg.edit_text(
                "\n".join(info_parts),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        # Логируем в dev канал (игнорируем ошибки)
        try:
            await message.bot.send_message(
                chat_id=config.DEV_CHANEL_ID,
                text=f"🎬 @{username} (ID: {user_id}) распознал из видео: {artist} - {title} #shazam_video"
            )
        except Exception:
            pass
        
    except Exception as e:
        logger.error(f"Error in video recognition: {e}")
        try:
            await status_msg.edit_text("❌ Произошла ошибка при распознавании. Попробуйте позже.")
        except Exception:
            pass
        try:
            await message.bot.send_message(
                chat_id=config.DEV_CHANEL_ID,
                text=f"❌ @{username} (ID: {user_id}) ошибка при распознавании видео: {str(e)[:100]} #shazam_video #error"
            )
        except Exception:
            pass
    finally:
        # Гарантированно удаляем временные файлы
        for path in [video_path, audio_path]:
            if path and os.path.isfile(path):
                try:
                    os.remove(path)
                except Exception:
                    pass


@router.callback_query(F.data == "shazam_download", ShazamState.confirm_download)
async def handle_shazam_download(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Скачать распознанный трек"""
    user_id = callback.from_user.id
    username = callback.from_user.username or str(user_id)
    file_path = None
    thumbnail_path = None
    status_msg = None
    
    data = await state.get_data()
    recognized = data.get('shazam_result')
    query = data.get('shazam_query')
    
    if not recognized or not query:
        await callback.answer("❌ Данные устарели, попробуйте заново", show_alert=True)
        await state.clear()
        return
    
    await callback.answer("⏳ Ищу и скачиваю...")
    
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    
    status_msg = await callback.message.reply("🔍 Ищу на YouTube...")
    
    try:
        # Ищем на YouTube
        search_results = worker.search_videos(query, max_results=1)
        
        if not search_results:
            await status_msg.edit_text("❌ Не удалось найти трек на YouTube")
            await log_download(session, user_id, 'audio', link=None, status=False)
            try:
                await callback.message.bot.send_message(
                    chat_id=config.DEV_CHANEL_ID,
                    text=f"❌ @{username} (ID: {user_id}) не смог найти трек через Shazam: {query} #shazam_download #error"
                )
            except Exception:
                pass
            await state.clear()
            return
        
        video = search_results[0]
        youtube_url = f"https://www.youtube.com/watch?v={video['id']}"
        
        await status_msg.edit_text("⬇️ Скачиваю...")
        
        # Скачиваем аудио
        result = await worker.get_audio_from_youtube(youtube_url)
        
        if not result or not result.get('audio'):
            await status_msg.edit_text("❌ Не удалось скачать трек")
            await log_download(session, user_id, 'audio', link=youtube_url, status=False)
            try:
                await callback.message.bot.send_message(
                    chat_id=config.DEV_CHANEL_ID,
                    text=f"❌ @{username} (ID: {user_id}) не смог скачать трек через Shazam #shazam_download #error"
                )
            except Exception:
                pass
            await state.clear()
            return
        
        filename = result['audio']
        thumbnail_path = result.get('thumbnail')
        file_path = f"./audio/youtube/{filename}"
        
        await status_msg.edit_text("📤 Отправляю...")
        
        # Формируем caption
        caption = (
            f"🎵 {recognized['artist']} - {recognized['title']}\n"
            f"@django_media_helper_bot"
        )
        
        # Отправляем аудио с правильными метаданными
        file_size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
        
        if file_size < 50 * 1024 * 1024:  # < 50MB
            doc = await callback.message.answer_audio(
                audio=FSInputFile(file_path),
                title=recognized['title'],
                performer=recognized['artist'],
                thumbnail=FSInputFile(thumbnail_path) if thumbnail_path and os.path.isfile(thumbnail_path) else None,
                caption=caption
            )
            
            # Сохраняем в библиотеку (source_url сохранит ссылку на YouTube)
            await save_sent_audio(session, doc, source='youtube', source_url=youtube_url)
            await log_download(session, user_id, 'audio', link=youtube_url, status=True)
        else:
            # Большой файл — через локальный API
            api_result = send_audio_through_api(
                user_id,
                file_path,
                thumbnail_path=thumbnail_path,
                delete_after=False
            )
            
            if api_result['success']:
                await save_audio_from_api_response(session, user_id, api_result['response'], source='youtube', source_url=youtube_url)
                await log_download(session, user_id, 'audio', link=youtube_url, status=True)
                await callback.message.answer(caption)
            else:
                await log_download(session, user_id, 'audio', link=youtube_url, status=False)
                await callback.message.answer("❌ Не удалось отправить файл")
                try:
                    await callback.message.bot.send_message(
                        chat_id=config.DEV_CHANEL_ID,
                        text=f"❌ @{username} (ID: {user_id}) не смог отправить большой файл через Shazam #shazam_download #error"
                    )
                except Exception:
                    pass
        
        try:
            await status_msg.delete()
        except Exception:
            pass
        
        # Логируем в dev канал (игнорируем ошибки)
        try:
            await callback.message.bot.send_message(
                chat_id=config.DEV_CHANEL_ID,
                text=f"✅ @{username} (ID: {user_id}) скачал через Shazam: {recognized['artist']} - {recognized['title']} #shazam_download"
            )
        except Exception:
            pass
        
    except Exception as e:
        logger.error(f"Error downloading shazam track: {e}")
        try:
            if status_msg:
                await status_msg.edit_text("❌ Произошла ошибка при скачивании")
        except Exception:
            pass
        try:
            await log_download(session, user_id, 'audio', link=None, status=False)
        except Exception:
            pass
        try:
            await callback.message.bot.send_message(
                chat_id=config.DEV_CHANEL_ID,
                text=f"❌ @{username} (ID: {user_id}) ошибка при скачивании через Shazam: {str(e)[:100]} #shazam_download #error"
            )
        except Exception:
            pass
    finally:
        # Гарантированно очищаем state и удаляем файлы
        await state.clear()
        
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


@router.message(F.audio)
async def handle_forwarded_audio(message: Message, session: AsyncSession):
    """
    Обработчик для пересланных или отправленных аудио.
    Сохраняет аудио в библиотеку пользователя для Mini App.
    """
    audio = message.audio
    
    if not audio:
        return
    
    # Определяем источник
    if message.forward_from or message.forward_from_chat:
        source = "forwarded"
    else:
        source = "uploaded"
    
    try:
        # Сохраняем аудио в базу
        saved_audio = await save_sent_audio(
            session=session,
            message=message,
            source=source,
            source_url=None
        )
        
        if saved_audio:
            title = audio.title or audio.file_name or "Без названия"
            artist = audio.performer or "Неизвестный исполнитель"
            
            await message.reply(
                f"✅ Добавлено в библиотеку:\n\n"
                f"🎵 {title}\n"
                f"👤 {artist}",
                parse_mode='Markdown'
            )
        else:
            # Аудио уже было в библиотеке
            await message.reply("ℹ️ Этот трек уже есть в вашей библиотеке.")
            
    except Exception as e:
        logger.error(f"Error saving forwarded audio: {e}")
        await message.reply("❌ Не удалось добавить трек. Попробуйте позже.")
