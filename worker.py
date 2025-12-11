import asyncio
import os
import os
import base64
import yt_dlp
import subprocess
import fnmatch
import subprocess
import random
import re
import requests
import json
import logging
import urllib

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
    

def get_yt_dlp_conf(path, proxy=None, player_client=["web"], player_js_version='actual'):
    """
    Возвращает ydl_opts. Если proxy_url задан — он подставляется (нормализуется).
    """
    ydl_opts = {
        'format': 'bestvideo[height<=1080]+bestaudio/best',
        'outtmpl': f'{path}/%(title)s.%(ext)s',
        'noplaylist': True,
        'verbose': False,  # уменьшаем логирование
        'quiet': True,     # уменьшаем логирование
        'extractor_args': {
            'youtube': {
                'player_client': player_client,
                'player_js_version': player_js_version
            }
        },
        'http_chunk_size': 0,   # отключаем chunked/Range-запросы
        'nopart': True,         # не использовать .part файлы
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'socket_timeout': 30,
        'retries': 3,
        'fragment_retries': 10,
        'nocheckcertificate': True,
        'skip_unavailable_fragments': True,
        'continue_dl': True,
        'cookiefile': DEFAULT_YT_COOKIE
    }

    if proxy:
        proxy_url = list(proxy.keys())[0]
        proxy_cookie = proxy[proxy_url]
        p = str(proxy_url).rstrip('/')
        ydl_opts['proxy'] = p
        ydl_opts['cookiefile'] = proxy_cookie
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

    try:
        info = await loop.run_in_executor(None, lambda: extract_info_sync(ydl_opts, link, download=False))
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

    # 1) no-proxy, web-like
    try:
        ydl_opts = get_yt_dlp_conf(path, proxy=None, player_client=['default', 'web_safari'])
        chosen_format = await get_format_for_youtube(ydl_opts, link, format_id, res)
        ydl_opts['format'] = chosen_format
        logger.info(f"Chosen format (no-proxy): {chosen_format}")
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
                ydl_opts_p = get_yt_dlp_conf(path, proxy=proxy, player_client=['default', 'web_safari'])
                chosen_format_p = await get_format_for_youtube(ydl_opts_p, link, format_id, res)
                ydl_opts_p['format'] = chosen_format_p
                logger.info(f"Chosen format (proxy): {chosen_format_p}")
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
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'cookiefile': DEFAULT_YT_COOKIE
    }
    
    try:
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
            
    except Exception as e:
        logger.error(f"Ошибка получения форматов: {e}")
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
    audio = None
    video = await download_from_youtube(link)
    video_path = "./videos/youtube"
    rev = video[::-1]
    tmp = rev.find('.')
    filename = rev[:tmp:-1]
    if video is None:
        print("Произошла ошибка при загрузке видео")
        return None
    os.makedirs(path, exist_ok=True)
    try:
        audio = await convert_to_audio(f"{video_path}/{video}", path, out_format, filename)
    except Exception as e:
        print("Error:", e)
        if os.path.isfile(f"{video_path}/{video}"):
            os.remove(f"{video_path}/{video}")
    if os.path.isfile(f"{video_path}/{video}"):
        os.remove(f"{video_path}/{video}")
    return audio

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
    i = reels_url.find("reel")
    j = reels_url[i+5:].find('/')
    filename = reels_url[i+5:i+5+j]
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
                'outtmpl': f"{path}/{filename}.mp4",
                'cookiefile': tmp_cookie_path,  # Используем временную копию
                'format': 'bestvideo+bestaudio/best',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/117.0'
                }
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
                'outtmpl': temp_file,
                'cookiefile': tmp_cookie_path,
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
                },
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
        'cookiefile': DEFAULT_YT_COOKIE
    }
    video_id = extract_video_id(url)
    video_info = None
    try:
        video_info = get_yt_info(ydl_opts, url, video_id)
    except Exception as e:
        logger.error(f"Got Error while get_youtube_video_info: {e}. \nTry with Proxy...")
        proxy = get_random_proxy()
        proxy_url = list(proxy.keys())[0]
        proxy_cookie = proxy[proxy_url]
        p = str(proxy_url).rstrip('/')
        ydl_opts['proxy'] = p
        ydl_opts['cookiefile'] = proxy_cookie
        ydl_opts['socket_timeout'] = 150
        # ставим env на всякий случай, очищаем HTTP_PROXY/HTTPS_PROXY
        os.environ['ALL_PROXY'] = p
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        video_info = get_yt_info(ydl_opts, url, video_id)
    return video_info


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

    def download_video(self, video_url: str, custom_name: Optional[str] = None) -> Optional[str]:
        if not self.validate_url(video_url):
            logger.error("Error: Invalid TikTok URL")
            return None

        filename = self.get_filename(video_url, custom_name)
        output_path = os.path.join(self.save_path, filename)

        ydl_opts = {
            'outtmpl': output_path,
            # скачиваем лучший видеопоток + лучший аудиопоток, иначе возьмёт комбинированный best
            'format': 'bestvideo+bestaudio/best',
            'noplaylist': True,
            'quiet': False,
            'verbose': True,
            #'progress_hooks': [self.progress_hook],
            'cookiefile': '/root/media_helper/tiktok_cookie.txt',
            # чтобы явно слить в mp4 (если нужно)
            'merge_output_format': 'mp4',
            # если веб-версия даёт только демо (без звука), убрать webpage_download
            # 'extractor_args': {'tiktok': {'webpage_download': False}},
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
                logger.info(f"\nVideo successfully downloaded: {output_path}")
            return filename
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Error downloading video: {str(e)}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")

        return None


def download_youtube_sync(link):
    return asyncio.run(download_from_youtube(link))

def get_audio_from_youtube_sync(link):
    return asyncio.run(get_audio_from_youtube(link))

def convert_to_audio_sync(path):
    return asyncio.run(convert_to_audio(path))

if __name__ == "__main__":
    print("Welcome to audio/video helper!")
    print("To download youtube video input 1\nTo extract audio from video input 2\nTo download audio from youtube "
          "input 3\nTo download reels from instagram input 4\nTo change audio on video input 5\nTo download TikTok input 6 \n"
          "To find yotube video input 7 \n"
          "To get youtube video formats input 8 \n"
          "To download reels V2 (with auto reencode for iOS) input 9 \n")
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
    else:
        print("I don`t know what u wanna do!")
