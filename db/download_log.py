from datetime import datetime, date
from typing import Optional, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from models import DownloadLog
from data.config import DAILY_VIDEO_LIMIT

# Типы загрузок для видео (для подсчёта лимита водяного знака)
VIDEO_TYPES = ['shorts', 'reels', 'tiktok', 'pinterest', 'youtube']




async def log_download(
    session: AsyncSession,
    user_id: int,
    download_type: str,
    link: Optional[str] = None,
    status: bool = True
) -> DownloadLog:
    """
    Логирует загрузку пользователя.
    
    Args:
        session: Сессия БД
        user_id: ID пользователя Telegram
        download_type: Тип загрузки (audio, youtube, shorts, reels, tiktok, pinterest)
        link: URL загрузки
        status: True = успех, False = ошибка
    
    Returns:
        Созданная запись DownloadLog
    """
    log_entry = DownloadLog(
        user_id=user_id,
        type=download_type,
        link=link,
        status=status
    )
    session.add(log_entry)
    await session.commit()
    await session.refresh(log_entry)
    return log_entry


async def get_user_video_count_today(session: AsyncSession, user_id: int) -> int:
    """
    Возвращает количество успешных видео-загрузок пользователя за сегодня.
    Учитываются: shorts, reels, tiktok, pinterest, youtube
    """
    today_start = datetime.combine(date.today(), datetime.min.time())
    
    query = select(func.count(DownloadLog.id)).where(
        and_(
            DownloadLog.user_id == user_id,
            DownloadLog.type.in_(VIDEO_TYPES),
            DownloadLog.datetime >= today_start,
            DownloadLog.status == True
        )
    )
    
    result = await session.execute(query)
    count = result.scalar() or 0
    return count


async def should_add_watermark(session: AsyncSession, user_id: int) -> bool:
    """
    Проверяет, нужно ли добавлять водяной знак.
    Возвращает True, если пользователь скачал больше DAILY_VIDEO_LIMIT видео за сегодня.
    """
    count = await get_user_video_count_today(session, user_id)
    return count >= DAILY_VIDEO_LIMIT


async def get_user_stats(
    session: AsyncSession,
    user_id: int,
    days: int = 30
) -> Dict[str, int]:
    """
    Возвращает статистику загрузок пользователя за последние N дней.
    """
    from datetime import timedelta
    start_date = datetime.now() - timedelta(days=days)
    
    query = select(
        DownloadLog.type,
        func.count(DownloadLog.id).label('count')
    ).where(
        and_(
            DownloadLog.user_id == user_id,
            DownloadLog.datetime >= start_date,
            DownloadLog.status == True
        )
    ).group_by(DownloadLog.type)
    
    result = await session.execute(query)
    stats = {row.type: row.count for row in result}
    return stats


async def get_total_downloads(session: AsyncSession, days: int = 30) -> Dict[str, int]:
    """
    Возвращает общую статистику загрузок за последние N дней (для админов).
    """
    from datetime import timedelta
    start_date = datetime.now() - timedelta(days=days)
    
    query = select(
        DownloadLog.type,
        func.count(DownloadLog.id).label('count')
    ).where(
        and_(
            DownloadLog.datetime >= start_date,
            DownloadLog.status == True
        )
    ).group_by(DownloadLog.type)
    
    result = await session.execute(query)
    stats = {row.type: row.count for row in result}
    return stats


async def get_today_stats(session: AsyncSession) -> Dict:
    """
    Возвращает статистику за сегодня для админов:
    - DAU (уникальные пользователи)
    - Общее количество загрузок
    - Загрузки по платформам
    - Топ 3 пользователя
    """
    today_start = datetime.combine(date.today(), datetime.min.time())
    
    # DAU - уникальные пользователи за сегодня
    dau_query = select(func.count(func.distinct(DownloadLog.user_id))).where(
        and_(
            DownloadLog.datetime >= today_start,
            DownloadLog.status == True
        )
    )
    dau_result = await session.execute(dau_query)
    dau = dau_result.scalar() or 0
    
    # Общее количество успешных загрузок за сегодня
    total_query = select(func.count(DownloadLog.id)).where(
        and_(
            DownloadLog.datetime >= today_start,
            DownloadLog.status == True
        )
    )
    total_result = await session.execute(total_query)
    total_downloads = total_result.scalar() or 0
    
    # Загрузки по платформам
    platform_query = select(
        DownloadLog.type,
        func.count(DownloadLog.id).label('count')
    ).where(
        and_(
            DownloadLog.datetime >= today_start,
            DownloadLog.status == True
        )
    ).group_by(DownloadLog.type).order_by(func.count(DownloadLog.id).desc())
    
    platform_result = await session.execute(platform_query)
    by_platform = {row.type: row.count for row in platform_result}
    
    # Топ 3 пользователя по загрузкам
    top_users_query = select(
        DownloadLog.user_id,
        func.count(DownloadLog.id).label('count')
    ).where(
        and_(
            DownloadLog.datetime >= today_start,
            DownloadLog.status == True
        )
    ).group_by(DownloadLog.user_id).order_by(
        func.count(DownloadLog.id).desc()
    ).limit(3)
    
    top_users_result = await session.execute(top_users_query)
    top_users = [(row.user_id, row.count) for row in top_users_result]
    
    # Количество ошибок за сегодня
    errors_query = select(func.count(DownloadLog.id)).where(
        and_(
            DownloadLog.datetime >= today_start,
            DownloadLog.status == False
        )
    )
    errors_result = await session.execute(errors_query)
    errors = errors_result.scalar() or 0
    
    return {
        'dau': dau,
        'total_downloads': total_downloads,
        'by_platform': by_platform,
        'top_users': top_users,
        'errors': errors
    }
