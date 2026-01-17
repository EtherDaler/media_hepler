<template>
  <div class="favorites-view">
    <header class="header">
      <button class="back-btn" @click="$router.back()">
        <IconBack />
      </button>
      <h1 class="title">Избранное</h1>
    </header>

    <div v-if="isLoading" class="loading">
      <div class="skeleton-track" v-for="i in 5" :key="i"></div>
    </div>

    <div v-else-if="tracks.length" class="content">
      <!-- Play All Button -->
      <button class="play-all-btn" @click="playAll">
        <IconPlay />
        <span>Воспроизвести</span>
      </button>

      <!-- Tracks -->
      <div class="track-list">
        <TrackItem
          v-for="(item, index) in tracks"
          :key="item.id"
          :track="item.audio"
          :index="index + 1"
          :show-index="true"
          :tracklist="tracks.map(t => t.audio)"
          @toggle-favorite="handleToggleFavorite"
        />
      </div>
    </div>

    <div v-else class="empty-state">
      <IconHeart class="empty-icon" />
      <p>Избранное пусто</p>
      <p class="text-secondary">Добавляйте треки в избранное нажимая ♥</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import { usePlayerStore } from '../stores/playerStore'
import TrackItem from '../components/TrackList/TrackItem.vue'
import IconBack from '../components/Common/icons/IconBack.vue'
import IconPlay from '../components/Common/icons/IconPlay.vue'
import IconHeart from '../components/Common/icons/IconHeart.vue'

const playerStore = usePlayerStore()
const tracks = ref([])
const isLoading = ref(true)

onMounted(async () => {
  try {
    const data = await api.getFavorites()
    tracks.value = data.items
  } catch (error) {
    console.error('Failed to load favorites:', error)
  } finally {
    isLoading.value = false
  }
})

function playAll() {
  if (tracks.value.length) {
    const audioTracks = tracks.value.map(t => t.audio)
    playerStore.playTrack(audioTracks[0], audioTracks)
  }
}

async function handleToggleFavorite(track) {
  try {
    const result = await api.toggleFavorite(track.id)
    if (!result.is_favorite) {
      // Удаляем из списка
      tracks.value = tracks.value.filter(t => t.audio.id !== track.id)
    }
  } catch (error) {
    console.error('Failed to toggle favorite:', error)
  }
}
</script>

<style scoped>
.favorites-view {
  padding: var(--spacing-md);
}

.header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md) 0;
}

.back-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-primary);
}

.back-btn svg {
  width: 24px;
  height: 24px;
}

.title {
  font-size: var(--font-size-xl);
  font-weight: 700;
}

.play-all-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  width: 100%;
  padding: var(--spacing-md);
  background: var(--accent);
  color: var(--bg-primary);
  border-radius: var(--radius-full);
  font-weight: 600;
  margin-bottom: var(--spacing-lg);
}

.play-all-btn svg {
  width: 20px;
  height: 20px;
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

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--text-secondary);
}

.empty-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto var(--spacing-md);
  opacity: 0.3;
  color: var(--accent);
}
</style>

