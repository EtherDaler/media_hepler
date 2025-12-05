import argparse
import os
import requests

from data.config import BOT_TOKEN
from bot_commands import send_video_through_api
from worker import get_video_resolution_moviepy


def send_message_to_chat(message, chat_id):
    """Отправка текстового сообщения в чат"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print(f"Failed to send message. Error: {response.text}")


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        Скрипт для отправки сообщений и видео в Telegram.
        """
    )
    parser.add_argument(
        "chat_id",
        help="Id чата"
    )
    parser.add_argument(
        "mode",
        choices=["message", "video"],
        help="Режим: message или video"
    )
    parser.add_argument(
        "--message", "-m",
        default="",
        help="Текст сообщения (для режима message)"
    )
    parser.add_argument(
        "--video", "-v",
        help="Путь к видео (для режима video)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "message":
        if not args.message:
            print("Error: --message is required for message mode")
            return
        send_message_to_chat(args.message, args.chat_id)
    elif args.mode == "video":
        if not args.video:
            print("Error: --video is required for video mode")
            return
        if not os.path.isfile(args.video):
            print(f"Error: Video file not found: {args.video}")
            return
        
        # Автоматически получаем ширину и высоту видео
        width, height = get_video_resolution_moviepy(args.video)
        print(f"Video resolution: {width}x{height}")
        
        send_video_through_api(args.chat_id, args.video, width, height)


if __name__ == "__main__":
    main()