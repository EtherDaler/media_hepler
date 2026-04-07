"""Админ-команды бота (отдельный Router)."""

import io
import logging

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from sqlalchemy.ext.asyncio import AsyncSession

from db import db_commands
from db.download_log import get_today_stats
from data import config
from models import User
import yt_cookie_utils

admin_router = Router(name="admin")

logger = logging.getLogger(__name__)

MAX_YT_COOKIE_UPLOAD_BYTES = 3 * 1024 * 1024


def _is_env_super_admin(user_id: int) -> bool:
    """Только tg_id из ADMINS в .env."""
    return str(user_id) in config.ADMINS


class SendAllState(StatesGroup):
    message = State()


class AnswerState(StatesGroup):
    tg_id = State()
    message = State()


class CookieUpdateState(StatesGroup):
    waiting_file = State()


class NotSlashCommandFilter(BaseFilter):
    """Текст не является командой (/...), чтобы /cancel обрабатывался глобально."""

    async def __call__(self, message: Message) -> bool:
        text = (message.text or "").strip()
        if not text:
            return True
        return not text.startswith("/")


@admin_router.message(Command("count_users"))
async def count_users(message: Message, session: AsyncSession) -> None:
    user = await db_commands.get_item(User, "tg_id", message.from_user.id, message, session)
    if user is not None:
        if user.is_admin:
            users = await db_commands.db_get_items(User, message, session)
            await message.answer(f"Количесвто пользователей, использующих бот: {len(users)}")
        else:
            await message.answer("У вас нет прав!")
    else:
        await message.answer("У вас нет прав!")


@admin_router.message(Command("stats"))
async def stats_command(message: Message, session: AsyncSession) -> None:
    """Статистика загрузок за сегодня (только для админов)"""
    user = await db_commands.get_item(User, "tg_id", message.from_user.id, message, session)
    if user is None or not user.is_admin:
        await message.answer("У вас нет прав!")
        return

    stats = await get_today_stats(session)

    platform_icons = {
        "youtube": "🎬",
        "shorts": "📱",
        "reels": "📸",
        "tiktok": "🎵",
        "pinterest": "📌",
        "audio": "🎧",
        "instagram": "📷",
    }

    text = "📊 **Статистика за сегодня**\n\n"

    text += f"👥 DAU (уникальных пользователей): **{stats['dau']}**\n"
    text += f"📥 Всего загрузок: **{stats['total_downloads']}**\n"
    text += f"❌ Ошибок: **{stats['errors']}**\n\n"

    if stats["by_platform"]:
        text += "📈 **По платформам:**\n"
        for platform, count in sorted(stats["by_platform"].items(), key=lambda x: x[1], reverse=True):
            icon = platform_icons.get(platform, "📦")
            text += f"  {icon} {platform}: {count}\n"
        text += "\n"
    else:
        text += "📈 Загрузок пока нет\n\n"

    if stats["top_users"]:
        text += "🏆 **Топ 3 пользователя:**\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, (user_id, count) in enumerate(stats["top_users"]):
            medal = medals[i] if i < len(medals) else f"{i + 1}."
            text += f"  {medal} ID: `{user_id}` — {count} загрузок\n"

    await message.answer(text, parse_mode="Markdown")


