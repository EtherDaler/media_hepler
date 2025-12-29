import worker
import logging
import os
import pinterest

from aiogram.types import Message, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.enums.chat_action import ChatAction
from aiogram.exceptions import TelegramEntityTooLarge

from data import config


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def handle_instagram_link(message: Message):
    await message.answer("Подождите загружаю reels...")
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
    link = message.text
    username = message.from_user.username
    user_id = message.from_user.id
    try:
        path = await worker.download_instagram_reels(link)
    except Exception as e:
        logger.error(e)
        path = None
    if path:
        #reencoded_path = worker.reencode_video(path)
        try:
            await message.answer_video(video=FSInputFile(path), caption="Ваш reels готов!\n@django_media_helper_bot")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #reels напрямую")
        except TelegramEntityTooLarge:
            logger.info("Обнаружен TelegramEntityTooLarge, переходим к отправке через API")
            # Локальный импорт чтобы избежать циклического импорта
            from bot_commands import send_video_through_api
            width, height = worker.get_video_resolution_moviepy(path)
            sended = send_video_through_api(message.chat.id, path, width, height)
            if not sended:
                await message.answer("Извините, размер файла слишком большой для отправки по Telegram.")
                await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #reels, размер файла слишком большой")
            else:
                await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #reels")
        except Exception as e:
            logger.error(f"Другая ошибка при отправке: {e}")
            await message.answer("Извините, произошла неизвестная ошибка при отправке видео.")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #reels, {e}")
        finally:
            #if os.path.isfile(reencoded_path):
            #    os.remove(reencoded_path)
            if os.path.isfile(path):
                os.remove(path)
    else:
        await message.answer("Произошла ошибка при загрузке reels. Попробуйте воспользоваться функцией позже.")
        await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #reels напрямую")


def is_youtube_shorts(url: str) -> bool:
    """Проверяет, является ли ссылка YouTube Shorts"""
    return '/shorts/' in url


async def handle_youtube_shorts(message: Message):
    """Обработка YouTube Shorts — сразу скачиваем без выбора качества"""
    await message.answer("⏳ Загружаю Shorts...")
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
    
    url = message.text
    username = message.from_user.username
    user_id = message.from_user.id
    
    try:
        # Скачиваем Shorts как обычное видео
        video_filename = await worker.download_from_youtube(url)
        
        if video_filename:
            video_path = f"./videos/youtube/{video_filename}"
            try:
                await message.answer_video(
                    video=FSInputFile(video_path),
                    caption="Ваш Shorts готов!\n@django_media_helper_bot"
                )
                await message.bot.send_message(
                    chat_id=config.DEV_CHANEL_ID,
                    text=f"Пользователь @{username} (ID: {user_id}) успешно скачал #shorts"
                )
            except TelegramEntityTooLarge:
                await message.answer_document(
                    document=FSInputFile(video_path),
                    caption="Ваш Shorts готов!\n@django_media_helper_bot"
                )
            finally:
                if os.path.isfile(video_path):
                    os.remove(video_path)
        else:
            await message.answer("❌ Не удалось скачать Shorts.")
            
    except Exception as e:
        logger.error(f"Ошибка скачивания Shorts: {e}")
        await message.answer("❌ Произошла ошибка при скачивании Shorts.")


async def handle_youtube_link(message: Message, state: FSMContext):
    """Обработка прямой YouTube ссылки"""
    url = message.text
    
    # Если это Shorts — обрабатываем отдельно
    if is_youtube_shorts(url):
        await handle_youtube_shorts(message)
        return
    
    from bot_commands import YoutubeSearchState
    
    # Получаем информацию о видео
    try:
        video_info = worker.get_youtube_video_info(url)

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

        await message.answer(
            f"🎬 **Найдено видео:** {video_info['title']}\n"
            f"📺 Канал: {video_info['channel']}\n"
            f"⏱ Длительность: {video_info['duration']}\n\n"
            "Выберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        await state.set_state(YoutubeSearchState.select_action)
   
    except Exception as e:
        logger.error(f"Ошибка обработки ссылки: {e}")
        await message.answer("❌ Не удалось обработать ссылку.")


async def handle_tiktok_link(message: Message):
    await message.answer("Подождите загружаем видео...")
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
    link = message.text
    username = message.from_user.username
    user_id = message.from_user.id
    tiktok_downloader = worker.TikTokDownloader("./videos/tiktok")
    try:
        filename = tiktok_downloader.download_video(link)
    except Exception as e:
        logger.error(e)
        filename = None
    if filename:
        try:
            doc = await message.answer_video(video=FSInputFile(f"./videos/tiktok/{filename}"),
                                                caption="Ваш tiktok готов!\n@django_media_helper_bot")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #tiktok напрямую")
            if doc:
                if os.path.isfile(f"./videos/tiktok/{filename}"):
                    os.remove(f"./videos/tiktok/{filename}")
        except Exception as e:
            logger.error(e)
            if os.path.isfile(f"./videos/tiktok/{filename}"):
                os.remove(f"./videos/tiktok/{filename}")
    else:
        await message.answer("Извините, произошла ошибка. Видео недоступно, либо указана неверная ссылка!")
        await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #tiktok напрямую")
        if os.path.isfile(f"./videos/tiktok/{filename}"):
            os.remove(f"./videos/tiktok/{filename}")


async def handle_pinterest_link(message: Message):
    await message.answer("Подождите загружаем видео...")
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
    link = message.text
    username = message.from_user.username
    user_id = message.from_user.id
    try:
        filename = pinterest.download_pin(link)
    except Exception as e:
        logger.error(e)
        filename = None
    if filename:
        doc = await message.answer_video(video=FSInputFile(f"./videos/pinterest/{filename}.mp4"),
                                            caption="Ваше видео готово!\n@django_media_helper_bot")
        await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #Pinterest напрямую")
        if doc:
            if os.path.isfile(f"./videos/pinterest/{filename}.mp4"):
                os.remove(f"./videos/pinterest/{filename}.mp4")
    else:
        await message.answer("Извините, произошла ошибка. Видео недоступно, либо указана неверная ссылка!")
        await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #Pinterest напрямую")
        if os.path.isfile(f"./videos/pinterest/{filename}.mp4"):
            os.remove(f"./videos/pinterest/{filename}.mp4")
