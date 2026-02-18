import asyncio
import os
import base64
import yt_dlp
import subprocess
import fnmatch
import random
import re
import requests
import json
import logging
import urllib
import shutil
import tempfile

from datetime import datetime
from typing import Optional, Dict, Any, List
from moviepy import VideoFileClip, AudioFileClip, concatenate_audioclips
from youtube_search import YoutubeSearch
from yt_dlp.networking.exceptions import SSLError
from yt_dlp.utils import DownloadError

from data.config import PROXYS, DEFAULT_YT_COOKIE


logger = logging.getLogger(__name__)


PARSED_PROXYS = json.loads(PROXYS)


def find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result


def generate_session():
    return base64.b64encode(os.urandom(16))


def get_random_proxy():
    if not PARSED_PROXYS:
        return None
    proxy = random.choice(PARSED_PROXYS)
    return proxy


def get_name_from_path(path: str):
    filename = path.split("/")
    filename = filename[-1]
    filename = filename.split(".")
    filename = filename[0]
    return filename


def compress_video_ffmpeg(input_file, output_file, max_size_mb=50, path='./videos/youtube'):
    """
    Сжимает видеофайл до нужного размера (меньше 50 МБ).
    Использует FFmpeg для сжатия видео.
    """
    # Определим максимальный размер в байтах
    max_size_bytes = max_size_mb * 1024 * 1024
    up_threashhold = 100 * 1024 * 1024
    
    # Проверим размер файла
    file_size = os.path.getsize(f"{path}/{input_file}")
    
    if file_size <= max_size_bytes:
        return input_file  # Если файл уже меньше или равен 50 МБ, просто возвращаем его
    
    # Параметры сжатия: снижаем битрейт и качество видео
    command = [
        'ffmpeg', '-i', f"{path}/{input_file}",
        '-vcodec', 'libx264',  # Используем кодек H.264
        '-crf', '28',  # Constant Rate Factor, компромисс между качеством и размером (22-28)
        '-preset', 'fast',  # Настройка скорости сжатия
        '-y',  # Перезаписываем выходной файл
        f"{path}/{output_file}"
    ]
    
    # Выполняем команду
    subprocess.run(command, check=True)
    
    # Проверяем, уменьшился ли файл до нужного размера
    output_size = os.path.getsize(f"{path}/{output_file}")
    if output_size > max_size_bytes:
        logger.warning(f"Warning: Video is still larger than {max_size_mb} MB.")

    if os.path.isfile(f"{path}/{input_file}"):
        os.remove(f"{path}/{input_file}")
    
    return output_file


def compress_video(input_path, output_path, target_size_mb=50):
    # Получаем размер файла в мегабайтах
    file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
    
    # Если размер больше указанного порога
    if file_size_mb > target_size_mb:
        logger.info(f"Видео {input_path} имеет размер {file_size_mb:.2f} МБ, что больше {target_size_mb} МБ.")
        logger.info("Запуск сжатия...")

        # Открываем видеофайл с помощью moviepy
        video = VideoFileClip(input_path)

        # Пример сжатия, уменьшив битрейт
        video.write_videofile(output_path, bitrate="500k", codec="libx264", audio_codec="aac")
        
        logger.info(f"Видео сжато и сохранено как {output_path}")
        if os.path.isfile(f"{input_path}"):
            os.remove(f"{input_path}")
        return True
    else:
        logger.info(f"Размер видео {input_path} ({file_size_mb:.2f} МБ) меньше {target_size_mb} МБ. Сжатие не требуется.")
        return False
    

# Хранит пути к временным файлам cookies для очистки
_temp_cookie_files = []

def get_temp_cookie_copy(original_cookie_path):
    """
    Создаёт временную копию файла cookies, чтобы yt-dlp не портил оригинал.
    Возвращает путь к временной копии.
    """
    if not original_cookie_path or not os.path.isfile(original_cookie_path):
        return None
    
    try:
        # Создаём временный файл
        fd, tmp_path = tempfile.mkstemp(suffix='.txt', prefix='yt_cookie_')
        os.close(fd)
        # Копируем содержимое
        shutil.copy2(original_cookie_path, tmp_path)
        _temp_cookie_files.append(tmp_path)
        return tmp_path
    except Exception as e:
        logger.warning(f"Failed to create temp cookie copy: {e}")
        return original_cookie_path

def cleanup_temp_cookies():
    """Удаляет все временные файлы cookies"""
    global _temp_cookie_files
    for path in _temp_cookie_files:
        try:
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass
    _temp_cookie_files = []


def get_yt_dlp_conf(path, proxy=None, player_client=["web"]):
    """
    Возвращает ydl_opts. Если proxy_url задан — он подставляется (нормализуется).
    Использует временную копию cookies чтобы не портить оригинал.
    """
    ydl_opts = {
        'format': 'bestvideo[height<=1080]+bestaudio/bestvideo+bestaudio/best',
        'outtmpl': f'{path}/%(title)s.%(ext)s',
        'noplaylist': True,
        'verbose': False,  # уменьшаем логирование
        'quiet': False,    # включаем логирование для отладки
        'extractor_args': {
            'youtube': {
                'player_client': player_client,
            }
        },
        'http_chunk_size': 0,   # отключаем chunked/Range-запросы
        'nopart': True,         # не использовать .part файлы
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'socket_timeout': 30,
        'retries': 3,
        'fragment_retries': 10,
        'nocheckcertificate': True,
        'skip_unavailable_fragments': True,
        'continue_dl': True,
        'ignoreerrors': False,
        # Включаем remote components для решения JS challenges (вместо --remote-components ejs:github)
        'remote_components': ['ejs:github'],
    }
    
    # Добавляем cookies если файл существует (используем временную копию!)
    if DEFAULT_YT_COOKIE and os.path.isfile(DEFAULT_YT_COOKIE):
        temp_cookie = get_temp_cookie_copy(DEFAULT_YT_COOKIE)
        if temp_cookie:
            ydl_opts['cookiefile'] = temp_cookie

    if proxy:
        proxy_url = list(proxy.keys())[0]
        proxy_cookie = proxy[proxy_url]
        p = str(proxy_url).rstrip('/')
        ydl_opts['proxy'] = p
        # Используем временную копию cookies для прокси тоже
        temp_proxy_cookie = get_temp_cookie_copy(proxy_cookie)
        if temp_proxy_cookie:
            ydl_opts['cookiefile'] = temp_proxy_cookie
        ydl_opts['socket_timeout'] = 150
        # ставим env на всякий случай, очищаем HTTP_PROXY/HTTPS_PROXY
        os.environ['ALL_PROXY'] = p
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)

    else:
        # гарантия, что при вызове без прокси окружение не использует старый прокси
        os.environ.pop('ALL_PROXY', None)
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)

    return ydl_opts


