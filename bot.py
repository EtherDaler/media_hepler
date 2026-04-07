import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from admin_commands import admin_router
from bot_commands import router as media_router
from inline_commands import inline_router
from middlewares import DbSessionMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from data import config


async def _check_db_connection():
    """Проверка подключения к БД при старте. Выводит понятное сообщение при ошибке."""
    from sqlalchemy import text
    engine = create_async_engine(url=config.DB_PATH, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except ConnectionRefusedError as e:
        raise SystemExit(
            f"\n[ОШИБКА] PostgreSQL недоступен: {e}\n"
            f"Проверьте на сервере:\n"
            f"  1. Запущен ли PostgreSQL: systemctl status postgresql\n"
            f"  2. Слушает ли порт 5432: ss -tlnp | grep 5432\n"
            f"  3. В .env указаны: DB_HOST={config.DB_HOST} DB_PORT={config.DB_PORT}\n"
            f"Если используете managed БД (Neon, Supabase и т.д.) — задайте DB_HOST на хост провайдера.\n"
        ) from e
    except Exception as e:
        if "connect" in str(e).lower() or "connection" in str(e).lower():
            raise SystemExit(
                f"\n[ОШИБКА] Не удалось подключиться к БД: {e}\n"
                f"Проверьте .env: DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME\n"
            ) from e
        raise
    finally:
        await engine.dispose()


async def main() -> None:
    TOKEN = config.BOT_TOKEN
    bot = Bot(TOKEN.strip(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    await _check_db_connection()

    engine = create_async_engine(url=config.DB_PATH, echo=True)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    dp.update.middleware(DbSessionMiddleware(session_pool=sessionmaker))

    dp.include_router(admin_router)
    dp.include_router(media_router)
    dp.include_router(inline_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
