import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot_commands import router as media_router
from middlewares import DbSessionMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from data import config


async def main() -> None:
    TOKEN = config.BOT_TOKEN
    bot = Bot(TOKEN.strip(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    engine = create_async_engine(url=config.DB_PATH, echo=True)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    dp.update.middleware(DbSessionMiddleware(session_pool=sessionmaker))

    dp.include_router(media_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