def extract_info_sync(opts, url, download=False):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=download)


async def get_format_for_youtube(ydl_opts, link, format_id='best', res='720p'):
    loop = asyncio.get_running_loop()

    # Копируем опции и убираем format - нам нужна только информация о форматах
    info_opts = ydl_opts.copy()
    info_opts.pop('format', None)  # Убираем format чтобы не было ошибки "Requested format is not available"
    info_opts['skip_download'] = True
    info_opts['ignore_no_formats_error'] = True  # Игнорируем ошибки форматов

    try:
        info = await loop.run_in_executor(None, lambda: extract_info_sync(info_opts, link, download=False))
    except (DownloadError, SSLError, Exception) as e:
        # не падаем — логируем и возвращаем fallback
        logger.warning(f"get_format_for_youtube: failed to extract info (will fallback). Error: {e}")
        # если пользователь явно указал формат (например '137' или '96'), вернём его
        if format_id and format_id != 'best':
            return format_id
        # иначе fallback на 'best'
        return 'best'

    formats = info.get('formats', []) or []

    def is_hls(fmt):
        proto = (fmt.get('protocol') or '').lower()
        ext = (fmt.get('ext') or '').lower()
        note = (fmt.get('format_note') or '').lower()
        return ('m3u8' in proto) or ('m3u8' in ext) or ('hls' in proto) or ('sabr' in note)

    # если запрошен 'best' — подбираем prefer itag 18 или лучший <= res
    if format_id == 'best':
        # preference for itag 18
        for f in formats:
            if f.get('format_id') == '18':
                return '18'

        max_h = 1080
        if isinstance(res, str) and res.endswith('p'):
            try:
                max_h = int(res[:-1])
            except Exception:
                pass
        cand = [f for f in formats if (f.get('vcodec') != 'none') and ((f.get('height') or 0) <= max_h)]
        if cand:
            cand_sorted = sorted(cand, key=lambda x: ((x.get('height') or 0), (x.get('tbr') or 0)), reverse=True)
            return cand_sorted[0].get('format_id')
        return 'best'
    else:
        # явно указанный формат — но если он HLS, попробуем подобрать non-HLS fallback
        chosen = str(format_id)
        chosen_entry = next((f for f in formats if str(f.get('format_id')) == chosen), None)
        if chosen_entry and is_hls(chosen_entry):
            # ищем ближайшую non-HLS альтернативу
            candidates = [f for f in formats if not is_hls(f) and (f.get('vcodec') != 'none')]
            if candidates:
                cand_sorted = sorted(candidates, key=lambda x: ((x.get('height') or 0), (x.get('tbr') or 0)), reverse=True)
                logger.info("Requested format %s is HLS — returning fallback non-HLS %s", chosen, cand_sorted[0].get('format_id'))
                return cand_sorted[0].get('format_id')
            # иначе возвращаем то, что попросили
        return format_id


