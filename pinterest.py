import os
import re
import json
import requests
from datetime import datetime
import logging
import yt_dlp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def download_via_scraping(url, path, filename):
    """Fallback метод - скачивание через парсинг страницы"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # Разрешаем редиректы для коротких ссылок
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
        if response.status_code != 200:
            logger.error(f"Failed to fetch page: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        video_url = None
        
        # Способ 1: ищем video тег
        video_tag = soup.find('video')
        if video_tag:
            video_url = video_tag.get('src')
            if not video_url:
                source = video_tag.find('source')
                if source:
                    video_url = source.get('src')
        
        # Способ 2: ищем в JSON данных на странице
        if not video_url:
            scripts = soup.find_all('script', type='application/json')
            for script in scripts:
                try:
                    if script.string:
                        data = json.loads(script.string)
                        # Ищем video URL в JSON
                        json_str = json.dumps(data)
                        # Ищем паттерны video URL
                        patterns = [
                            r'"V_720P":"([^"]+)"',
                            r'"V_EXP7":"([^"]+)"',
                            r'"video_url":"([^"]+)"',
                            r'"contentUrl":"([^"]+\.mp4[^"]*)"',
                        ]
                        for pattern in patterns:
                            match = re.search(pattern, json_str)
                            if match:
                                video_url = match.group(1).replace('\\u002F', '/')
                                break
                        if video_url:
                            break
                except (json.JSONDecodeError, TypeError):
                    continue
        
        # Способ 3: ищем в inline scripts
        if not video_url:
            for script in soup.find_all('script'):
                if script.string:
                    patterns = [
                        r'"V_720P"\s*:\s*"([^"]+)"',
                        r'"V_EXP7"\s*:\s*"([^"]+)"',
                        r'(https://v1\.pinimg\.com/videos/[^"]+\.mp4)',
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, script.string)
                        if match:
                            video_url = match.group(1).replace('\\u002F', '/')
                            break
                    if video_url:
                        break
        
        if not video_url:
            logger.error("Could not find video URL in page")
            return None
        
        # Скачиваем видео
        logger.info(f"Downloading video from: {video_url[:60]}...")
        video_response = requests.get(video_url, headers=headers, stream=True, timeout=60)
        
        if video_response.status_code == 200:
            output_path = f"{path}/{filename}.mp4"
            with open(output_path, 'wb') as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"Successfully downloaded via scraping: {filename}")
                return filename
            else:
                logger.error("Downloaded file is empty")
                return None
        else:
            logger.error(f"Failed to download video: {video_response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Scraping fallback error: {e}")
        return None


def download_pin(url, path='./videos/pinterest', filename=None, out_format='mp4'):
    """
    Скачивает видео с Pinterest.
    Сначала пробует yt-dlp, потом fallback на прямой парсинг.
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
    
    # Способ 1: yt-dlp
    ydl_opts = {
        'format': 'bestvideo*+bestaudio/best/bestvideo/bestaudio',
        'outtmpl': f'{path}/{filename}.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
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
        logger.info(f"Trying yt-dlp for Pinterest: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if info:
                # Находим скачанный файл
                for ext in ['mp4', 'webm', 'mkv', 'avi']:
                    potential_file = f"{path}/{filename}.{ext}"
                    if os.path.isfile(potential_file):
                        logger.info(f"Pinterest video downloaded via yt-dlp: {filename}")
                        return filename
                
                # Ищем файл по паттерну
                for f in os.listdir(path):
                    if f.startswith(filename) and f.endswith(('.mp4', '.webm', '.mkv')):
                        return os.path.splitext(f)[0]
                        
    except yt_dlp.utils.DownloadError as e:
        logger.warning(f"yt-dlp failed, trying scraping fallback: {e}")
    except Exception as e:
        logger.warning(f"yt-dlp error, trying scraping fallback: {e}")
    
    # Способ 2: Fallback на прямой парсинг
    logger.info("Trying scraping fallback for Pinterest...")
    result = download_via_scraping(url, path, filename)
    
    if result:
        return result
    
    logger.error("All download methods failed for Pinterest")
    return None
