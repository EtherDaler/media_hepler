"""FastAPI приложение для Mini App"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_user_id
from api.routes import audio, playlists, favorites
from api.schemas import UserStatsResponse
from db.audio_commands import count_user_audio, count_user_favorites
from models import Playlist
from sqlalchemy import select, func


app = FastAPI(
    title="Media Helper Mini App API",
    description="API для Telegram Mini App - управление аудио, плейлистами и избранным",
    version="1.0.0"
)

# CORS для Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на домен Mini App
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роуты
app.include_router(audio.router)
app.include_router(playlists.router)
app.include_router(favorites.router)


@app.get("/")
async def root():
    """Проверка работоспособности API"""
    return {"status": "ok", "app": "Media Helper Mini App API"}


@app.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Получить статистику пользователя"""
    total_tracks = await count_user_audio(db, user_id)
    total_favorites = await count_user_favorites(db, user_id)
    
    # Количество плейлистов
    result = await db.execute(
        select(func.count(Playlist.id)).where(Playlist.user_id == user_id)
    )
    total_playlists = result.scalar() or 0
    
    return UserStatsResponse(
        total_tracks=total_tracks,
        total_playlists=total_playlists,
        total_favorites=total_favorites
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