async def download_from_youtube(link, path='./videos/youtube', out_format="mp4", res="720p", format_id="best", filename=None):
    """
    Логика:
    1) Пытаться скачать БЕЗ прокси (player_client=web).
    2) Если всё ещё неудача — попытки повторяются с прокси (если get_random_proxy() даёт прокси).
    Если неудача — пробовать другие clients (android_embedded, tv_embedded) без прокси.
    Возвращает имя файла (строку) или None.
    """
    os.makedirs(path, exist_ok=True)
    loop = asyncio.get_running_loop()
    logger.info(f"Trying to download video in format: {format_id}")
    result = None

    async def try_strategy(ydl_opts, tries=3):
        backoff = 1.0
        for i in range(1, tries + 1):
            try:
                logger.info(f"Download attempt {i} for client={ydl_opts.get('extractor_args', {}).get('youtube', {}).get('player_client')} proxy={ydl_opts.get('proxy')} format={ydl_opts.get('format')}")
                res_local = await loop.run_in_executor(None, lambda: extract_info_sync(ydl_opts, link, download=True))
                return res_local
            except SSLError as e:
                logger.warning(f"SSLError attempt {i}: {e}")
            except Exception as e:
                logger.warning(f"Download attempt {i} failed: {e}")
                if 'Unable to download webpage' in str(e):
                    ydl_opts['user_agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            if i < tries:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
        return None

    # 1) no-proxy, web-like (пробуем разные клиенты)
    try:
        ydl_opts = get_yt_dlp_conf(path, proxy=None, player_client=['web_creator', 'mweb', 'tv'])
        chosen_format = await get_format_for_youtube(ydl_opts, link, format_id, res)
        # Добавляем fallback на 'best' если выбранный формат недоступен
        ydl_opts['format'] = f"{chosen_format}/best" if chosen_format != 'best' else 'best'
        logger.info(f"Chosen format (no-proxy): {ydl_opts['format']}")
        result = await try_strategy(ydl_opts, tries=1)
    except Exception as e:
        logger.exception(f"Unexpected error in primary no-proxy flow: {e}")
        result = None

    # fallback no-proxy alt client
    if result is None:
        try:
            ydl_opts_alt = get_yt_dlp_conf(path, proxy=None, player_client=['android_embedded'])
            ydl_opts_alt['format'] = 'best'
            result = await try_strategy(ydl_opts_alt, tries=1)
        except Exception as e:
            logger.exception(f"Unexpected error in no-proxy fallback: {e}")
            result = None

    # 2) try with proxy(s)
    if result is None:
        # get_random_proxy может возвращать dict или строку; поддерживаем оба варианта
        proxy = None
        try:
            proxy = get_random_proxy()
        except Exception as e:
            logger.exception(f"get_random_proxy failed: {e}")
            proxy = None

        if proxy:
            # primary proxy attempt
            try:
                ydl_opts_p = get_yt_dlp_conf(path, proxy=proxy, player_client=['web_creator', 'mweb', 'tv'])
                chosen_format_p = await get_format_for_youtube(ydl_opts_p, link, format_id, res)
                # Добавляем fallback на 'best' если выбранный формат недоступен
                ydl_opts_p['format'] = f"{chosen_format_p}/best" if chosen_format_p != 'best' else 'best'
                logger.info(f"Chosen format (proxy): {ydl_opts_p['format']}")
                result = await try_strategy(ydl_opts_p, tries=1)
            except Exception as e:
                logger.exception(f"Unexpected error preparing proxy attempt: {e}")
                result = None

            # fallback proxy client
            if result is None:
                try:
                    ydl_opts_p2 = get_yt_dlp_conf(path, proxy=proxy, player_client=['android_embedded'])
                    ydl_opts_p2['format'] = 'best'
                    result = await try_strategy(ydl_opts_p2, tries=1)
                except Exception as e:
                    logger.exception(f"Unexpected error in proxy fallback: {e}")
                    result = None

    os.environ.pop('ALL_PROXY', None)
    os.environ.pop('HTTP_PROXY', None)
    os.environ.pop('HTTPS_PROXY', None)
    
    # Очищаем временные файлы cookies
    cleanup_temp_cookies()

    # если успешно — формируем имя файла и возвращаем
    if result is not None:
        video_title = result.get('title', 'video').strip()
        replacements = {
            '/': '⧸', '\\': '⧹', '|': '｜', '?': '？', '*': '＊',
            ':': '：', '"': '＂', '<': '＜', '>': '＞',
        }
        for old, new in replacements.items():
            video_title = video_title.replace(old, new)
        video_title = re.sub(r'[\x00-\x1F\x7F]', '', video_title)
        ext = result.get('ext', out_format)
        video_filename = f"{video_title}.{ext}"
        return video_filename

    # все попытки провалены
    return None


class YoutubeSearchWithProxy(YoutubeSearch):
    def __init__(self, search_terms: str, max_results=None, proxy=None):
        self.proxy = proxy
        super().__init__(search_terms, max_results)
    
    def _search(self):
        # Убедитесь, что установлен пакет для поддержки SOCKS: pip install requests[socks]
        encoded_search = urllib.parse.quote_plus(self.search_terms)
        BASE_URL = "https://youtube.com"
        url = f"{BASE_URL}/results?search_query={encoded_search}"
        
        # Настройка прокси для SOCKS5h
        proxies = None
        if self.proxy:
            proxies = {
                'http': self.proxy,
                'https': self.proxy
            }
        
        response = requests.get(url, proxies=proxies).text
        while "ytInitialData" not in response:
            response = requests.get(url, proxies=proxies).text
            
        results = self._parse_html(response)
        if self.max_results is not None and len(results) > self.max_results:
            return results[: self.max_results]
        return results


def search_videos(query, max_results=8):
    """Поиск видео по запросу"""
    try:
        proxy = list(get_random_proxy().keys())[0]
        results = YoutubeSearchWithProxy(query, max_results=max_results, proxy=proxy).to_dict()
        return results
    except Exception as e:
        logging.error(f"Ошибка поиска: {e}")
        return []


def get_video_formats(url: str, max_formats=5):
    """Получение доступных форматов видео"""
    
    def extract_formats(ydl_opts):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Фильтруем форматы: только видео+аудио в MP4
            video_formats = []
            for f in info.get('formats', []):
                if (f.get('vcodec') != 'none' and 
                    f.get('acodec') != 'none' and 
                    f.get('ext') == 'mp4'):
                    
                    format_info = {
                        'format_id': f.get('format_id'),
                        'resolution': f.get('resolution', 'N/A'),
                        'format_note': f.get('format_note', 'N/A'),
                        'filesize': format_filesize(f.get('filesize')),
                        'quality': get_quality_score(f)
                    }
                    video_formats.append(format_info)
            
            # Сортируем по качеству и берем топ
            video_formats.sort(key=lambda x: x['quality'], reverse=True)
            return video_formats[:max_formats]
    
    # Попытка без прокси (используем временную копию куки!)
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'age_limit': None,  # Снимаем ограничение возраста
    }
    
    # Проверяем наличие и валидность cookie файла
    cookie_exists = DEFAULT_YT_COOKIE and os.path.isfile(DEFAULT_YT_COOKIE)
    logger.info(f"get_video_formats: Cookie file exists: {cookie_exists}, path: {DEFAULT_YT_COOKIE}")
    
    # Используем временную копию куки, чтобы оригинал не перезатирался
    temp_cookie = None
    if DEFAULT_YT_COOKIE and os.path.isfile(DEFAULT_YT_COOKIE):
        temp_cookie = get_temp_cookie_copy(DEFAULT_YT_COOKIE)
        if temp_cookie:
            ydl_opts['cookiefile'] = temp_cookie
            logger.info(f"get_video_formats: Using temp cookie: {temp_cookie}")
        else:
            logger.warning("get_video_formats: Failed to create temp cookie copy!")
    else:
        logger.warning(f"get_video_formats: Cookie file NOT found at {DEFAULT_YT_COOKIE}")
    
    try:
        result = extract_formats(ydl_opts)
        cleanup_temp_cookies()
        return result
    except Exception as e:
        logger.warning(f"Ошибка получения форматов без прокси: {e}. Пробуем с прокси...")
    
    # Fallback: пробуем с прокси
    try:
        proxy = get_random_proxy()
        if proxy:
            proxy_url = list(proxy.keys())[0]
            proxy_cookie = proxy[proxy_url]
            ydl_opts['proxy'] = str(proxy_url).rstrip('/')
            # Используем временную копию прокси-куки тоже
            temp_proxy_cookie = get_temp_cookie_copy(proxy_cookie)
            if temp_proxy_cookie:
                ydl_opts['cookiefile'] = temp_proxy_cookie
            ydl_opts['socket_timeout'] = 150
            result = extract_formats(ydl_opts)
            cleanup_temp_cookies()
            return result
    except Exception as e:
        logger.error(f"Ошибка получения форматов с прокси: {e}")
    
    cleanup_temp_cookies()
    return []


def get_quality_score(format_info):
    """Оценка качества формата для сортировки"""
    score = 0
    resolution = format_info.get('resolution', '')
    
    if '1080' in resolution:
        score += 300
    elif '720' in resolution:
        score += 200
    elif '480' in resolution:
        score += 100
    
    if 'mp4' in format_info.get('ext', ''):
        score += 50
    
    filesize = format_info.get('filesize', 0)
    if filesize:
        score += min(filesize / (1024 * 1024), 100)  # Максимум 100 за размер
        
    return score


def format_filesize(size_bytes):
    """Форматирование размера файла"""
    if not size_bytes:
        return 0
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            break
        size_bytes /= 1024.0
    return size_bytes


def format_filesize_str(size_bytes):
    """Форматирование размера файла в строку"""
    if not size_bytes:
        return "Неизвестно"
    
    size = format_filesize(size_bytes)
    units = ['B', 'KB', 'MB', 'GB']
    unit_index = 0
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
        
    return f"{size:.1f} {units[unit_index]}"


