import os

from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.environ.get("TOKEN")
DB_NAME = os.environ.get("DB_NAME")
DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
DB_PORT = os.environ.get("DB_PORT")
DB_PATH = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

ADMINS = os.environ.get("ADMINS").split()

DEV_CHANEL_ID = os.environ.get("DEV_CHANEL_ID")

PROXYS = os.environ.get("PROXY", "[]")