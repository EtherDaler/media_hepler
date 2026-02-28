import worker
import logging
import os
import pinterest

from aiogram.types import Message, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.enums.chat_action import ChatAction
from aiogram.exceptions import TelegramEntityTooLarge
from aiogram.utils.markdown import escape_md
from sqlalchemy.ext.asyncio import AsyncSession

from data import config
from db.download_log import log_download, should_add_watermark


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def handle_instagram_link(message: Message, session: AsyncSession):
    await message.answer("Подождите загружаю reels...")
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
    link = message.text
    username = message.from_user.username
    user_id = message.from_user.id
    
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
            await message.answer_video(video=FSInputFile(final_path), caption="Ваш reels готов!\n@django_media_helper_bot")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #reels напрямую")
            # Логируем успешную загрузку
            await log_download(session, user_id, 'reels', link, status=True)
        except TelegramEntityTooLarge:
            logger.info("Обнаружен TelegramEntityTooLarge, переходим к отправке через API")
            from bot_commands import send_video_through_api
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
            # Удаляем оригинал если он отличается от финального
            if final_path != path and os.path.isfile(path):
                os.remove(path)
    else:
        await message.answer("Произошла ошибка при загрузке reels. Попробуйте воспользоваться функцией позже.")
        await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #reels напрямую")
        await log_download(session, user_id, 'reels', link, status=False)


def is_youtube_shorts(url: str) -> bool:
    """Проверяет, является ли ссылка YouTube Shorts"""
    return '/shorts/' in url


async def handle_youtube_shorts(message: Message, session: AsyncSession):
    """Обработка YouTube Shorts — сразу скачиваем без выбора качества"""
    await message.answer("⏳ Загружаю Shorts...")
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
    
    url = message.text
    username = message.from_user.username
    user_id = message.from_user.id
    
    # Проверяем, нужен ли водяной знак
    add_wm = await should_add_watermark(session, user_id)
    
    try:
        video_filename = await worker.download_from_youtube(url)
        
        if video_filename:
            video_path = f"./videos/youtube/{video_filename}"
            # Добавляем водяной знак если нужно
            final_path = worker.add_watermark_if_needed(video_path, add_wm)
            
            try:
                await message.answer_video(
                    video=FSInputFile(final_path),
                    caption="Ваш Shorts готов!\n@django_media_helper_bot"
                )
                await message.bot.send_message(
                    chat_id=config.DEV_CHANEL_ID,
                    text=f"Пользователь @{username} (ID: {user_id}) успешно скачал #shorts"
                )
                await log_download(session, user_id, 'shorts', url, status=True)
            except TelegramEntityTooLarge:
                await message.answer_document(
                    document=FSInputFile(final_path),
                    caption="Ваш Shorts готов!\n@django_media_helper_bot"
                )
                await log_download(session, user_id, 'shorts', url, status=True)
            finally:
                if os.path.isfile(final_path):
                    os.remove(final_path)
                if final_path != video_path and os.path.isfile(video_path):
                    os.remove(video_path)
        else:
            await message.answer("❌ Не удалось скачать Shorts.")
            await log_download(session, user_id, 'shorts', url, status=False)
            
    except Exception as e:
        logger.error(f"Ошибка скачивания Shorts: {e}")
        await message.answer("❌ Произошла ошибка при скачивании Shorts.")
        await log_download(session, user_id, 'shorts', url, status=False)


async def handle_youtube_link(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка прямой YouTube ссылки"""
    url = message.text
    
    # Если это Shorts — обрабатываем отдельно
    if is_youtube_shorts(url):
        await handle_youtube_shorts(message, session)
        return
    
    from bot_commands import YoutubeSearchState
    
    # Получаем информацию о видео
    try:
        video_info = worker.get_youtube_video_info(url)
        
        # Проверяем, что video_info не None
        if video_info is None:
            logger.error(f"get_youtube_video_info вернул None для URL: {url}")
            await message.answer("❌ Не удалось получить информацию о видео. Возможно, видео недоступно или требует авторизации.")
            username = message.from_user.username
            user_id = message.from_user.id
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог получить инфо о видео (None)")
            return

        # Сохраняем выбранное видео
        await state.update_data(selected_video=video_info)

        # Показываем действия для этого видео
        keyboard = [
            [
                InlineKeyboardButton(text="🎵 Скачать аудио", callback_data="download_audio"),
                InlineKeyboardButton(text="🎥 Скачать видео", callback_data="download_video"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        title = escape_md(video_info['title'])
        channel = escape_md(video_info['channel'])
        duration = escape_md(video_info['duration'])

        await message.answer(
            f"🎬 *Найдено видео:*\n{title}\n\n"
            f"📺 Канал: {channel}\n"
            f"⏱ Длительность: {duration}\n\n"
            "Выберите действие:",
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )

        await state.set_state(YoutubeSearchState.select_action)
   
    except Exception as e:
        logger.error(f"Ошибка обработки ссылки: {e}")
        await message.answer("❌ Не удалось обработать ссылку.")
        username = message.from_user.username
        user_id = message.from_user.id
        await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог обработать ссылку: {url}")


async def handle_tiktok_link(message: Message, session: AsyncSession):
    await message.answer("Подождите загружаем видео...")
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
    link = message.text
    username = message.from_user.username
    user_id = message.from_user.id
    
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
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #tiktok напрямую")
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
        await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #tiktok напрямую")
        await log_download(session, user_id, 'tiktok', link, status=False)


async def handle_pinterest_link(message: Message, session: AsyncSession):
    await message.answer("Подождите загружаем видео...")
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
    link = message.text
    username = message.from_user.username
    user_id = message.from_user.id
    
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
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #Pinterest напрямую")
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
        await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #Pinterest напрямую")
        await log_download(session, user_id, 'pinterest', link, status=False)