def format_formats_for_display(formats: List[Dict]) -> str:
    """Форматирует список форматов для читаемого вывода"""
    if not formats:
        return "❌ Не удалось получить форматы для этого видео"
    
    output = "📹 **Доступные форматы:**\n\n"
    
    for i, fmt in enumerate(formats, 1):
        output += f"🎥 **Формат {i}**\n"
        output += f"   🆔 ID: `{fmt['format_id']}`\n"
        output += f"   📊 Разрешение: {fmt['resolution']}\n"
        output += f"   💾 Размер: {fmt['filesize']}\n"
        output += f"   🎚 Качество: {fmt['format_note']}\n"
        output += f"   📝 Тип: Видео+Аудио\n"
        output += f"   🔤 Расширение: mp4\n\n"
    
    output += "💡 *Используйте ID формата для загрузки*"
    return output


def extract_video_id(url: str) -> str:
    """Извлечение ID видео из YouTube ссылки"""
    import re
    
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&/\n?#]*)',
        r'youtube\.com/embed/([^&/\n?#]*)',
        r'youtube\.com/v/([^&/\n?#]*)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


async def convert_to_audio(video, path='./audio/converted', out_format="mp3", filename=None):
    if filename is None:
        filename, ext = os.path.splitext(video)   
    os.makedirs(path, exist_ok=True)
    result = await asyncio.to_thread(_convert_audio, video, path, out_format, filename)
    return result

def _convert_audio(video, path, out_format, filename):
    clip = VideoFileClip(video)
    ind = 1
    # Генерируем уникальное имя файла
    while os.path.isfile(f"{path}/{filename}.{out_format}"):
        filename = filename + f"({ind})"
        ind += 1
    # Сохраняем аудио в нужном формате
    filename = filename.strip()
    clip.audio.write_audiofile(f"{path}/{filename}.{out_format}")
    clip.close()
    return f"{filename}.{out_format}"

async def get_audio_from_youtube(link, path="./audio/youtube", out_format="mp3", filename=None):
    """
    Скачивает видео и конвертирует в аудио с метаданными (автор, название).
    
    Returns:
        dict: {'audio': 'filename.mp3', 'thumbnail': '/path/to/thumbnail.jpg'} или None
    """
    audio = None
    thumbnail = None
    video_path = "./videos/youtube"
    
    # Извлекаем video_id для обложки
    video_id = extract_video_id(link)
    
    # Сначала получаем информацию о видео для метаданных
    try:
        video_info = get_youtube_video_info(link)
        title = video_info.get('title', 'Unknown')
        artist = video_info.get('channel', 'Unknown')
    except Exception as e:
        logger.warning(f"Could not get video info for metadata: {e}")
        title = "Unknown"
        artist = "Unknown"
    
    # Скачиваем обложку ПАРАЛЛЕЛЬНО с видео
    async def download_thumbnail_async():
        if video_id:
            try:
                return await asyncio.to_thread(download_youtube_thumbnail, video_id)
            except Exception as e:
                logger.warning(f"Could not download thumbnail: {e}")
        return None
    
    # Запускаем параллельно
    thumbnail_task = asyncio.create_task(download_thumbnail_async())
    video = await download_from_youtube(link)
    thumbnail = await thumbnail_task  # Получаем результат (уже готов или почти готов)
    
    # Проверка на None СРАЗУ после скачивания
    if video is None:
        print("Произошла ошибка при загрузке видео")
        return None
    
    # Извлекаем имя файла без расширения
    rev = video[::-1]
    tmp = rev.find('.')
    filename = rev[:tmp:-1]
    
    os.makedirs(path, exist_ok=True)
    
    # Генерируем уникальное имя файла
    output_filename = filename.strip()
    ind = 1
    while os.path.isfile(f"{path}/{output_filename}.{out_format}"):
        output_filename = f"{filename}({ind})"
        ind += 1
    
    input_file = f"{video_path}/{video}"
    output_file = f"{path}/{output_filename}.{out_format}"
    
    try:
        # Конвертируем через ffmpeg с метаданными
        ffmpeg_cmd = [
            'ffmpeg', '-i', input_file,
            '-vn',  # Без видео
            '-acodec', 'libmp3lame' if out_format == 'mp3' else 'aac',
            '-ab', '192k',
            '-metadata', f'title={title}',
            '-metadata', f'artist={artist}',
            '-metadata', 'album=YouTube',
            '-y',
            output_file
        ]
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            audio = f"{output_filename}.{out_format}"
        else:
            logger.error(f"FFmpeg error: {result.stderr}")
    except Exception as e:
        logger.error(f"Error converting to audio: {e}")
    finally:
        # Удаляем видео файл в любом случае
        if os.path.isfile(input_file):
            os.remove(input_file)
    
    if audio:
        return {
            'audio': audio,
            'thumbnail': thumbnail
        }
    return None

