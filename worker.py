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
import json
import logging

from datetime import datetime
from typing import Optional, Dict, Any
from moviepy import VideoFileClip, AudioFileClip, concatenate_audioclips
from youtube_search import YoutubeSearch
from data.config import PROXYS


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
    

def get_yt_dlp_conf(path, proxy_url=None, player_client='web'):
    """
    Возвращает ydl_opts. Если proxy_url задан — он подставляется (нормализуется).
    """
    ydl_opts = {
        'format': 'bestvideo[height<=1080]+bestaudio/best',
        'outtmpl': f'{path}/%(title)s.%(ext)s',
        'noplaylist': True,
        'verbose': True,
        'quiet': False,
        'extractor_args': {
            'youtube': {
                'player_client': [player_client],
                'skip': ['dash', 'hls']
            }
        },
        'http_chunk_size': 0,   # отключаем chunked/Range-запросы
        'nopart': True,         # не использовать .part файлы
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'socket_timeout': 30,
        'retries': 3,
        'fragment_retries': 10,
        'skip_unavailable_fragments': True,
        'continue_dl': True,
        'cookiefile': '/root/media_helper/cookies.txt'
    }

    if proxy_url:
        p = str(proxy_url).rstrip('/') + '/'
        ydl_opts['proxy'] = p
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


async def download_from_youtube(link, path='./videos/youtube', out_format="mp4", res="720p", filename=None):
    """
    Логика:
    1) Пытаться скачать БЕЗ прокси (player_client=web).
    2) Если неудача — пробовать другие clients (android_embedded, tv_embedded) без прокси.
    3) Если всё ещё неудача — попытки повторяются с прокси (если get_random_proxy() даёт прокси).
    Возвращает имя файла (строку) или None.
    """
    os.makedirs(path, exist_ok=True)
    loop = asyncio.get_event_loop()

    # helper: попытка с указанными ydl_opts (download=False чтобы получить info, затем download=True)
    def extract_info_sync(opts, url, download=False):
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=download)

    # шаги без прокси
    attempts = []

    # 1) Первый базовый вариант: web client, try to choose format 18 if present
    try:
        logger.info("Attempt: no-proxy, client=web -> extract_info")
        ydl_opts = get_yt_dlp_conf(path, proxy_url=None, player_client='web')
        info = await loop.run_in_executor(None, lambda: extract_info_sync(ydl_opts, link, download=False))
        formats = info.get('formats', [])
        # выбрать формат: предпочтение 18 (как в CLI)
        chosen_format = None
        for f in formats:
            if f.get('format_id') == '18':
                chosen_format = '18'
                break
        if not chosen_format:
            # fallback: лучший <= requested res (или best)
            max_h = 1080
            if isinstance(res, str) and res.endswith('p'):
                try:
                    max_h = int(res[:-1])
                except Exception:
                    pass
            cand = [f for f in formats if (f.get('height') or 0) <= max_h and f.get('vcodec') != 'none']
            if cand:
                cand_sorted = sorted(cand, key=lambda x: (x.get('height') or 0, x.get('tbr') or 0), reverse=True)
                chosen_format = cand_sorted[0].get('format_id')
            else:
                chosen_format = 'best'
        logger.info("Chosen format (no-proxy):", chosen_format)
        ydl_opts['format'] = chosen_format

        logger.info("Downloading (no-proxy) with chosen format...")
        result = await loop.run_in_executor(None, lambda: extract_info_sync(ydl_opts, link, download=True))
    except Exception as e_no_proxy:
        logger.error("No-proxy primary attempt failed:", repr(e_no_proxy))
        result = None
        # 2) Фоллбек: другие clients без прокси
        try:
            logger.info("Fallback: no-proxy, try clients android_embedded, tv_embedded")
            ydl_opts_alt = get_yt_dlp_conf(path, proxy_url=None, player_client='android_embedded')
            ydl_opts_alt['format'] = 'best'
            result = await loop.run_in_executor(None, lambda: extract_info_sync(ydl_opts_alt, link, download=True))
        except Exception as e_alt_no_proxy:
            logger.error("Fallback no-proxy failed:", repr(e_alt_no_proxy))
            result = None

    # 3) Если без прокси всё не получилось -> пробуем с прокси (если есть)
    if result is None:
        proxy = None
        try:
            proxy = get_random_proxy()  # твоя функция должна вернуть строку или None
        except Exception as e:
            logger.error("get_random_proxy failed:", repr(e))
            proxy = None

        if proxy:
            try:
                logger.info("Attempt: with-proxy, client=web -> extract_info")
                ydl_opts_p = get_yt_dlp_conf(path, proxy_url=proxy, player_client='web')
                info_p = await loop.run_in_executor(None, lambda: extract_info_sync(ydl_opts_p, link, download=False))
                formats_p = info_p.get('formats', [])
                chosen_format_p = None
                for f in formats_p:
                    if f.get('format_id') == '18':
                        chosen_format_p = '18'
                        break
                if not chosen_format_p:
                    max_h = 1080
                    if isinstance(res, str) and res.endswith('p'):
                        try:
                            max_h = int(res[:-1])
                        except Exception:
                            pass
                    cand = [f for f in formats_p if (f.get('height') or 0) <= max_h and f.get('vcodec') != 'none']
                    if cand:
                        cand_sorted = sorted(cand, key=lambda x: (x.get('height') or 0, x.get('tbr') or 0), reverse=True)
                        chosen_format_p = cand_sorted[0].get('format_id')
                    else:
                        chosen_format_p = 'best'
                logger.info("Chosen format (proxy):", chosen_format_p)
                ydl_opts_p['format'] = chosen_format_p

                logger.info("Downloading (with-proxy) with chosen format...")
                result = await loop.run_in_executor(None, lambda: extract_info_sync(ydl_opts_p, link, download=True))
            except Exception as e_with_proxy:
                logger.error("With-proxy attempt failed:", repr(e_with_proxy))
                result = None
            # last fallback with different client using proxy
            if result is None:
                try:
                    logger.info("Fallback (with-proxy): try android_embedded client")
                    ydl_opts_p2 = get_yt_dlp_conf(path, proxy_url=proxy, player_client='android_embedded')
                    ydl_opts_p2['format'] = 'best'
                    result = await loop.run_in_executor(None, lambda: extract_info_sync(ydl_opts_p2, link, download=True))
                except Exception as e_with_proxy_alt:
                    logger.error("With-proxy fallback failed:", repr(e_with_proxy_alt))
                    result = None

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


