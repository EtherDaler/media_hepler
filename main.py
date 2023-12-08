import subprocess
import os
import sys
import time

from moviepy.editor import VideoFileClip
from pytube import YouTube


def download_from_youtube(link, path='./videos', out_format="mp4", res="720p", filename=None):
    yt = YouTube(link)
    video = yt.streams.filter(progressive=True, file_extension=out_format, resolution=res)[0]
    if filename is None:
        filename = f"{yt.streams[0].title}.{out_format}"
    ind = 1
    while os.path.isfile(f"{path}/{filename}"):
        filename = f"{yt.streams[0].title}({ind}).{out_format}"
    video.download(path, filename)
    return [path, filename]


def convert_to_audio(video, path='./audio', out_format="mp3", filename=None):
    if filename is None:
        filename, ext = os.path.splitext(video)
    clip = VideoFileClip(video)
    ind = 1
    while os.path.isfile(f"{path}/{filename}.{out_format}"):
        filename = filename + f"({ind})"
    clip.audio.write_audiofile(f"{path}/{filename}.{out_format}")
    clip.close()


def get_audio_from_youtube(link, path="./audio", out_format="mp3", filename=None):
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


if __name__ == "__main__":
    print("Welcome to audio/video helper!")
    print("To download youtube video input 1\n To extract audio from video input 2\n To download audio from youtube "
          "input 3\n")
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
    else:
        print("I don`t know what u wanna do!")
