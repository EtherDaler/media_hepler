import worker
import logging
import os
import pinterest

from aiogram.types import Message, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.enums.chat_action import ChatAction

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
        path = worker.download_instagram_reels(link)
    except Exception as e:
        logger.error(e)
        filename = None
    if path:
        reencoded_path = worker.reencode_video(path)
        doc = await message.answer_document(document=FSInputFile(reencoded_path), caption="Ваш reels готов!\n@django_media_helper_bot")
        await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #reels напрямую")
        if doc:
            if os.path.isfile(reencoded_path):
                os.remove(reencoded_path)
    else:
        await message.answer("Произошла ошибка при загрузке reels. Попробуйте воспользоваться функцией позже.")
        await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #reels напрямую")
    try:            
        if os.path.isfile(path):
            os.remove(path)
    except Exception as e:
        print(e)


async def handle_youtube_link(message: Message, state: FSMContext):
    """Обработка прямой YouTube ссылки"""
    from bot_commands import YoutubeSearchState
    url = message.text
    video_id = worker.extract_video_id(url)
    
    if not video_id:
        await message.answer("❌ Неверная ссылка на YouTube.")
        return
    
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
            doc = await message.answer_document(document=FSInputFile(f"./videos/tiktok/{filename}"),
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
        doc = await message.answer_document(document=FSInputFile(f"./videos/pinterest/{filename}.mp4"),
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