def search_videos(query, max_results=5):
    """Поиск видео по запросу"""
    try:
        results = YoutubeSearch(query, max_results=max_results).to_dict()
        return results
    except Exception as e:
        logging.error(f"Ошибка поиска: {e}")
        return []


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
    output_path = path_to_video.replace('.mp4', '_reencoded.mp4')
    command = [
        'ffmpeg', '-i', path_to_video, 
        '-c:v', 'libx264', '-c:a', 'aac', '-strict', 'experimental', 
        '-movflags', 'faststart', output_path
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path

def download_instagram_reels(reels_url):
    path = "./videos/reels"
    os.makedirs(path, exist_ok=True)
    i = reels_url.find("reel")
    j = reels_url[i+5:].find('/')
    filename = reels_url[i+5:i+5+j]
    while os.path.isfile(f"{path}/{filename}.mp4"):
        filename = filename + f"({ind})"
        ind += 1
    filename = filename.strip()
    cookies = ['0', '1', '2']
    while len(cookies) > 0:
        cookie = random.choice(cookies)
        try:
            ydl_opts = {
                'outtmpl': f"{path}/{filename}.mp4",  # Имя файла для сохранения
                'cookiefile': f'./instagram{cookie}.txt',  # Путь к файлу с cookies
                'format': 'bestvideo+bestaudio/best',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
                }
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([reels_url])
            return f"{path}/{filename}.mp4"
        except Exception as e:
            cookies.remove(cookie)
            print(e)
            print(f"Get another cookie: ./instagram{cookie}.txt")
    return None
    
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
          "To find yotube video input 7 \n")
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
        download_instagram_reels(link)
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
        text = input("Gimme what u want to find: ")
        res = search_videos(text)
        for item in res:
            print(f"{item['title']}\n - https://www.youtube.com/watch?v={item['id']}\n")
    else:
        print("I don`t know what u wanna do!")