def reencode_video(path_to_video):
    """
    Перекодирует видео для совместимости с iOS/Telegram.
    Оптимизировано для скорости с сохранением совместимости.
    """
    output_path = path_to_video.replace('.mp4', '_reencoded.mp4')
    command = [
        'ffmpeg', '-i', path_to_video,
        '-c:v', 'libx264',
        '-preset', 'veryfast',      # Быстрое кодирование (в 3-5 раз быстрее дефолта)
        '-crf', '23',               # Хорошее качество
        '-profile:v', 'baseline',   # Максимальная совместимость с iOS
        '-level', '3.1',
        '-pix_fmt', 'yuv420p',      # Совместимость с iOS
        '-c:a', 'aac',
        '-b:a', '128k',             # Битрейт аудио
        '-movflags', '+faststart',  # Метаданные в начале для стриминга
        '-y',                       # Перезаписывать без вопросов
        output_path
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path

def _download_instagram_reels_sync(reels_url):
    """Синхронная функция скачивания Instagram reels (внутренняя)"""
    import shutil
    import tempfile
    
    path = "./videos/reels"
    os.makedirs(path, exist_ok=True)
    match = re.search(r"reel/([^/?]+)", reels_url)
    filename = match.group(1) if match else "instagram_video"
    ind = 0
    while os.path.isfile(f"{path}/{filename}.mp4"):
        filename = filename + f"({ind})"
        ind += 1
    filename = filename.strip()
    cookies = ['0', '1', '2']
    while len(cookies) > 0:
        cookie = random.choice(cookies)
        original_cookie_path = f'./instagram{cookie}.txt'
        tmp_cookie_path = None
        
        # Создаём временную копию файла с куками, чтобы yt-dlp не перезаписал оригинал
        # Используем shutil.copy2 для точного бинарного копирования
        try:
            if not os.path.exists(original_cookie_path):
                raise FileNotFoundError(f"Cookie file not found: {original_cookie_path}")
            
            # Создаём временный файл и копируем туда куки
            tmp_fd, tmp_cookie_path = tempfile.mkstemp(suffix='.txt')
            os.close(tmp_fd)
            shutil.copy2(original_cookie_path, tmp_cookie_path)
        except FileNotFoundError:
            logger.warning(f"Cookie file not found: {original_cookie_path}")
            cookies.remove(cookie)
            continue
        
        try:
            ydl_opts = {
                'outtmpl': f"{path}/{filename}.%(ext)s",
                'cookiefile': tmp_cookie_path,  # Используем временную копию
                # Приоритет: лучшее видео (до 1080p) + аудио, иначе лучший комбинированный
                'format': 'bestvideo[height<=1080]+bestaudio/bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',  # Гарантируем mp4 на выходе
                # Сортировка форматов: приоритет качеству и разрешению
                'format_sort': ['res:1080', 'vcodec:h264', 'acodec:aac'],
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
                },
                'noplaylist': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([reels_url])
            return f"{path}/{filename}.mp4"
        except Exception as e:
            cookies.remove(cookie)
            logger.error(f"Failed with cookie {cookie}: {e}")
        finally:
            # Удаляем временный файл
            if tmp_cookie_path and os.path.exists(tmp_cookie_path):
                os.remove(tmp_cookie_path)
    return None


async def download_instagram_reels(reels_url):
    """Асинхронная функция скачивания Instagram reels"""
    return await asyncio.to_thread(_download_instagram_reels_sync, reels_url)


def _download_instagram_reels_sync_v2(reels_url):
    """
    Скачивание Instagram reels с автоматическим перекодированием для iOS.
    Скачивает видео, затем перекодирует через ffmpeg в одной функции.
    
    Для тестирования: python worker.py, затем выбрать вариант 9 и ввести ссылку.
    """
    import shutil
    import tempfile
    
    path = "./videos/reels"
    os.makedirs(path, exist_ok=True)
    i = reels_url.find("reel")
    j = reels_url[i+5:].find('/')
    filename = reels_url[i+5:i+5+j]
    ind = 0
    while os.path.isfile(f"{path}/{filename}.mp4") or os.path.isfile(f"{path}/{filename}_ios.mp4"):
        filename = filename + f"({ind})"
        ind += 1
    filename = filename.strip()
    cookies = ['0', '1', '2']
    
    while len(cookies) > 0:
        cookie = random.choice(cookies)
        original_cookie_path = f'./instagram{cookie}.txt'
        tmp_cookie_path = None
        
        try:
            if not os.path.exists(original_cookie_path):
                raise FileNotFoundError(f"Cookie file not found: {original_cookie_path}")
            
            tmp_fd, tmp_cookie_path = tempfile.mkstemp(suffix='.txt')
            os.close(tmp_fd)
            shutil.copy2(original_cookie_path, tmp_cookie_path)
        except FileNotFoundError:
            logger.warning(f"Cookie file not found: {original_cookie_path}")
            cookies.remove(cookie)
            continue
        
        try:
            # Шаг 1: Скачиваем видео
            temp_file = f"{path}/{filename}_temp.mp4"
            ydl_opts = {
                'outtmpl': f"{path}/{filename}_temp.%(ext)s",
                'cookiefile': tmp_cookie_path,
                'format': 'bestvideo[height<=1080]+bestaudio/bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'format_sort': ['res:1080', 'vcodec:h264', 'acodec:aac'],
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
                },
                'noplaylist': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([reels_url])
            
            # Шаг 2: Перекодируем для iOS
            output_file = f"{path}/{filename}.mp4"
            ffmpeg_cmd = [
                'ffmpeg', '-i', temp_file,
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-profile:v', 'baseline',
                '-level', '3.1',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                '-y',
                output_file
            ]
            logger.info(f"Running ffmpeg: {' '.join(ffmpeg_cmd)}")
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                return None
            
            # Удаляем временный файл
            if os.path.isfile(temp_file):
                os.remove(temp_file)
            
            logger.info(f"Downloaded and encoded for iOS: {output_file}")
            return output_file
            
        except Exception as e:
            cookies.remove(cookie)
            logger.error(f"Failed with cookie {cookie}: {e}")
            # Очистка при ошибке
            temp_file = f"{path}/{filename}_temp.mp4"
            if os.path.isfile(temp_file):
                os.remove(temp_file)
        finally:
            if tmp_cookie_path and os.path.exists(tmp_cookie_path):
                os.remove(tmp_cookie_path)
    return None


def format_duration(seconds: int) -> str:
    """Форматирование длительности из секунд"""
    if not seconds:
        return "N/A"
    
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def get_yt_info(ydl_opts, url, video_id):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_info = {
            'id': video_id,
            'title': info.get('title', 'Неизвестно'),
            'channel': info.get('uploader', 'Неизвестно'),
            'duration': format_duration(info.get('duration', 0)),
            'views': 'N/A'
        }
    return video_info

def get_youtube_video_info(url):
    os.environ.pop('ALL_PROXY', None)
    os.environ.pop('HTTP_PROXY', None)
    os.environ.pop('HTTPS_PROXY', None)
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True,
        'skip_download': True,  # Явно указываем что не скачиваем
        'extract_flat': 'in_playlist',  # Для одиночных видео - полная инфа, для плейлистов - только метаданные
        'ignore_no_formats_error': True,  # Игнорируем ошибки форматов - нам нужны только метаданные
    }
    
    # Используем временную копию куки, чтобы оригинал не перезатирался
    if DEFAULT_YT_COOKIE and os.path.isfile(DEFAULT_YT_COOKIE):
        temp_cookie = get_temp_cookie_copy(DEFAULT_YT_COOKIE)
        if temp_cookie:
            ydl_opts['cookiefile'] = temp_cookie
    
    video_id = extract_video_id(url)
    video_info = None
    try:
        video_info = get_yt_info(ydl_opts, url, video_id)
        cleanup_temp_cookies()
        return video_info
    except Exception as e:
        logger.error(f"Got Error while get_youtube_video_info: {e}. \nTry with Proxy...")
        try:
            proxy = get_random_proxy()
            if proxy:
                proxy_url = list(proxy.keys())[0]
                proxy_cookie = proxy[proxy_url]
                p = str(proxy_url).rstrip('/')
                ydl_opts['proxy'] = p
                # Используем временную копию прокси-куки тоже
                temp_proxy_cookie = get_temp_cookie_copy(proxy_cookie)
                if temp_proxy_cookie:
                    ydl_opts['cookiefile'] = temp_proxy_cookie
                ydl_opts['socket_timeout'] = 150
                # ставим env на всякий случай, очищаем HTTP_PROXY/HTTPS_PROXY
                os.environ['ALL_PROXY'] = p
                os.environ.pop('HTTP_PROXY', None)
                os.environ.pop('HTTPS_PROXY', None)
                video_info = get_yt_info(ydl_opts, url, video_id)
        except Exception as e2:
            logger.error(f"Got Error with proxy too: {e2}")
        cleanup_temp_cookies()
    return video_info


