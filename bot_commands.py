import json

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder


router = Router()

@router.message(CommandStart())
async def command_start_handler(message: Message, session: AsyncSession) -> None:
    """
    This handler receives messages with `/start` command
    """
    status = True
    user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
    if user is None:
        status = await db_commands.db_register_user(message, session)
        if status:
            user = await db_commands.get_item(User, 'tg_id', message.from_user.id, message, session)
        else:
            await message.answer("Произошла ошибка, повторите попытку позже!")
    if status:
        file = "texts/command_start.txt"
        if user.lang == 'tj':
            file = "texts/command_start_tj.txt"
        elif user.lang == 'uz':
            file = "texts/command_start_uz.txt"
        with open(file, "r", encoding="utf-8") as f:
            command_start_text = f.read()
            await message.answer(command_start_text.format(message.from_user.full_name))