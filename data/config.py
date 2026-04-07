import os

from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.environ.get("TOKEN")
DB_NAME = os.environ.get("DB_NAME", "media_helper")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_PATH = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def check_db_config() -> list[str]:
    """Проверка наличия обязательных параметров БД. Возвращает список ошибок."""
    errors = []
    if not DB_NAME or not DB_USER:
        errors.append("DB_NAME и DB_USER должны быть заданы в .env")
    return errors

# Список tg_id главных админов (из .env ADMINS через пробел). Только они могут выдавать/забирать админку в БД.
_raw_admins = os.environ.get("ADMINS") or ""
ADMINS = [x.strip() for x in _raw_admins.split() if x.strip()]

DEV_CHANEL_ID = os.environ.get("DEV_CHANEL_ID")

PROXYS = os.environ.get("PROXY", "[]")
SIMPLE_PROXY = os.environ.get("SIMPLE_PROXY")
DEFAULT_YT_COOKIE = os.environ.get("DEFAULT_YT_COOKIE")

# Mini App URL (для кнопки в боте)
MINI_APP_URL = os.environ.get("MINI_APP_URL")

# Имя бота без @ для deep link t.me/<username>?start=... (импорт из Mini App)
BOT_USERNAME = (os.environ.get("BOT_USERNAME") or "").strip().lstrip("@")
DAILY_VIDEO_LIMIT = int(os.environ.get("DAILY_VIDEO_LIMIT", 10))

# YouTube PO Token (для обхода age-restriction без cookies)
# Получить можно через DevTools или расширение браузера
YT_PO_TOKEN = os.environ.get("YT_PO_TOKEN")
YT_VISITOR_DATA = os.environ.get("YT_VISITOR_DATA")

# Локальный Bot API (для больших файлов), например http://127.0.0.1:8081
LOCAL_BOT_API_URL = os.environ.get("LOCAL_BOT_API_URL", "").rstrip("/")