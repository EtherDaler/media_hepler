# Media Helper Bot 🎬

Telegram бот для скачивания медиа контента с различных платформ + Mini App плеер в стиле Spotify.

## 🚀 Возможности

### Telegram Bot
- **YouTube** — скачивание видео (выбор качества) и аудио с обложками
- **Instagram Reels** — скачивание видео
- **TikTok** — скачивание видео (с поддержкой прокси)
- **Pinterest** — скачивание видео
- **Shazam** — распознавание музыки из голосовых сообщений и видео
- **Inline режим** — скачивание в любом чате через @bot_name

### Mini App (Web Player)
- Плеер в стиле Spotify
- Управление очередью воспроизведения (drag & drop)
- Плейлисты и избранное
- Lock screen controls (Media Session API)
- Поиск по YouTube

### Дополнительные функции
- Водяной знак на видео после лимита загрузок
- Статистика загрузок (для админов)
- PO Token для YouTube (вместо cookies)

## 📋 Требования

- Python 3.10+
- PostgreSQL
- FFmpeg
- Node.js 18+ (для Mini App)
- Deno (для YouTube JS challenges)

## 🛠 Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/EtherDaler/media_hepler.git
cd media_helper
```

### 2. Создание виртуального окружения

```bash
# Linux/Mac
python3 -m venv myvenv
source myvenv/bin/activate

# Windows
python -m venv myvenv
myvenv\Scripts\activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
# Telegram Bot
TOKEN=your_bot_token
ADMINS=admin_id_1 admin_id_2
DEV_CHANEL_ID=-100xxxxxxxxx

# Database
DB_NAME=media_helper
DB_HOST=localhost
DB_USER=postgres
DB_PASS=your_password
DB_PORT=5432

# Optional: Proxy for TikTok
PROXY=[]
SIMPLE_PROXY=

# YouTube cookies (path to cookies file)
DEFAULT_YT_COOKIE=/path/to/cookie.txt

# YouTube PO Token (alternative to cookies)
YT_PO_TOKEN=your_po_token
YT_VISITOR_DATA=your_visitor_data

# Mini App
MINI_APP_URL=https://your-domain.com

# Watermark limit
DAILY_VIDEO_LIMIT=8
```

### 5. Настройка базы данных

```bash
# Создание базы данных
createdb media_helper

# Применение миграций
alembic upgrade head
```

### 6. Запуск бота

```bash
python main.py
```

## 🌐 Mini App (Frontend)

### Установка

```bash
cd mini-app
npm install
```

### Разработка

```bash
npm run dev
```

### Сборка для продакшена

```bash
npm run build
```

### Деплой на VPS

1. Собрать Mini App: `npm run build`
2. Настроить Nginx для раздачи статики из `mini-app/dist`
3. Настроить SSL сертификат (Let's Encrypt)
4. Добавить API прокси в Nginx конфиг

## 🔧 Локальное тестирование

Запустите worker.py для тестирования отдельных функций:

```bash
python worker.py
```

Доступные опции:
1. Скачать YouTube видео
2. Извлечь аудио из видео
3. Скачать аудио с YouTube
4. Скачать Instagram Reels
5. Заменить аудио в видео
6. Скачать TikTok
7. Поиск YouTube видео
8. Получить форматы YouTube видео
9. Скачать Reels V2 (с перекодированием для iOS)
10. Тест водяного знака
11. Скачать Pinterest видео

## 🔐 YouTube Cookies

Для скачивания age-restricted видео нужны cookies:

1. Установите расширение "Get cookies.txt LOCALLY" в браузере
2. Залогиньтесь на YouTube (аккаунт с подтвержденным возрастом)
3. Экспортируйте cookies в файл
4. Укажите путь в `DEFAULT_YT_COOKIE`

### YouTube PO Token (альтернатива cookies)

PO Token более стабилен и не требует обновления:

1. Откройте YouTube в браузере
2. DevTools → Network → фильтр `player`
3. Найдите `visitor_data` и `poToken` в запросах
4. Добавьте в `.env`:
   ```env
   YT_PO_TOKEN=your_token
   YT_VISITOR_DATA=your_visitor_data
   ```

## 📊 Админ команды

- `/stats` — статистика за сегодня (DAU, загрузки по платформам, топ пользователей)
- `/count_users` — количество пользователей