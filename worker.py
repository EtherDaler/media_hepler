import asyncio
import os
import time
import requests
import os
import base64
import yt_dlp
import exifread
import subprocess

from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_audioclips
from pytube import YouTube
from instascrape.scrapers import Reel
from pprint import pprint

import ffmpeg
from PIL import Image, ExifTags



def generate_session():
    return base64.b64encode(os.urandom(16))

def get_name_from_path(path: str):
    filename = path.split("/")
    filename = filename[-1]
    filename = filename.split(".")
    filename = filename[0]
    return filename


async def download_from_youtube(link, path='./videos/youtube', out_format="mp4", res="720p", filename=None):
    po_token = "MnTT_c32vPYUIdPFFRKfxFLG21j22_tHNgtcxsnyI-BBLV8qkeyHs5ymawmenUy_VXvcmiGSA6BKQOwOf97daFTOMr0L_WimcA4MsiCKOaeiCiySQd0Ia15Asyt8gsbyVM9jsjIqjHnuFqYJPqAMaqeT1oPnuA=="
    bad_characters = '\/:*?"<>|'
    ydl_opts = {
        'format': 'best',  # Выбор лучшего доступного качества
        'outtmpl': f'{path}/%(title)s.%(ext)s',  # Шаблон имени файла
        'noplaylist': True,  # Скачивание только одного видео, если это плейлист
        'cookiefile': './cookies.txt'
    }
    os.makedirs(path, exist_ok=True)
    # Функция для выполнения yt-dlp
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(link, download=True))

    audio_title = result['title'].replace('/', u"\u2215")
    audio_filename = f"{audio_title}.{out_format}"  # Форматирование имени файла
    return audio_filename if result is not None else None


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
    ydl_opts = {
        'outtmpl': f"{path}/{filename}.mp4",  # Имя файла для сохранения
        'cookiefile': './instagram.txt',  # Путь к файлу с cookies
        'format': 'bestvideo+bestaudio/best'
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([reels_url])
        return f"{path}/{filename}.mp4"
    except:
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

    

if __name__ == "__main__":
    print("Welcome to audio/video helper!")
    print("To download youtube video input 1\nTo extract audio from video input 2\nTo download audio from youtube "
          "input 3\nTo download reels from instagram input 4\nTo change audio on video 5\n")
    choise = int(input("Chose variant: "))
    if choise == 1:
        link = input("Give me the link: ")
        download_from_youtube(link)
        print("Done!")
    elif choise == 2:
        path = input("Give me path to the video file: ")
        convert_to_audio(path)
        print("Done!")
    elif choise == 3:
        link = input("Give me the link: ")
        get_audio_from_youtube(link)
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