def download_youtube_thumbnail(video_id: str, output_path: str = "./thumbnails") -> Optional[str]:
    """
    Скачивает и обрабатывает обложку видео с YouTube.
    Возвращает путь к квадратной обложке 320x320 для Telegram.
    """
    os.makedirs(output_path, exist_ok=True)
    
    # Пробуем разные качества обложек
    thumbnail_urls = [
        f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
    ]
    
    thumbnail_path = os.path.join(output_path, f"{video_id}.jpg")
    square_thumbnail_path = os.path.join(output_path, f"{video_id}_square.jpg")
    
    # Скачиваем обложку (сначала напрямую, потом через прокси)
    downloaded = False
    
    # Попытка 1: без прокси
    for url in thumbnail_urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200 and len(response.content) > 1000:
                with open(thumbnail_path, 'wb') as f:
                    f.write(response.content)
                downloaded = True
                break
        except Exception as e:
            logger.warning(f"Failed to download thumbnail from {url}: {e}")
            continue
    
    # Попытка 2: с прокси если не удалось напрямую
    if not downloaded:
        proxy = get_random_proxy()
        if proxy:
            proxy_url = list(proxy.keys())[0]
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            for url in thumbnail_urls:
                try:
                    response = requests.get(url, timeout=15, proxies=proxies)
                    if response.status_code == 200 and len(response.content) > 1000:
                        with open(thumbnail_path, 'wb') as f:
                            f.write(response.content)
                        downloaded = True
                        logger.info(f"Downloaded thumbnail via proxy: {video_id}")
                        break
                except Exception as e:
                    logger.warning(f"Failed to download thumbnail via proxy from {url}: {e}")
                    continue
    
    if not downloaded:
        return None
    
    # Обрезаем до квадрата с помощью ffmpeg
    try:
        # Получаем размеры изображения
        probe_cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'json',
            thumbnail_path
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        probe_data = json.loads(probe_result.stdout)
        
        width = probe_data['streams'][0]['width']
        height = probe_data['streams'][0]['height']
        
        # Вычисляем размер квадрата (минимум из ширины и высоты)
        size = min(width, height)
        x_offset = (width - size) // 2
        y_offset = (height - size) // 2
        
        # Обрезаем до квадрата и масштабируем до 320x320
        ffmpeg_cmd = [
            'ffmpeg', '-i', thumbnail_path,
            '-vf', f'crop={size}:{size}:{x_offset}:{y_offset},scale=320:320',
            '-y',
            square_thumbnail_path
        ]
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Удаляем оригинальный файл
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            return square_thumbnail_path
        else:
            logger.error(f"FFmpeg thumbnail error: {result.stderr}")
            return thumbnail_path  # Возвращаем оригинал если не получилось обрезать
            
    except Exception as e:
        logger.error(f"Error processing thumbnail: {e}")
        return thumbnail_path  # Возвращаем оригинал если ошибка


def replace_audio(video_path, audio_path, path="./videos/for_replace/ready"):
    os.makedirs(path, exist_ok=True)
    # Загружаем видео
    video_name = get_name_from_path(video_path)
    audio_name = get_name_from_path(audio_path)
    result_name = video_name + "_" + audio_name 
    result_name = result_name.strip()
    try:
        video = VideoFileClip(video_path)
        
        # Загружаем новое аудио
        audio = AudioFileClip(audio_path)
        
        # Проверяем длительности
        video_duration = video.duration
        audio_duration = audio.duration
        
        if audio_duration > video_duration:
            # Если аудио длиннее видео, обрезаем аудио
            audio = audio.subclip(0, video_duration)
        else:
            # Если аудио короче видео, повторяем аудио
            audio_clips = []
            while sum(clip.duration for clip in audio_clips) < video_duration:
                audio_clips.append(audio)
            audio = concatenate_audioclips(audio_clips)  # Конкатенируем клипы
            audio = audio.subclip(0, video_duration)  # Убираем лишнее, если есть

        # Заменяем аудиодорожку
        video = video.set_audio(audio)
        
        # Сохраняем новое видео
        video.write_videofile(f"{path}/{result_name}.mp4", codec='libx264', audio_codec='aac')
        return f"{path}/{result_name}.mp4"
    except:
        return None
    
def get_video_resolution_moviepy(video_path):
    """Получает разрешение видеофайла с помощью moviepy.

    Args:
    video_path: Путь к видеофайлу.

    Returns:
    Кортеж (ширина, высота).
    """

    clip = VideoFileClip(video_path)
    width, height = clip.size
    clip.close()
    return width, height


class TikTokDownloader:
    def __init__(self, save_path: str = 'tiktok_videos'):
        self.save_path = save_path
        self.create_save_directory()

    def create_save_directory(self) -> None:
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)

    @staticmethod
    def validate_url(url: str) -> bool:
        tiktok_pattern = r'https?://((?:vm|vt|www)\.)?tiktok\.com/.*'
        return bool(re.match(tiktok_pattern, url))

    @staticmethod
    def progress_hook(d: Dict[str, Any]) -> None:
        if d['status'] == 'downloading':
            progress = d.get('_percent_str', 'N/A')
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            logger.info(f"Downloading: {progress} at {speed} ETA: {eta}", end='\r')
        elif d['status'] == 'finished':
            logger.info("\nDownload completed, finalizing...")

    def get_filename(self, video_url: str, custom_name: Optional[str] = None) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if custom_name:
            return f"{custom_name}_{timestamp}.mp4"
        return f"tiktok_{timestamp}.mp4"

    def list_formats(self, video_url: str) -> None:
        """Debug helper: покажет доступные форматы для видео (позволит увидеть, есть ли аудио)."""
        ydl_opts = {'nocheckcertificate': True, 'listformats': True, 'quiet': False}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

    def _get_base_opts(self, output_path: str) -> dict:
        """Базовые опции для yt-dlp"""
        return {
            'outtmpl': output_path,
            'format': 'bestvideo+bestaudio/best',
            'noplaylist': True,
            'quiet': False,
            'verbose': True,
            'merge_output_format': 'mp4',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            'socket_timeout': 30,
            'retries': 3,
        }

    def download_video(self, video_url: str, custom_name: Optional[str] = None) -> Optional[str]:
        if not self.validate_url(video_url):
            logger.error("Error: Invalid TikTok URL")
            return None

        filename = self.get_filename(video_url, custom_name)
        output_path = os.path.join(self.save_path, filename)
        
        # 1) Попытка без прокси
        ydl_opts = self._get_base_opts(output_path)
        
        # Добавляем cookies если файл существует (используем временную копию!)
        tiktok_cookie = '/root/media_helper/tiktok_cookie.txt'
        if os.path.isfile(tiktok_cookie):
            temp_cookie = get_temp_cookie_copy(tiktok_cookie)
            if temp_cookie:
                ydl_opts['cookiefile'] = temp_cookie

        try:
            logger.info("TikTok: Trying download without proxy...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
                logger.info(f"\nVideo successfully downloaded: {output_path}")
            cleanup_temp_cookies()
            return filename
        except yt_dlp.utils.DownloadError as e:
            logger.warning(f"TikTok download without proxy failed: {e}")
        except Exception as e:
            logger.warning(f"TikTok unexpected error without proxy: {e}")

        # 2) Попытка с прокси
        try:
            proxy = get_random_proxy()
            if proxy:
                proxy_url = list(proxy.keys())[0]
                proxy_cookie = proxy[proxy_url]
                p = str(proxy_url).rstrip('/')
                
                logger.info(f"TikTok: Trying download with proxy {p}...")
                
                ydl_opts_proxy = self._get_base_opts(output_path)
                ydl_opts_proxy['proxy'] = p
                ydl_opts_proxy['socket_timeout'] = 150
                
                # Используем временную копию cookies от прокси
                if proxy_cookie and os.path.isfile(proxy_cookie):
                    temp_proxy_cookie = get_temp_cookie_copy(proxy_cookie)
                    if temp_proxy_cookie:
                        ydl_opts_proxy['cookiefile'] = temp_proxy_cookie
                elif os.path.isfile(tiktok_cookie):
                    temp_cookie = get_temp_cookie_copy(tiktok_cookie)
                    if temp_cookie:
                        ydl_opts_proxy['cookiefile'] = temp_cookie
                
                with yt_dlp.YoutubeDL(ydl_opts_proxy) as ydl:
                    ydl.download([video_url])
                    logger.info(f"\nVideo successfully downloaded with proxy: {output_path}")
                cleanup_temp_cookies()
                return filename
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"TikTok download with proxy failed: {e}")
        except Exception as e:
            logger.error(f"TikTok unexpected error with proxy: {e}")

        cleanup_temp_cookies()
        return None


