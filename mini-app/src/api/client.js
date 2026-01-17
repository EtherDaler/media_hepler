/**
 * API Client для Media Helper Mini App
 */

const API_BASE = '/api'

// Получаем Telegram WebApp
const tg = window.Telegram?.WebApp

// Заголовки с авторизацией
function getHeaders() {
  const headers = {
    'Content-Type': 'application/json'
  }
  
  if (tg?.initData) {
    headers['X-Telegram-Init-Data'] = tg.initData
  } else {
    // Для разработки без Telegram (используй свой Telegram ID)
    headers['X-Telegram-Init-Data'] = 'dev:392046128'
  }
  
  return headers
}

// Базовый fetch с обработкой ошибок
async function fetchApi(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  
  const response = await fetch(url, {
    headers: getHeaders(),
    ...options
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
  
  return response.json()
}

export const api = {
  // ==================== Audio ====================
  
  /**
   * Получить список аудио
   */
  async getAudioList(params = {}) {
    const query = new URLSearchParams(params).toString()
    return fetchApi(`/audio${query ? `?${query}` : ''}`)
  },
  
  /**
   * Получить аудио по ID
   */
  async getAudio(audioId) {
    return fetchApi(`/audio/${audioId}`)
  },
  
  /**
   * Получить URL для стриминга
   */
  async getStreamUrl(audioId) {
    return fetchApi(`/audio/${audioId}/stream-url`)
  },
  
  /**
   * Обновить URL для стриминга
   */
  async refreshStreamUrl(audioId) {
    return fetchApi(`/audio/${audioId}/refresh-url`, { method: 'POST' })
  },
  
  /**
   * Удалить аудио
   */
  async deleteAudio(audioId) {
    return fetchApi(`/audio/${audioId}`, { method: 'DELETE' })
  },
  
  // ==================== Playlists ====================
  
  /**
   * Получить все плейлисты
   */
  async getPlaylists() {
    return fetchApi('/playlists')
  },
  
  /**
   * Получить плейлист с треками
   */
  async getPlaylist(playlistId) {
    return fetchApi(`/playlists/${playlistId}`)
  },
  
  /**
   * Создать плейлист
   */
  async createPlaylist(data) {
    return fetchApi('/playlists', {
      method: 'POST',
      body: JSON.stringify(data)
    })
  },
  
  /**
   * Обновить плейлист
   */
  async updatePlaylist(playlistId, data) {
    return fetchApi(`/playlists/${playlistId}`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    })
  },
  
  /**
   * Удалить плейлист
   */
  async deletePlaylist(playlistId) {
    return fetchApi(`/playlists/${playlistId}`, { method: 'DELETE' })
  },
  
  /**
   * Добавить трек в плейлист
   */
  async addTrackToPlaylist(playlistId, audioId) {
    return fetchApi(`/playlists/${playlistId}/tracks`, {
      method: 'POST',
      body: JSON.stringify({ audio_id: audioId })
    })
  },
  
  /**
   * Удалить трек из плейлиста
   */
  async removeTrackFromPlaylist(playlistId, audioId) {
    return fetchApi(`/playlists/${playlistId}/tracks/${audioId}`, {
      method: 'DELETE'
    })
  },
  
  // ==================== Favorites ====================
  
  /**
   * Получить избранное
   */
  async getFavorites(params = {}) {
    const query = new URLSearchParams(params).toString()
    return fetchApi(`/favorites${query ? `?${query}` : ''}`)
  },
  
  /**
   * Добавить/удалить из избранного
   */
  async toggleFavorite(audioId) {
    return fetchApi('/favorites/toggle', {
      method: 'POST',
      body: JSON.stringify({ audio_id: audioId })
    })
  },
  
  // ==================== Stats ====================
  
  /**
   * Получить статистику пользователя
   */
  async getStats() {
    return fetchApi('/stats')
  }
}

