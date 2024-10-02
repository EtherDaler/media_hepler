import subprocess
import os
import sys
import time
import requests
import os
import base64
import math
import datetime
import instaloader

from moviepy.editor import VideoFileClip
from pytube import YouTube
from instascrape.scrapers import Reel


def generate_session():
    return base64.b64encode(os.urandom(16))


def download_from_youtube(link, path='./videos/youtube', out_format="mp4", res="720p", filename=None):
    yt = YouTube(link)
    video = yt.streams.filter(progressive=True, file_extension=out_format, resolution=res)[0]
    if filename is None:
        filename = f"{yt.streams[0].title}.{out_format}"
    ind = 1
    while os.path.isfile(f"{path}/{filename}"):
        filename = f"{yt.streams[0].title}({ind}).{out_format}"
    video.download(path, filename)
    return [path, filename]


def convert_to_audio(video, path='./audio/converted', out_format="mp3", filename=None):
    if filename is None:
        filename, ext = os.path.splitext(video)
    clip = VideoFileClip(video)
    ind = 1
    while os.path.isfile(f"{path}/{filename}.{out_format}"):
        filename = filename + f"({ind})"
    clip.audio.write_audiofile(f"{path}/{filename}.{out_format}")
    clip.close()


def get_audio_from_youtube(link, path="./audio/youtube", out_format="mp3", filename=None):
    """
    video = download_from_youtube(link)
    if filename is None:
        filename, ext = os.path.splitext(video[1])
    try:
        convert_to_audio(f"{video[0]}/{video[1]}", path, out_format, filename)
    except Exception as e:
        print("Error:", e)
        if os.path.isfile(f"{video[0]}/{video[1]}"):
            os.remove(f"{video[0]}/{video[1]}")
    if os.path.isfile(f"{video[0]}/{video[1]}"):
        os.remove(f"{video[0]}/{video[1]}")
    yt = YouTube(link)
    if filename is None:
        filename = f"{yt.streams[0].title}.{out_format}"
    ind = 1
    while os.path.isfile(f"{path}/{filename}"):
        filename = f"{yt.streams[0].title}({ind}).{out_format}"
    video.download(path, filename)
    return [path, filename]
    """
    yt = YouTube(link)
    audio = yt.streams.filter(only_audio=True).all()

    if filename is None:
        filename = f"{yt.streams[0].title}.{out_format}"
    ind = 1
    while os.path.isfile(f"{path}/{filename}"):
        filename = f"{yt.streams[0].title}({ind}).{out_format}"
    audio[0].download(path, filename)
    return [path, filename]


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
