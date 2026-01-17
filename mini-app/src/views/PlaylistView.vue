<template>
  <div class="playlist-view">
    <header class="header">
      <button class="back-btn" @click="$router.back()">
        <IconBack />
      </button>
      <h1 class="title truncate">{{ playlist?.name || 'Плейлист' }}</h1>
      <button class="menu-btn" @click="showMenu = true">
        <IconMore />
      </button>
    </header>

    <div v-if="isLoading" class="loading">
      <div class="skeleton-header"></div>
      <div class="skeleton-track" v-for="i in 5" :key="i"></div>
    </div>

    <div v-else-if="playlist" class="content">
      <!-- Playlist Info -->
      <div class="playlist-header">
        <div class="playlist-cover">
          <IconLibrary />
        </div>
        <div class="playlist-meta">
          <h2 class="playlist-name">{{ playlist.name }}</h2>
          <p v-if="playlist.description" class="playlist-desc">{{ playlist.description }}</p>
          <span class="playlist-count">{{ playlist.track_count }} треков</span>
        </div>
      </div>

      <!-- Actions -->
      <div v-if="playlist.tracks?.length" class="actions">
        <button class="play-btn" @click="playAll">
          <IconPlay />
        </button>
      </div>

      <!-- Tracks -->
      <div v-if="playlist.tracks?.length" class="track-list">
        <TrackItem
          v-for="(track, index) in playlist.tracks"
          :key="track.id"
          :track="track"
          :index="index + 1"
          :show-index="true"
          :tracklist="playlist.tracks"
          @toggle-favorite="handleToggleFavorite"
        />
      </div>

      <div v-else class="empty-state">
        <p>Плейлист пуст</p>
        <p class="text-secondary">Добавляйте треки из библиотеки</p>
      </div>
    </div>

    <!-- Menu -->
    <Teleport to="body">
      <div v-if="showMenu" class="menu-overlay" @click.self="showMenu = false">
        <div class="menu">
          <button class="menu-item" @click="editPlaylist">
            <IconEdit />
            <span>Редактировать</span>
          </button>
          <button class="menu-item danger" @click="deletePlaylist">
            <IconDelete />
            <span>Удалить плейлист</span>
          </button>
          <button class="menu-item" @click="showMenu = false">
            <span>Отмена</span>
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/client'
import { usePlayerStore } from '../stores/playerStore'
import TrackItem from '../components/TrackList/TrackItem.vue'
import IconBack from '../components/Common/icons/IconBack.vue'
import IconMore from '../components/Common/icons/IconMore.vue'
import IconPlay from '../components/Common/icons/IconPlay.vue'
import IconLibrary from '../components/Common/icons/IconLibrary.vue'
import IconEdit from '../components/Common/icons/IconEdit.vue'
import IconDelete from '../components/Common/icons/IconDelete.vue'

const route = useRoute()
const router = useRouter()
const playerStore = usePlayerStore()

const playlist = ref(null)
const isLoading = ref(true)
const showMenu = ref(false)

onMounted(async () => {
  try {
    const id = route.params.id
    playlist.value = await api.getPlaylist(id)
  } catch (error) {
    console.error('Failed to load playlist:', error)
  } finally {
    isLoading.value = false
  }
})

function playAll() {
  if (playlist.value?.tracks?.length) {
    playerStore.playTrack(playlist.value.tracks[0], playlist.value.tracks)
  }
}

async function handleToggleFavorite(track) {
  try {
    const result = await api.toggleFavorite(track.id)
    track.is_favorite = result.is_favorite
  } catch (error) {
    console.error('Failed to toggle favorite:', error)
  }
}

function editPlaylist() {
  showMenu.value = false
  // TODO: Implement edit
}

async function deletePlaylist() {
  if (!confirm('Удалить плейлист?')) return
  
  try {
    await api.deletePlaylist(playlist.value.id)
    router.replace('/library')
  } catch (error) {
    console.error('Failed to delete playlist:', error)
  }
}
</script>

<style scoped>
.playlist-view {
  padding: var(--spacing-md);
}

.header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md) 0;
}

.back-btn,
.menu-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-primary);
}

.back-btn svg,
.menu-btn svg {
  width: 24px;
  height: 24px;
}

.title {
  flex: 1;
  font-size: var(--font-size-lg);
  font-weight: 700;
}

.playlist-header {
  display: flex;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.playlist-cover {
  width: 120px;
  height: 120px;
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  flex-shrink: 0;
}

.playlist-cover svg {
  width: 48px;
  height: 48px;
}

.playlist-meta {
  flex: 1;
  min-width: 0;
}

.playlist-name {
  font-size: var(--font-size-xl);
  font-weight: 700;
  margin-bottom: var(--spacing-xs);
}

.playlist-desc {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-sm);
}

.playlist-count {
  font-size: var(--font-size-sm);
  color: var(--text-muted);
}

.actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--spacing-lg);
}

.play-btn {
  width: 56px;
  height: 56px;
  background: var(--accent);
  color: var(--bg-primary);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
}

.play-btn svg {
  width: 24px;
  height: 24px;
  margin-left: 2px;
}

.loading {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.skeleton-header {
  height: 120px;
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-lg);
  animation: pulse 1.5s infinite;
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

/* Menu */
.menu-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: flex-end;
  z-index: 200;
}

.menu {
  background: var(--bg-elevated);
  width: 100%;
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  padding: var(--spacing-md);
  padding-bottom: calc(var(--spacing-md) + env(safe-area-inset-bottom));
}

.menu-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  width: 100%;
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  color: var(--text-primary);
}

.menu-item:active {
  background: var(--bg-highlight);
}

.menu-item.danger {
  color: #e74c3c;
}

.menu-item svg {
  width: 22px;
  height: 22px;
}
</style>

