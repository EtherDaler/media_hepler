import os
from typing import List

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

# Авто-PO (bgutil-ytdlp-pot-provider): pip install + HTTP-сервер рядом с воркером.
# https://github.com/Brainicism/bgutil-ytdlp-pot-provider
# Явный URL провайдера (перекрывает дефолт ниже):
BGUTIL_POT_BASE_URL = (os.environ.get("BGUTIL_POT_BASE_URL") or "").strip().rstrip("/")
# Если BGUTIL_POT_BASE_URL пустой, подставляется этот адрес (по умолчанию локальный bgutil).
DEFAULT_BGUTIL_POT_HTTP = (os.environ.get("DEFAULT_BGUTIL_POT_HTTP") or "http://127.0.0.1:4416").strip().rstrip("/")
# 1 / true — не передавать bgutil в yt-dlp (если сервер не запущен — иначе будут ошибки подключения к POT)
BGUTIL_DISABLE = (os.environ.get("BGUTIL_DISABLE") or "").strip().lower() in ("1", "true", "yes", "on")

# yt-dlp --remote-components: загрузка JS solver для n/signature (ejs:github). none/off — отключить (нужен Node.js на PATH).
_raw_rc = (os.environ.get("YTDLP_REMOTE_COMPONENTS") or "ejs:github").strip()
if _raw_rc.lower() in ("none", "off", "false", "-", "0"):
    YTDLP_REMOTE_COMPONENTS: List[str] = []
else:
    YTDLP_REMOTE_COMPONENTS = [x.strip() for x in _raw_rc.split(",") if x.strip()]

# Mini App URL (для кнопки в боте)
MINI_APP_URL = os.environ.get("MINI_APP_URL")
DAILY_VIDEO_LIMIT = int(os.environ.get("DAILY_VIDEO_LIMIT", 10))

# YouTube: только если НЕТ файла DEFAULT_YT_COOKIE (иначе сессия из cookies; смешивать с env нельзя)
YT_PO_TOKEN = os.environ.get("YT_PO_TOKEN")
YT_VISITOR_DATA = os.environ.get("YT_VISITOR_DATA")

# Локальный Bot API (для больших файлов), например http://127.0.0.1:8081
LOCAL_BOT_API_URL = os.environ.get("LOCAL_BOT_API_URL", "").rstrip("/")