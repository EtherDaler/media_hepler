import asyncio
import os
import time
import requests
import os
import base64
import yt_dlp
import exifread
import subprocess
import fnmatch
import ffmpeg
import subprocess
import random
import shlex
import re
import json

from moviepy import VideoFileClip, AudioFileClip, concatenate_audioclips
from pytube import YouTube
from instascrape.scrapers import Reel
from pprint import pprint
from data.config import PROXYS

from PIL import Image, ExifTags


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
        print(f"Warning: Video is still larger than {max_size_mb} MB.")

    if os.path.isfile(f"{path}/{input_file}"):
        os.remove(f"{path}/{input_file}")
    
    return output_file


def compress_video(input_path, output_path, target_size_mb=50):
    # Получаем размер файла в мегабайтах
    file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
    
    # Если размер больше указанного порога
    if file_size_mb > target_size_mb:
        print(f"Видео {input_path} имеет размер {file_size_mb:.2f} МБ, что больше {target_size_mb} МБ.")
        print("Запуск сжатия...")

        # Открываем видеофайл с помощью moviepy
        video = VideoFileClip(input_path)

        # Пример сжатия, уменьшив битрейт
        video.write_videofile(output_path, bitrate="500k", codec="libx264", audio_codec="aac")
        
        print(f"Видео сжато и сохранено как {output_path}")
        if os.path.isfile(f"{input_path}"):
            os.remove(f"{input_path}")
        return True
    else:
        print(f"Размер видео {input_path} ({file_size_mb:.2f} МБ) меньше {target_size_mb} МБ. Сжатие не требуется.")
        return False
    

def get_yt_dlp_conf(path, proxy=False):
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/best[height<=1080]',
        'outtmpl': f'{path}/%(title)s.%(ext)s',
        'noplaylist': True,
        'verbose': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'skip': ['dash', 'hls']
            }
        },
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'socket_timeout': 30,
        'retries': 3,
        'fragment_retries': 10,
        'skip_unavailable_fragments': True,
        'continue_dl': True,
        'cookiefile': '/root/media_helper/cookies.txt'
    }
    if proxy:
        proxy_url = get_random_proxy()
        ydl_opts['proxy'] = proxy_url
    return ydl_opts


async def download_from_youtube(link, path='./videos/youtube', out_format="mp4", res="720p", filename=None):
    ydl_opts = get_yt_dlp_conf(path)
    os.makedirs(path, exist_ok=True)
    # Функция для выполнения yt-dlp
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(link, download=True))
    except Exception as e:
        print(f"Error downloading video: {e}")
        try:
            ydl_opts_alt = ydl_opts.copy()
            ydl_opts_alt['format'] = 'best'
            ydl_opts_alt['extractor_args'] = {
                'youtube': {
                    'player_client': ['android_embedded', 'tv_embedded'],
                    'skip': ['dash', 'hls']
                }
            }
            result = await loop.run_in_executor(
                None, 
                lambda: yt_dlp.YoutubeDL(ydl_opts_alt).extract_info(link, download=True)
            )
        except Exception as alt_e:
            print(f"❌ Failed without proxy: {alt_e}")
            try:
                print("🔄 Trying with proxies...")
                ydl_opts = get_yt_dlp_conf(path, proxy=True)
                result = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(link, download=True))
            except Exception as last_e:
                print(f"❌ Failed even with proxy: {last_e}")
                result = None

    if result is not None:
        replacements = {
            '/': '⧸',     # Прямой слэш
            '\\': '⧹',    # Обратный слэш
            '|': '｜',     # Вертикальная черта
            '?': '？',     # Вопросительный знак
            '*': '＊',     # Звёздочка
            ':': '：',     # Двоеточие
            '"': '＂',     # Двойные кавычки
            '<': '＜',     # Меньше
            '>': '＞',     # Больше
        }
        video_title = result['title'].strip()
        for old, new in replacements.items():
            video_title = video_title.replace(old, new)
        video_title = re.sub(r'[\x00-\x1F\x7F]', '', video_title)
        video_filename = f"{video_title}.{result['ext']}"
        return video_filename
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


def download_youtube_sync(link):
    return asyncio.run(download_from_youtube(link))

def get_audio_from_youtube_sync(link):
    return asyncio.run(get_audio_from_youtube(link))

def convert_to_audio_sync(path):
    return asyncio.run(convert_to_audio(path))

if __name__ == "__main__":
    print("Welcome to audio/video helper!")
    print("To download youtube video input 1\nTo extract audio from video input 2\nTo download audio from youtube "
          "input 3\nTo download reels from instagram input 4\nTo change audio on video 5\n")
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
    else:
        print("I don`t know what u wanna do!")
