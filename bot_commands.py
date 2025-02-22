import os
import worker
import metadata
import logging
import pinterest
import requests

from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, ContentType, ReplyKeyboardRemove, InputFile, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramEntityTooLarge, TelegramForbiddenError
from aiogram.enums.chat_action import ChatAction

from sqlalchemy.ext.asyncio import AsyncSession
from db import db_commands
from data import config
from models import User
from fake_useragent import UserAgent


router = Router()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
BOT_TOKEN = config.BOT_TOKEN


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
    
    # Проверяем существование файла
    if not os.path.isfile(file_path):
        logger.error(f"Файл {file_path} не найден.")
        return False

    # Отправка запроса
    try:
        with open(file_path, 'rb') as video:
            files = {'video': video}
            data = {
                'chat_id': chat_id,
                'caption': 'Ваше видео готово!\n@django_media_helper_bot',
                'width': width,
                'height': height
            }
            response = requests.post(url, data=data, files=files)
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
async def get_link(message: Message, state: FSMContext) -> None:
    await state.update_data(link = message.text)
    state_info = await state.get_data()
    link = state_info['link']
    user_id = message.from_user.id
    username = message.from_user.username
    if state_info["command_type"] == 'video':
        await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
        await message.answer("Подождите загружаем видео...")
        filename = await worker.download_from_youtube(link)
        if filename:
            width, height = worker.get_video_resolution_moviepy(f"./videos/youtube/{filename}")
            try:
                #reencoded_path = worker.reencode_video(f"./videos/youtube/{filename}")
                #doc = await message.answer_video(video=video_file, caption='Ваше видео готово!\n@django_media_helper_bot')
                doc = await message.bot.send_video(message.chat.id, FSInputFile(f"./videos/youtube/{filename}"), caption='Ваше видео готово!\n@django_media_helper_bot', supports_streaming=True, width=width, height=height)
                #doc = await message.answer_document(document=FSInputFile(f"./videos/youtube/{filename}"), caption="Ваше видео готово!\n@django_media_helper_bot")
                await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #YouTube")
                if not doc:
                    await message.answer("Извините, произошла ошибка. Видео недоступно, либо указана неверная ссылка!")
                    await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #YouTube")
            except TelegramEntityTooLarge:
                sended = send_video_through_api(message.chat.id, f"./videos/youtube/{filename}", width, height)
                if not sended:
                    await message.answer("Извините, размер файла слишком большой для отправки по Telegram.")
                    await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #YouTube, размер файла слишком большой")
                else:
                    await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #YouTube")
            except Exception as e:
                logger.error(e)
            finally:
                if os.path.isfile(f"./videos/youtube/{filename}"):
                    os.remove(f"./videos/youtube/{filename}")
        else:
            await message.answer("Извините, произошла ошибка. Видео недоступно, либо указана неверная ссылка!")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #YouTube")
            try:
                if os.path.isfile(f"./videos/youtube/{filename}"):
                    os.remove(f"./videos/youtube/{filename}")
            except Exception as e:
                logger.error(e)

    elif state_info["command_type"] == 'audio':
        await message.answer("Подождите загружаем аудио...")
        await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VOICE)
        filename = await worker.get_audio_from_youtube(link)
        if filename:
            try:
                doc = await message.answer_document(document=FSInputFile(f"./audio/youtube/{filename}"), caption="Ваше аудио готово!\n@django_media_helper_bot")
                await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал аудио из #YouTube")
            except TelegramEntityTooLarge:
                await message.answer("Извините, размер файла слишком большой для отправки по Telegram.")
                await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать аудио из #YouTube, размер файла слишком большой")
            if os.path.isfile(f"./audio/youtube/{filename}"):
                os.remove(f"./audio/youtube/{filename}")
        else:
            await message.answer("Извините, произошла ошибка. Видео недоступно!")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать аудио из #YouTube")
    elif state_info["command_type"] == 'reel':
        await message.answer("Подождите загружаем reels...")
        await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
        path = worker.download_instagram_reels(link)
        if path:
            reencoded_path = worker.reencode_video(path)
            doc = await message.answer_document(document=FSInputFile(reencoded_path), caption="Ваш reels готов!\n@django_media_helper_bot")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #reels")
            if doc:
                if os.path.isfile(reencoded_path):
                    os.remove(reencoded_path)
        else:
            await message.answer("Произошла ошибка при загрузке reels. Попробуйте воспользоваться функцией позже.")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #reels")
        try:            
            if os.path.isfile(path):
                os.remove(path)
        except Exception as e:
            print(e)

    elif state_info["command_type"] == 'pinterest':
        await message.answer("Подождите загружаем видео...")
        await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_VIDEO)
        filename = pinterest.download_pin(link)
        if filename:
            doc = await message.answer_document(document=FSInputFile(f"./videos/pinterest/{filename}.mp4"),
                                                caption="Ваше видео готово!\n@django_media_helper_bot")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно скачал видео из #Pinterest")
            if doc:
                if os.path.isfile(f"./videos/pinterest/{filename}.mp4"):
                    os.remove(f"./videos/pinterest/{filename}.mp4")
        else:
            await message.answer("Извините, произошла ошибка. Видео недоступно, либо указана неверная ссылка!")
            await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) не смог скачать видео из #Pinterest")
            if os.path.isfile(f"./videos/pinterest/{filename}.mp4"):
                os.remove(f"./videos/pinterest/{filename}.mp4")
    await state.clear()

@router.message(VideoState.video)
async def process_video(message: Message, state: FSMContext) -> None:
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
        doc = await message.answer_document(document=FSInputFile(f"./audio/converted/{filename}"), caption="Вот ваше аудио!\n@django_media_helper_bot")
        await message.bot.send_message(chat_id=config.DEV_CHANEL_ID, text=f"Пользователь @{username} (ID: {user_id}) успешно извлек аудио #audio_cut")
        if doc:
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
            await message.answer_document(document=FSInputFile(result_path), caption="Ваше видео готово!\n@django_media_helper_bot")
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
@router.message(F.text.casefold() == "cancel")
async def cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("Cancelling state %r", current_state)
    data = await state.get_data()
    if 'video' in data.keys():
        if os.path.isfile(data['video']):
                os.remove(data['video'])
    if 'audio' in data.keys():
        if os.path.isfile(data['audio']):
                os.remove(data['audio'])
    await state.clear()
    await message.answer(
        "Cancelled.",
        reply_markup=ReplyKeyboardRemove(),
    )