@admin_router.message(Command("grant_admin"))
async def command_grant_admin(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    if not _is_env_super_admin(message.from_user.id):
        await message.answer("Эта команда доступна только главному администратору.")
        return
    if not command.args:
        await message.answer("Использование: /grant_admin <tg_id>")
        return
    try:
        target_id = int(command.args.strip().split()[0])
    except ValueError:
        await message.answer("tg_id должен быть целым числом.")
        return
    ok, err = await db_commands.grant_admin_by_tg_id(target_id, message, session)
    if ok:
        await message.answer(
            f"Пользователю `{target_id}` выданы права администратора.", parse_mode="Markdown"
        )
    else:
        await message.answer(err or "Не удалось выдать права.")


@admin_router.message(Command("revoke_admin"))
async def command_revoke_admin(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    if not _is_env_super_admin(message.from_user.id):
        await message.answer("Эта команда доступна только главному администратору.")
        return
    if not command.args:
        await message.answer("Использование: /revoke_admin <tg_id>")
        return
    try:
        target_id = int(command.args.strip().split()[0])
    except ValueError:
        await message.answer("tg_id должен быть целым числом.")
        return
    ok, err = await db_commands.revoke_admin_by_tg_id(target_id, message, session)
    if ok:
        extra = ""
        if str(target_id) in config.ADMINS:
            extra = (
                "\n\nПримечание: этот tg_id указан в ADMINS в .env — команды главного админа "
                "для него останутся доступны, пока он в списке ADMINS."
            )
        await message.answer(
            f"У пользователя `{target_id}` сняты права администратора в базе.{extra}",
            parse_mode="Markdown",
        )
    else:
        await message.answer(err or "Не удалось снять права.")


@admin_router.message(Command("update_yt_cookies"))
async def command_update_yt_cookies(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    user = await db_commands.get_item(User, "tg_id", message.from_user.id, message, session)
    if user is None or not user.is_admin:
        await message.answer("У вас нет прав.")
        return
    if not config.DEFAULT_YT_COOKIE:
        await message.answer(
            "В .env не задан путь DEFAULT_YT_COOKIE — некуда записывать cookies."
        )
        return
    await state.set_state(CookieUpdateState.waiting_file)
    await message.answer(
        "Пришлите **документом** текстовый файл `.txt` с cookies YouTube "
        "(формат Netscape, например из расширения «Get cookies.txt LOCALLY»).\n"
        "Другие типы файлов не принимаются. /cancel — отмена.",
        parse_mode="Markdown",
    )


@admin_router.message(CookieUpdateState.waiting_file, F.document)
async def cookie_update_receive_document(message: Message, state: FSMContext) -> None:
    doc = message.document
    if not doc:
        await message.answer("Отправьте файл как документ (не как сжатое фото).")
        return
    name = (doc.file_name or "").lower()
    if not name.endswith(".txt"):
        await message.answer("Нужен файл с расширением .txt")
        return
    mime = (doc.mime_type or "").lower()
    if mime and mime not in (
        "text/plain",
        "application/octet-stream",
        "text/x-plain",
    ):
        await message.answer("Ожидается текстовый файл (.txt).")
        return
    if doc.file_size and doc.file_size > MAX_YT_COOKIE_UPLOAD_BYTES:
        await message.answer("Файл слишком большой.")
        return

    path = config.DEFAULT_YT_COOKIE
    if not path:
        await state.clear()
        await message.answer("DEFAULT_YT_COOKIE не настроен.")
        return

    buf = io.BytesIO()
    try:
        await message.bot.download(doc, destination=buf)
    except Exception as e:
        logger.exception("download cookie file: %s", e)
        await message.answer("Не удалось получить файл из Telegram.")
        return

    raw = buf.getvalue()
    if len(raw) > MAX_YT_COOKIE_UPLOAD_BYTES:
        await message.answer("Файл слишком большой.")
        return
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        await message.answer("Файл должен быть в кодировке UTF-8.")
        return

    ok, err = yt_cookie_utils.validate_netscape_youtube_cookies(text)
    if not ok:
        await message.answer(f"Ошибка проверки cookies: {err}")
        return

    try:
        yt_cookie_utils.write_cookie_file_atomic(path, text)
    except OSError as e:
        logger.exception("write cookies: %s", e)
        await message.answer(f"Не удалось записать файл: {e}")
        return

    await state.clear()
    await message.answer(f"Файл cookies обновлён: `{path}`", parse_mode="Markdown")


@admin_router.message(CookieUpdateState.waiting_file, NotSlashCommandFilter())
async def cookie_update_wrong_kind(message: Message) -> None:
    await message.answer(
        "Отправьте один текстовый файл `.txt` с cookies (как **документ**). "
        "Или /cancel для отмены."
    )


@admin_router.message(Command("send_all"))
async def send_all(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await db_commands.get_item(User, "tg_id", message.from_user.id, message, session)
    if user is not None:
        if user.is_admin:
            await message.answer("Напишите сообщение")
            await state.set_state(SendAllState.message)
        else:
            await message.answer("У вас нет прав!")
    else:
        await message.answer("У вас нет прав!")


@admin_router.message(Command("answer"))
async def answer(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await db_commands.get_item(User, "tg_id", message.from_user.id, message, session)
    if user is not None:
        if user.is_admin:
            await message.answer("Укажите tg_id пользователя")
            await state.set_state(AnswerState.tg_id)
        else:
            await message.answer("У вас нет прав!")
    else:
        await message.answer("У вас нет прав!")


@admin_router.message(SendAllState.message, F.text)
async def process_sendall(message: Message, session: AsyncSession, state: FSMContext) -> None:
    users = await db_commands.db_get_items(User, message, session)
    state_message = message.text
    for user in users:
        if user.tg_id != message.from_user.id:
            try:
                await message.bot.send_message(user.tg_id, state_message)
            except TelegramForbiddenError:
                continue
            except Exception:
                continue
    await message.answer("Сообщение отправлено")
    await state.clear()


@admin_router.message(SendAllState.message)
async def process_sendall_non_text(message: Message) -> None:
    await message.answer("Нужно отправить текстовое сообщение (не стикер и не фото).")


@admin_router.message(AnswerState.tg_id, F.text)
async def process_tg_id(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    try:
        target_id = int(raw)
    except ValueError:
        await message.answer("tg_id должен быть числом (например: 123456789). Попробуйте снова.")
        return
    await state.update_data(tg_id=target_id)
    await message.answer("Отправьте сообщение пользователю")
    await state.set_state(AnswerState.message)


@admin_router.message(AnswerState.tg_id)
async def process_tg_id_non_text(message: Message) -> None:
    await message.answer("Отправьте tg_id одним числом текстом.")


@admin_router.message(AnswerState.message, F.text)
async def process_answer(message: Message, state: FSMContext) -> None:
    await state.update_data(message=message.text)
    state_info = await state.get_data()
    chat_id = state_info["tg_id"]
    try:
        await message.bot.send_message(chat_id, state_info["message"])
        await message.answer("Сообщение успешно отправлено пользователю")
    except TelegramForbiddenError:
        await message.answer("Пользователь заблокировал бота")
    except TelegramBadRequest as e:
        await message.answer(f"Не удалось отправить (проверьте tg_id): {e}")
    await state.clear()


@admin_router.message(AnswerState.message)
async def process_answer_non_text(message: Message) -> None:
    await message.answer("Нужно текстовое сообщение.")
