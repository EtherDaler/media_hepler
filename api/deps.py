"""Зависимости FastAPI"""

import hashlib
import hmac
import json
from typing import Optional
from urllib.parse import unquote, parse_qsl

from fastapi import HTTPException, Header, Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from data.config import DB_PATH, BOT_TOKEN


# Database setup
engine = create_async_engine(DB_PATH, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Получить сессию БД"""
    async with async_session_maker() as session:
        yield session


def validate_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """
    Валидация Telegram WebApp initData.
    Возвращает распарсенные данные или вызывает исключение.
    """
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        
        if 'hash' not in parsed:
            raise ValueError("Missing hash")
        
        received_hash = parsed.pop('hash')
        
        # Сортируем ключи и формируем data-check-string
        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )
        
        # Вычисляем secret_key = HMAC-SHA256(bot_token, "WebAppData")
        secret_key = hmac.new(
            bot_token.encode(),  # key
            b"WebAppData",       # message
            hashlib.sha256
        ).digest()
        
        # Проверяем auth_date (не старше 24 часов)
        import time
        auth_date = int(parsed.get('auth_date', 0))
        if time.time() - auth_date > 86400:
            raise ValueError("Auth data expired")
        
        # Вычисляем hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(calculated_hash, received_hash):
            raise ValueError("Invalid hash")
        
        # Парсим user data
        if 'user' in parsed:
            parsed['user'] = json.loads(unquote(parsed['user']))
        
        return parsed
        
    except Exception as e:
        raise ValueError(f"Invalid init data: {e}")


async def get_current_user(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data")
) -> dict:
    """
    Получить текущего пользователя из Telegram initData.
    Для разработки можно использовать X-Dev-User-Id заголовок.
    """
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    # Для разработки: если строка начинается с "dev:", используем test user
    if x_telegram_init_data.startswith("dev:"):
        user_id = int(x_telegram_init_data.split(":")[1])
        return {
            "id": user_id,
            "first_name": "Developer",
            "is_dev": True
        }
    
    try:
        data = validate_telegram_init_data(x_telegram_init_data, BOT_TOKEN)
        user = data.get('user', {})
        if not user or 'id' not in user:
            raise HTTPException(status_code=401, detail="Invalid user data")
        return user
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


def get_user_id(user: dict = Depends(get_current_user)) -> int:
    """Получить ID текущего пользователя"""
    return user['id']

