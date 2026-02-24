import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import os
import re
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Download function 
def download_file(url, path='./videos/pinterest', filename='defaultpin', out_format='mp4'):
    response = requests.get(url, stream=True)

    file_size = int(response.headers.get('Content-Length', 0))
    progress = tqdm(response.iter_content(1024), f'Downloading {filename}', total=file_size, unit='B', unit_scale=True, unit_divisor=1024)

    with open(f"{path}/{filename}.{out_format}", 'wb') as f:
        for data in progress.iterable:
            f.write(data)
            progress.update(len(data))
    return filename


def extract_video_url(soup):
    """Извлекает URL видео из страницы Pinterest несколькими способами"""
    
    # Способ 1: video с классом hwa
    video_tag = soup.find("video", class_="jI_JN7")
    if video_tag and video_tag.get('src'):
        return video_tag['src']
    
    # Способ 2: любой video тег с src
    video_tag = soup.find("video")
    if video_tag and video_tag.get('src'):
        return video_tag['src']
    
    # Способ 3: source внутри video
    source_tag = soup.find("video")
    if source_tag:
        source = source_tag.find("source")
        if source and source.get('src'):
            return source['src']
    
    # Способ 4: ищем в JSON-LD данных
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict):
                if 'video' in data:
                    video_data = data['video']
                    if isinstance(video_data, dict) and 'contentUrl' in video_data:
                        return video_data['contentUrl']
                if 'contentUrl' in data:
                    return data['contentUrl']
        except (json.JSONDecodeError, TypeError):
            continue
    
    # Способ 5: ищем URL в data-атрибутах
    for tag in soup.find_all(attrs={"data-video-url": True}):
        return tag['data-video-url']
    
    # Способ 6: ищем в inline scripts
    scripts = soup.find_all("script")
    for script in scripts:
        if script.string:
            # Ищем паттерн video URL
            match = re.search(r'"video_url"\s*:\s*"([^"]+)"', script.string)
            if match:
                return match.group(1).replace('\\u002F', '/')
            # Ищем m3u8 URL
            match = re.search(r'(https://[^"]+\.m3u8)', script.string)
            if match:
                return match.group(1)
    
    return None


def download_pin(url, path='./videos/pinterest', filename='defaultpin', out_format='mp4'):
    os.makedirs(path, exist_ok=True)
    page_url = url
    
    # Проверка URL
    if "pinterest.com/pin/" not in page_url and "https://pin.it/" not in page_url:
        logger.error("Entered url is invalid")
        return None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # Обработка короткой ссылки pin.it
    if "https://pin.it/" in page_url:
        logger.info("extracting original pin link")
        try:
            t_body = requests.get(page_url, headers=headers, allow_redirects=True, timeout=15)
            if t_body.status_code != 200:
                logger.error("Entered URL is invalid or not working.")
                return None
            
            # Сначала пробуем получить URL из редиректа
            if t_body.url and "pinterest.com/pin/" in t_body.url:
                page_url = t_body.url
            else:
                # Парсим HTML
                soup = BeautifulSoup(t_body.content, "html.parser")
                link_tag = soup.find("link", rel="alternate")
                if link_tag and link_tag.get('href'):
                    href_link = link_tag['href']
                    match = re.search(r'url=(.*?)&', href_link)
                    if match:
                        page_url = match.group(1)
                    else:
                        page_url = t_body.url
                else:
                    page_url = t_body.url
        except Exception as e:
            logger.error(f"Error extracting pin link: {e}")
            return None

    logger.info(f"fetching content from: {page_url}")
    
    try:
        body = requests.get(page_url, headers=headers, timeout=15)
        if body.status_code != 200:
            logger.error(f"URL returned status {body.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error fetching URL: {e}")
        return None
    
    soup = BeautifulSoup(body.content, "html.parser")
    logger.info("Fetched content Successfully.")
    
    # Извлекаем URL видео
    extract_url = extract_video_url(soup)
    
    if not extract_url:
        logger.error("Could not find video URL on the page. This might be an image pin, not a video.")
        return None
    
    # Конвертируем m3u8 в mp4 URL
    if '.m3u8' in extract_url:
        convert_url = extract_url.replace("hls", "720p").replace("m3u8", "mp4")
    else:
        convert_url = extract_url
    
    logger.info(f"Downloading file from: {convert_url[:50]}...")
    
    # Генерируем уникальное имя файла
    filename = datetime.now().strftime("%d_%m_%H_%M_%S_")
    ind = 1
    while os.path.isfile(f"{path}/{filename}.{out_format}"):
        filename = filename + f"({ind})"
        ind += 1
    
    try:
        res = download_file(convert_url, path, filename, out_format)
        return res
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return None