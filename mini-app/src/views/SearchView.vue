<template>
  <div class="search-view">
    <header class="header">
      <div class="search-box">
        <IconSearch class="search-icon" />
        <input
          v-model="query"
          type="text"
          placeholder="Треки в библиотеке и на YouTube..."
          class="search-input"
          @input="handleSearch"
        />
        <button v-if="query" class="clear-btn" @click="clearSearch">
          <IconClear />
        </button>
      </div>
    </header>

    <div v-if="isLoading" class="loading">
      <div class="skeleton-track" v-for="i in 5" :key="i"></div>
    </div>

    <template v-else-if="query.trim()">
      <section v-if="libraryTracks.length" class="section">
        <h2 class="section-title">Из библиотеки</h2>
        <div class="track-list">
          <TrackItem
            v-for="track in libraryTracks"
            :key="'lib-' + track.id"
            :track="track"
            :tracklist="libraryTracks"
            @toggle-favorite="handleToggleFavorite"
          />
        </div>
      </section>

      <section v-if="youtubeTracks.length" class="section">
        <h2 class="section-title">YouTube</h2>
        <p class="section-hint">До 10 мин · «+» открывает чат с ботом: он скачает аудио, трек появится в библиотеке</p>
        <div class="track-list">
          <YoutubeSearchRow
            v-for="yt in youtubeTracks"
            :key="'yt-' + yt.video_id"
            :item="yt"
            :busy="importingVideoId === yt.video_id"
            @add="handleYoutubeAdd"
          />
        </div>
      </section>

      <div v-if="!libraryTracks.length && !youtubeTracks.length" class="empty-state">
        <IconSearch class="empty-icon" />
        <p>Ничего не найдено</p>
        <p class="text-secondary">Попробуйте другой запрос</p>
      </div>
    </template>

    <div v-else class="hint">
      <IconSearch class="hint-icon" />
      <p>Введите название трека или исполнителя</p>
      <p class="text-secondary hint-sub">Сначала покажем совпадения из вашей библиотеки, затем ролики с YouTube. Добавление через «+» — загрузка в чате с ботом.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import TrackItem from '../components/TrackList/TrackItem.vue'
import YoutubeSearchRow from '../components/TrackList/YoutubeSearchRow.vue'
import IconSearch from '../components/Common/icons/IconSearch.vue'
import IconClear from '../components/Common/icons/IconClear.vue'

const query = ref('')
const libraryTracks = ref([])
const youtubeTracks = ref([])
const isLoading = ref(false)
const importingVideoId = ref(null)
const botUsername = ref('')

const tg = typeof window !== 'undefined' ? window.Telegram?.WebApp : null

let searchTimeout = null

onMounted(async () => {
  try {
    const cfg = await api.getMiniAppConfig()
    botUsername.value = (cfg.bot_username || '').trim()
  } catch (e) {
    console.error('getMiniAppConfig failed:', e)
  }
})

function handleSearch() {
  clearTimeout(searchTimeout)

  if (!query.value.trim()) {
    libraryTracks.value = []
    youtubeTracks.value = []
    return
  }

  searchTimeout = setTimeout(async () => {
    try {
      isLoading.value = true
      const data = await api.searchCombined(query.value.trim())
      libraryTracks.value = data.library || []
      youtubeTracks.value = data.youtube || []
    } catch (error) {
      console.error('Search failed:', error)
      libraryTracks.value = []
      youtubeTracks.value = []
    } finally {
      isLoading.value = false
    }
  }, 350)
}

function clearSearch() {
  query.value = ''
  libraryTracks.value = []
  youtubeTracks.value = []
}

async function handleToggleFavorite(track) {
  try {
    const result = await api.toggleFavorite(track.id)
    track.is_favorite = result.is_favorite
  } catch (error) {
    console.error('Failed to toggle favorite:', error)
  }
}

async function handleYoutubeAdd(item) {
  if (!botUsername.value) {
    try {
      const cfg = await api.getMiniAppConfig()
      botUsername.value = (cfg.bot_username || '').trim()
    } catch (e) {
      console.error(e)
    }
  }
  if (!botUsername.value) {
    tg?.showAlert?.(
      'На сервере не задан BOT_USERNAME в .env (имя бота без @). Добавьте и перезапустите API.'
    )
    tg?.HapticFeedback?.notificationOccurred?.('error')
    return
  }
  importingVideoId.value = item.video_id
  try {
    const url = `https://t.me/${botUsername.value}?start=impyt_${item.video_id}`
    if (tg?.openTelegramLink) {
      tg.openTelegramLink(url)
    } else {
      window.open(url, '_blank')
    }
    tg?.HapticFeedback?.notificationOccurred?.('success')
  } catch (error) {
    console.error('Open bot failed:', error)
    tg?.showAlert?.(error?.message || 'Не удалось открыть чат с ботом')
    tg?.HapticFeedback?.notificationOccurred?.('error')
  } finally {
    importingVideoId.value = null
  }
}
</script>

<style scoped>
.search-view {
  padding: var(--spacing-md);
}

.header {
  padding: var(--spacing-md) 0;
}

.search-box {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  background: var(--bg-elevated);
  border-radius: var(--radius-full);
  padding: var(--spacing-sm) var(--spacing-md);
}

.search-icon {
  width: 20px;
  height: 20px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  padding: var(--spacing-sm) 0;
  font-size: var(--font-size-md);
  color: var(--text-primary);
}

.search-input::placeholder {
  color: var(--text-muted);
}

.clear-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.clear-btn svg {
  width: 16px;
  height: 16px;
}

.section {
  margin-bottom: var(--spacing-xl);
}

.section-title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  margin-bottom: var(--spacing-sm);
}

.section-hint {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-md);
  line-height: 1.4;
}

.loading {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.skeleton-track {
  height: 64px;
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  animation: pulse 1.5s infinite;
}

.empty-state,
.hint {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--text-secondary);
}

.hint-sub {
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--text-muted);
  line-height: 1.4;
}

.empty-icon,
.hint-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto var(--spacing-md);
  opacity: 0.3;
}
</style>
