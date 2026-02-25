import os
from datetime import datetime
import logging
import yt_dlp

logger = logging.getLogger(__name__)


def download_pin(url, path='./videos/pinterest', filename=None, out_format='mp4'):
    """
    Скачивает видео с Pinterest используя yt-dlp.
    Поддерживает как полные ссылки pinterest.com/pin/, так и короткие pin.it/
    """
    os.makedirs(path, exist_ok=True)
    
    # Проверка URL
    if "pinterest" not in url and "pin.it" not in url:
        logger.error(f"Invalid Pinterest URL: {url}")
        return None
    
    # Генерируем уникальное имя файла
    if not filename:
        filename = datetime.now().strftime("pin_%Y%m%d_%H%M%S")
    
    # Убедимся, что имя файла уникальное
    base_filename = filename
    ind = 1
    while os.path.isfile(f"{path}/{filename}.{out_format}"):
        filename = f"{base_filename}_{ind}"
        ind += 1
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{path}/{filename}.%(ext)s',
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'merge_output_format': 'mp4',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        },
        'socket_timeout': 30,
        'retries': 3,
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }
    
    try:
        logger.info(f"Downloading Pinterest video: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if info:
                # Находим скачанный файл
                downloaded_file = None
                for ext in ['mp4', 'webm', 'mkv', 'avi']:
                    potential_file = f"{path}/{filename}.{ext}"
                    if os.path.isfile(potential_file):
                        downloaded_file = potential_file
                        break
                
                if downloaded_file:
                    logger.info(f"Pinterest video downloaded successfully: {filename}")
                    return filename
                else:
                    # Ищем файл по паттерну
                    for f in os.listdir(path):
                        if f.startswith(filename) and f.endswith(('.mp4', '.webm', '.mkv')):
                            # Возвращаем имя без расширения
                            return os.path.splitext(f)[0]
                    
                    logger.error("Downloaded file not found")
                    return None
            else:
                logger.error("Could not extract video info - this might be an image pin, not a video")
                return None
                
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "no video" in error_msg.lower() or "image" in error_msg.lower():
            logger.error("This is an image pin, not a video")
        else:
            logger.error(f"Pinterest download error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading Pinterest: {e}")
        return None