# ==================== Watermark ====================

def add_watermark(
    input_path: str,
    output_path: Optional[str] = None,
    text: str = "tg: @django_media_helper_bot",
    fontsize: int = 20,
    opacity: float = 0.7
) -> Optional[str]:
    """
    Добавляет текстовый водяной знак на видео.
    
    Args:
        input_path: Путь к исходному видео
        output_path: Путь для сохранения (если None, создаётся автоматически)
        text: Текст водяного знака
        fontsize: Размер шрифта
        opacity: Прозрачность (0.0 - 1.0)
    
    Returns:
        Путь к видео с водяным знаком или None при ошибке
    """
    if not os.path.isfile(input_path):
        logger.error(f"add_watermark: file not found: {input_path}")
        return None
    
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_wm{ext}"
    
    try:
        # FFmpeg команда для добавления текста в правый нижний угол
        cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-vf', f"drawtext=text='{text}':fontsize={fontsize}:fontcolor=white@{opacity}:x=w-tw-10:y=h-th-10:shadowcolor=black@0.5:shadowx=1:shadowy=1",
            '-codec:a', 'copy',
            '-preset', 'ultrafast',
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0 and os.path.isfile(output_path):
            logger.info(f"Watermark added successfully: {output_path}")
            return output_path
        else:
            logger.error(f"FFmpeg watermark failed: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg watermark timeout")
        return None
    except Exception as e:
        logger.error(f"Error adding watermark: {e}")
        return None


def add_watermark_if_needed(
    input_path: str,
    add_watermark_flag: bool,
    delete_original: bool = True
) -> str:
    """
    Добавляет водяной знак если нужно и возвращает путь к финальному файлу.
    
    Args:
        input_path: Путь к исходному видео
        add_watermark_flag: Нужно ли добавлять водяной знак
        delete_original: Удалять ли оригинал после добавления водяного знака
    
    Returns:
        Путь к финальному видео (с водяным знаком или без)
    """
    if not add_watermark_flag:
        return input_path
    
    watermarked_path = add_watermark(input_path)
    
    if watermarked_path and os.path.isfile(watermarked_path):
        if delete_original and input_path != watermarked_path:
            try:
                os.remove(input_path)
            except Exception as e:
                logger.warning(f"Could not delete original file: {e}")
        return watermarked_path
    
    # Если не получилось добавить водяной знак, возвращаем оригинал
    return input_path


def download_youtube_sync(link):
    return asyncio.run(download_from_youtube(link))

def get_audio_from_youtube_sync(link):
    return asyncio.run(get_audio_from_youtube(link))

def convert_to_audio_sync(path):
    return asyncio.run(convert_to_audio(path))


# ==================== Music Recognition (Shazam) ====================

async def recognize_music(audio_path: str) -> Optional[Dict[str, Any]]:
    """
    Распознать музыку из аудиофайла с помощью Shazam.
    
    Args:
        audio_path: Путь к аудиофайлу (mp3, ogg, wav, m4a и др.)
    
    Returns:
        Словарь с информацией о треке или None если не найдено:
        {
            'title': str,
            'artist': str,
            'album': str,
            'year': str,
            'cover_url': str,
            'shazam_url': str,
            'apple_music_url': str,
            'spotify_url': str,
            'youtube_query': str  # Для поиска на YouTube
        }
    """
    try:
        from shazamio import Shazam
        
        shazam = Shazam()
        result = await shazam.recognize(audio_path)
        
        if not result or 'track' not in result:
            logger.info(f"Shazam: track not found for {audio_path}")
            return None
        
        track = result['track']
        
        # Извлекаем основную информацию
        title = track.get('title', 'Unknown')
        artist = track.get('subtitle', 'Unknown Artist')
        
        # Извлекаем метаданные
        sections = track.get('sections', [])
        album = None
        year = None
        
        for section in sections:
            if section.get('type') == 'SONG':
                metadata = section.get('metadata', [])
                for meta in metadata:
                    if meta.get('title') == 'Album':
                        album = meta.get('text')
                    elif meta.get('title') == 'Released':
                        year = meta.get('text')
        
        # Получаем обложку
        images = track.get('images', {})
        cover_url = images.get('coverarthq') or images.get('coverart')
        
        # Получаем ссылки
        shazam_url = track.get('url')
        
        # Ищем ссылки на стриминговые сервисы
        apple_music_url = None
        spotify_url = None
        
        hub = track.get('hub', {})
        providers = hub.get('providers', [])
        for provider in providers:
            if provider.get('type') == 'SPOTIFY':
                actions = provider.get('actions', [])
                for action in actions:
                    if action.get('type') == 'uri':
                        spotify_url = action.get('uri')
            elif provider.get('type') == 'APPLEMUSIC':
                actions = provider.get('actions', [])
                for action in actions:
                    if action.get('type') == 'uri':
                        apple_music_url = action.get('uri')
        
        # Формируем поисковый запрос для YouTube
        youtube_query = f"{artist} - {title}"
        
        logger.info(f"Shazam: found '{title}' by '{artist}'")
        
        return {
            'title': title,
            'artist': artist,
            'album': album,
            'year': year,
            'cover_url': cover_url,
            'shazam_url': shazam_url,
            'apple_music_url': apple_music_url,
            'spotify_url': spotify_url,
            'youtube_query': youtube_query
        }
        
    except ImportError:
        logger.error("shazamio not installed. Run: pip install shazamio")
        return None
    except Exception as e:
        logger.error(f"Error recognizing music: {e}")
        return None


