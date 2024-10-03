import asyncio
import os
import time
import requests
import os
import base64
import yt_dlp

from moviepy.editor import VideoFileClip
from pytube import YouTube
from instascrape.scrapers import Reel


def generate_session():
    return base64.b64encode(os.urandom(16))


async def download_from_youtube(link, path='./videos/youtube', out_format="mp4", res="720p", filename=None):
    po_token = "MnTT_c32vPYUIdPFFRKfxFLG21j22_tHNgtcxsnyI-BBLV8qkeyHs5ymawmenUy_VXvcmiGSA6BKQOwOf97daFTOMr0L_WimcA4MsiCKOaeiCiySQd0Ia15Asyt8gsbyVM9jsjIqjHnuFqYJPqAMaqeT1oPnuA=="
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

    audio_title = result['title']
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



def download_reel(url, path="./videos/insta"):
    sessionId = generate_session().decode('utf-8')  # Преобразуем байтовую строку в обычную строку
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)\
        AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.74 \
        Safari/537.36 Edg/79.0.309.43",
        "cookie": f'sessionid={sessionId};'
    }
    insta_reel = Reel(url)

    # Используем функцию scrape с заголовками
    insta_reel.scrape(headers=headers, session=requests.Session())

    # Скачиваем видео
    insta_reel.download(fp=f"{path}/reel{int(time.time())}.mp4")
 


if __name__ == "__main__":
    print("Welcome to audio/video helper!")
    print("To download youtube video input 1\n To extract audio from video input 2\n To download audio from youtube "
          "input 3\n To download reels from instagram input 4\n")
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
        download_reel(link)
        print("Done!")
    else:
        print("I don`t know what u wanna do!")
