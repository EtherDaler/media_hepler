import os
import worker

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


router = Router()


class YoutubeState(StatesGroup):
    link = State()
    command_type = State()

class VideoState(StatesGroup):
    video = State() 

@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    file = "./texts/start_text.txt"
    with open(file, "r", encoding="utf-8") as f:
        command_start_text = f.read()
        await message.answer(command_start_text.format(message.from_user.full_name))

@router.message(Command("youtube_video"))
async def command_youtube_video(message: Message, state: FSMContext) -> None:
    await state.update_data(command_type="video")
    await message.answer("Отправь мне ссылку на видео")
    await state.set_state(YoutubeState.link)

@router.message(Command("youtube_audio"))
async def command_youtube_audio(message: Message, state: FSMContext) -> None:
    await state.update_data(command_type="audio")
    await message.answer("Отправь мне ссылку на видео")
    await state.set_state(YoutubeState.link)

@router.message(Command("convert_to_audio"))
async def command_youtube_audio(message: Message, state: FSMContext) -> None:
    await message.answer("Отправь мне видео")
    await state.set_state(VideoState.video)

@router.message(YoutubeState.link)
async def get_link(message: Message, state: FSMContext) -> None:
    await state.update_data(link = message.text)
    state_info = await state.get_data()
    link = state_info['link']
    if state_info["command_type"] == 'video':
        await message.answer("Подождите загружаем видео...")
        filename = await worker.download_from_youtube(link)
        doc = await message.answer_document(document=FSInputFile(f"./videos/youtube/{filename}"), caption="Ваше видео готово!")
        if doc:
            if os.path.isfile(f"./videos/youtube/{filename}"):
                os.remove(f"./videos/youtube/{filename}")

    else:
        await message.answer("Подождите загружаем аудио...")
        filename = await worker.get_audio_from_youtube(link)
        doc = await message.answer_document(document=FSInputFile(f"./audio/youtube/{filename}"), caption="Ваше аудио готово!")
        if doc:
            if os.path.isfile(f"./audio/youtube/{filename}"):
                os.remove(f"./audio/youtube/{filename}")
    await state.finish()

@router.message(VideoState.video, content_types=ContentType.VIDEO)
async def process_video(message: Message, state: FSMContext) -> None:
    video_file = await message.video.download()  # Загружаем видео
    video_path = video_file.name  # Путь к загруженному видео
    await message.answer("Видео получено. Извлекаем аудио...")

    filename = await worker.convert_to_audio(video_path)
    # Отправляем извлечённое аудио обратно пользователю
    doc = await message.answer_audio(audio=open(f"./audio/converted/{filename}", 'rb'), caption="Вот ваше аудио!")
    if doc:
        if os.path.isfile(f"./audio/converted/{filename}"):
            os.remove(f"./audio/converted/{filename}")
        if os.path.isfile(f"{video_path}"):
            os.remove(f"{video_path}")
    await state.finish()