async def recognize_and_download(audio_path: str, output_dir: str = "./audio/shazam") -> Optional[Dict[str, Any]]:
    """
    Распознать музыку и скачать трек с YouTube.
    
    Args:
        audio_path: Путь к аудиофайлу для распознавания
        output_dir: Директория для сохранения
    
    Returns:
        Словарь с информацией о треке и путём к скачанному файлу:
        {
            'recognized': {...},  # Результат распознавания
            'audio_file': str,    # Путь к скачанному файлу
            'thumbnail': str      # Путь к обложке (если есть)
        }
    """
    # Распознаём трек
    recognized = await recognize_music(audio_path)
    
    if not recognized:
        return None
    
    # Ищем на YouTube
    query = recognized['youtube_query']
    search_results = search_videos(query, max_results=1)
    
    if not search_results:
        logger.warning(f"No YouTube results for: {query}")
        return {
            'recognized': recognized,
            'audio_file': None,
            'thumbnail': None
        }
    
    # Скачиваем первый результат
    video = search_results[0]
    youtube_url = f"https://www.youtube.com/watch?v={video['id']}"
    
    result = await get_audio_from_youtube(youtube_url, path=output_dir)
    
    if result:
        return {
            'recognized': recognized,
            'audio_file': f"{output_dir}/{result['audio']}",
            'thumbnail': result.get('thumbnail')
        }
    
    return {
        'recognized': recognized,
        'audio_file': None,
        'thumbnail': None
    }


if __name__ == "__main__":
    print("Welcome to audio/video helper!")
    print("To download youtube video input 1\nTo extract audio from video input 2\nTo download audio from youtube "
          "input 3\nTo download reels from instagram input 4\nTo change audio on video input 5\nTo download TikTok input 6 \n"
          "To find yotube video input 7 \n"
          "To get youtube video formats input 8 \n"
          "To download reels V2 (with auto reencode for iOS) input 9 \n"
          "To test watermark on video input 10 \n")
    choise = int(input("Chose variant: "))
    if choise == 1:
        link = input("Give me the link: ")
        download_youtube_sync(link)
        print("Done!")
    elif choise == 2:
        path = input("Give me path to the video file: ")
        convert_to_audio_sync(path)
        print("Done!")
    elif choise == 3:
        link = input("Give me the link: ")
        get_audio_from_youtube_sync(link)
        print("Done!")
    elif choise == 4:
        link = input("Give me the link: ")
        _download_instagram_reels_sync(link)
        print("Done!")
    elif choise == 5:
        replace_audio("подъем коленей высоко.mov", "Lou Reed - Perfect Day (Official Audio).mp3")
        print("Done!")
    elif choise == 6:
        link = input("Give me the link: ")
        downloader = TikTokDownloader(save_path='videos/tiktok')
        res = downloader.download_video(link)
        print(res)
        #downloader.list_formats(link)
    elif choise == 7:
        text = input("Give me what u want to find: ")
        res = search_videos(text)
        for item in res:
            print(f"{item['title']}\n - https://www.youtube.com/watch?v={item['id']}\n")
    elif choise == 8:
        link = input("Give me the link: ")
        formats = get_video_formats(link)
        res = format_formats_for_display(formats)
        print(res)
    elif choise == 9:
        link = input("Give me the Instagram reel link: ")
        result = _download_instagram_reels_sync_v2(link)
        if result:
            print(f"Done! Video saved to: {result}")
        else:
            print("Failed to download video")
    elif choise == 10:
        print("\n=== Watermark Test ===")
        print("1. Download YouTube video with watermark")
        print("2. Download TikTok with watermark")
        print("3. Download Instagram Reels with watermark")
        print("4. Add watermark to existing video file")
        sub_choice = int(input("Choose: "))
        
        if sub_choice == 1:
            link = input("Give me YouTube link: ")
            print("Downloading video...")
            filename = download_youtube_sync(link)
            if filename:
                video_path = f"./videos/youtube/{filename}"
                print(f"Downloaded: {video_path}")
                print("Adding watermark...")
                result = add_watermark(video_path)
                if result:
                    print(f"✅ Watermarked video saved to: {result}")
                    print(f"Original (no watermark): {video_path}")
                else:
                    print("❌ Failed to add watermark")
            else:
                print("❌ Failed to download video")
        elif sub_choice == 2:
            link = input("Give me TikTok link: ")
            print("Downloading video...")
            downloader = TikTokDownloader(save_path='videos/tiktok')
            filename = downloader.download_video(link)
            if filename:
                video_path = f"./videos/tiktok/{filename}"
                print(f"Downloaded: {video_path}")
                print("Adding watermark...")
                result = add_watermark(video_path)
                if result:
                    print(f"✅ Watermarked video saved to: {result}")
                    print(f"Original (no watermark): {video_path}")
                else:
                    print("❌ Failed to add watermark")
            else:
                print("❌ Failed to download video")
        elif sub_choice == 3:
            link = input("Give me Instagram Reels link: ")
            print("Downloading video...")
            video_path = _download_instagram_reels_sync(link)
            if video_path:
                print(f"Downloaded: {video_path}")
                print("Adding watermark...")
                result = add_watermark(video_path)
                if result:
                    print(f"✅ Watermarked video saved to: {result}")
                    print(f"Original (no watermark): {video_path}")
                else:
                    print("❌ Failed to add watermark")
            else:
                print("❌ Failed to download video")
        elif sub_choice == 4:
            path = input("Give me path to video file: ")
            if os.path.isfile(path):
                print("Adding watermark...")
                result = add_watermark(path)
                if result:
                    print(f"✅ Watermarked video saved to: {result}")
                else:
                    print("❌ Failed to add watermark")
            else:
                print(f"❌ File not found: {path}")
        else:
            print("Invalid choice")
    else:
        print("I don`t know what u wanna do!")
