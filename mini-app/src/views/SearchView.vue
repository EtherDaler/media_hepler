<template>
  <div class="search-view">
    <header class="header">
      <div class="search-box">
        <IconSearch class="search-icon" />
        <input
          v-model="query"
          type="text"
          placeholder="Поиск треков..."
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

    <div v-else-if="results.length" class="results">
      <p class="results-count">Найдено: {{ results.length }}</p>
      <div class="track-list">
        <TrackItem
          v-for="track in results"
          :key="track.id"
          :track="track"
          :tracklist="results"
          @toggle-favorite="handleToggleFavorite"
        />
      </div>
    </div>

    <div v-else-if="query && !isLoading" class="empty-state">
      <IconSearch class="empty-icon" />
      <p>Ничего не найдено</p>
      <p class="text-secondary">Попробуйте другой запрос</p>
    </div>

    <div v-else class="hint">
      <IconSearch class="hint-icon" />
      <p>Введите название трека или исполнителя</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api/client'
import TrackItem from '../components/TrackList/TrackItem.vue'
import IconSearch from '../components/Common/icons/IconSearch.vue'
import IconClear from '../components/Common/icons/IconClear.vue'

const query = ref('')
const results = ref([])
const isLoading = ref(false)

let searchTimeout = null

function handleSearch() {
  clearTimeout(searchTimeout)
  
  if (!query.value.trim()) {
    results.value = []
    return
  }

  searchTimeout = setTimeout(async () => {
    try {
      isLoading.value = true
      const data = await api.getAudioList({ search: query.value.trim(), limit: 50 })
      results.value = data.items
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      isLoading.value = false
    }
  }, 300)
}

function clearSearch() {
  query.value = ''
  results.value = []
}

async function handleToggleFavorite(track) {
  try {
    const result = await api.toggleFavorite(track.id)
    track.is_favorite = result.is_favorite
  } catch (error) {
    console.error('Failed to toggle favorite:', error)
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

.results-count {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-md);
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

.empty-icon,
.hint-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto var(--spacing-md);
  opacity: 0.3;
}
</style>

