<template>
  <div class="home-view">
    <!-- Header -->
    <header class="header">
      <h1 class="title">Добрый день</h1>
    </header>

    <!-- Stats -->
    <section v-if="stats" class="stats-section">
      <div class="stats-grid">
        <router-link to="/library" class="stat-card">
          <IconMusic class="stat-icon" />
          <div class="stat-info">
            <span class="stat-value">{{ stats.total_tracks }}</span>
            <span class="stat-label">Треков</span>
          </div>
        </router-link>
        
        <router-link to="/favorites" class="stat-card">
          <IconHeart class="stat-icon" :filled="true" />
          <div class="stat-info">
            <span class="stat-value">{{ stats.total_favorites }}</span>
            <span class="stat-label">Избранное</span>
          </div>
        </router-link>
        
        <router-link to="/library" class="stat-card">
          <IconLibrary class="stat-icon" />
          <div class="stat-info">
            <span class="stat-value">{{ stats.total_playlists }}</span>
            <span class="stat-label">Плейлистов</span>
          </div>
        </router-link>
      </div>
    </section>

    <!-- Recent Tracks -->
    <section class="section">
      <div class="section-header">
        <h2 class="section-title">Недавние треки</h2>
        <router-link to="/library" class="see-all">Все</router-link>
      </div>
      
      <div v-if="isLoading" class="loading">
        <div class="skeleton-track" v-for="i in 5" :key="i"></div>
      </div>
      
      <div v-else-if="recentTracks.length" class="track-list">
        <TrackItem
          v-for="track in recentTracks"
          :key="track.id"
          :track="track"
          :tracklist="recentTracks"
          @toggle-favorite="handleToggleFavorite"
        />
      </div>
      
      <div v-else class="empty-state">
        <IconMusic class="empty-icon" />
        <p>У вас пока нет треков</p>
        <p class="text-secondary">Скачайте аудио через бота</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import TrackItem from '../components/TrackList/TrackItem.vue'
import IconMusic from '../components/Common/icons/IconMusic.vue'
import IconHeart from '../components/Common/icons/IconHeart.vue'
import IconLibrary from '../components/Common/icons/IconLibrary.vue'

const stats = ref(null)
const recentTracks = ref([])
const isLoading = ref(true)

onMounted(async () => {
  try {
    const [statsData, audioData] = await Promise.all([
      api.getStats(),
      api.getAudioList({ limit: 10 })
    ])
    
    stats.value = statsData
    recentTracks.value = audioData.items
  } catch (error) {
    console.error('Failed to load data:', error)
  } finally {
    isLoading.value = false
  }
})

async function handleToggleFavorite(track) {
  try {
    const result = await api.toggleFavorite(track.id)
    track.is_favorite = result.is_favorite
    
    // Обновляем статистику
    if (stats.value) {
      stats.value.total_favorites += result.is_favorite ? 1 : -1
    }
  } catch (error) {
    console.error('Failed to toggle favorite:', error)
  }
}
</script>

<style scoped>
.home-view {
  padding: var(--spacing-md);
}

.header {
  padding: var(--spacing-md) 0;
}

.title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--text-primary);
}

/* Stats */
.stats-section {
  margin-bottom: var(--spacing-xl);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-sm);
}

.stat-card {
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  transition: background var(--transition-fast);
}

.stat-card:active {
  background: var(--bg-highlight);
}

.stat-icon {
  width: 24px;
  height: 24px;
  color: var(--accent);
}

.stat-info {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--text-primary);
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

/* Sections */
.section {
  margin-bottom: var(--spacing-xl);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.section-title {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--text-primary);
}

.see-all {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-secondary);
}

/* Loading */
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

/* Empty State */
.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--text-secondary);
}

.empty-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto var(--spacing-md);
  opacity: 0.5;
}
</style>

