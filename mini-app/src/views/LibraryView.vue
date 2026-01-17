<template>
  <div class="library-view">
    <header class="header">
      <h1 class="title">Библиотека</h1>
    </header>

    <!-- Playlists Section -->
    <section class="section">
      <div class="section-header">
        <h2 class="section-title">Плейлисты</h2>
        <button class="add-btn" @click="showCreatePlaylist = true">
          <IconPlus />
        </button>
      </div>

      <div v-if="playlists.length" class="playlists-list">
        <router-link
          v-for="playlist in playlists"
          :key="playlist.id"
          :to="`/playlist/${playlist.id}`"
          class="playlist-card"
        >
          <div class="playlist-cover">
            <IconLibrary />
          </div>
          <div class="playlist-info">
            <span class="playlist-name truncate">{{ playlist.name }}</span>
            <span class="playlist-count">{{ playlist.track_count }} треков</span>
          </div>
        </router-link>
      </div>

      <div v-else class="empty-hint">
        Нажмите + чтобы создать плейлист
      </div>
    </section>

    <!-- Quick Links -->
    <section class="section">
      <router-link to="/favorites" class="quick-link">
        <div class="quick-icon favorites">
          <IconHeart :filled="true" />
        </div>
        <span class="quick-title">Избранное</span>
        <IconChevron class="chevron" />
      </router-link>
    </section>

    <!-- All Tracks -->
    <section class="section">
      <div class="section-header">
        <h2 class="section-title">Все треки</h2>
        <span class="track-count">{{ totalTracks }}</span>
      </div>

      <div v-if="isLoading" class="loading">
        <div class="skeleton-track" v-for="i in 5" :key="i"></div>
      </div>

      <div v-else-if="tracks.length" class="track-list">
        <TrackItem
          v-for="track in tracks"
          :key="track.id"
          :track="track"
          :tracklist="tracks"
          @toggle-favorite="handleToggleFavorite"
        />

        <button 
          v-if="hasMore" 
          class="load-more"
          @click="loadMore"
          :disabled="isLoadingMore"
        >
          {{ isLoadingMore ? 'Загрузка...' : 'Загрузить ещё' }}
        </button>
      </div>

      <div v-else class="empty-state">
        <p>Треков пока нет</p>
      </div>
    </section>

    <!-- Create Playlist Modal -->
    <Teleport to="body">
      <div v-if="showCreatePlaylist" class="modal-overlay" @click.self="showCreatePlaylist = false">
        <div class="modal">
          <h3 class="modal-title">Новый плейлист</h3>
          <input
            v-model="newPlaylistName"
            type="text"
            placeholder="Название плейлиста"
            class="modal-input"
            @keyup.enter="createPlaylist"
          />
          <div class="modal-actions">
            <button class="modal-btn cancel" @click="showCreatePlaylist = false">Отмена</button>
            <button 
              class="modal-btn confirm" 
              @click="createPlaylist"
              :disabled="!newPlaylistName.trim()"
            >
              Создать
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import TrackItem from '../components/TrackList/TrackItem.vue'
import IconLibrary from '../components/Common/icons/IconLibrary.vue'
import IconHeart from '../components/Common/icons/IconHeart.vue'
import IconPlus from '../components/Common/icons/IconPlus.vue'
import IconChevron from '../components/Common/icons/IconChevron.vue'

const playlists = ref([])
const tracks = ref([])
const totalTracks = ref(0)
const isLoading = ref(true)
const isLoadingMore = ref(false)
const offset = ref(0)
const limit = 20
const hasMore = ref(false)

const showCreatePlaylist = ref(false)
const newPlaylistName = ref('')

onMounted(async () => {
  await Promise.all([loadPlaylists(), loadTracks()])
})

async function loadPlaylists() {
  try {
    const data = await api.getPlaylists()
    playlists.value = data.items
  } catch (error) {
    console.error('Failed to load playlists:', error)
  }
}

async function loadTracks() {
  try {
    isLoading.value = true
    const data = await api.getAudioList({ limit, offset: 0 })
    tracks.value = data.items
    totalTracks.value = data.total
    offset.value = limit
    hasMore.value = data.items.length < data.total
  } catch (error) {
    console.error('Failed to load tracks:', error)
  } finally {
    isLoading.value = false
  }
}

async function loadMore() {
  try {
    isLoadingMore.value = true
    const data = await api.getAudioList({ limit, offset: offset.value })
    tracks.value.push(...data.items)
    offset.value += limit
    hasMore.value = tracks.value.length < data.total
  } catch (error) {
    console.error('Failed to load more:', error)
  } finally {
    isLoadingMore.value = false
  }
}

async function createPlaylist() {
  if (!newPlaylistName.value.trim()) return

  try {
    const playlist = await api.createPlaylist({ name: newPlaylistName.value.trim() })
    playlists.value.unshift(playlist)
    newPlaylistName.value = ''
    showCreatePlaylist.value = false
  } catch (error) {
    console.error('Failed to create playlist:', error)
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
</script>

<style scoped>
.library-view {
  padding: var(--spacing-md);
}

.header {
  padding: var(--spacing-md) 0;
}

.title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
}

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
}

.add-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-elevated);
  border-radius: var(--radius-full);
  color: var(--text-primary);
}

.add-btn svg {
  width: 18px;
  height: 18px;
}

.track-count {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* Playlists */
.playlists-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.playlist-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm);
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
}

.playlist-cover {
  width: 56px;
  height: 56px;
  background: var(--bg-highlight);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.playlist-cover svg {
  width: 24px;
  height: 24px;
}

.playlist-info {
  flex: 1;
  min-width: 0;
}

.playlist-name {
  display: block;
  font-weight: 600;
}

.playlist-count {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* Quick Links */
.quick-link {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
}

.quick-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
}

.quick-icon.favorites {
  background: linear-gradient(135deg, #7b2cbf, #c77dff);
  color: white;
}

.quick-icon svg {
  width: 24px;
  height: 24px;
}

.quick-title {
  flex: 1;
  font-weight: 600;
}

.chevron {
  width: 20px;
  height: 20px;
  color: var(--text-muted);
}

/* Loading & Empty */
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
.empty-hint {
  text-align: center;
  padding: var(--spacing-lg);
  color: var(--text-secondary);
}

.load-more {
  width: 100%;
  padding: var(--spacing-md);
  margin-top: var(--spacing-md);
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-weight: 500;
}

.load-more:disabled {
  opacity: 0.6;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-lg);
  z-index: 200;
}

.modal {
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  width: 100%;
  max-width: 320px;
}

.modal-title {
  font-size: var(--font-size-lg);
  font-weight: 700;
  margin-bottom: var(--spacing-md);
}

.modal-input {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--bg-highlight);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
}

.modal-input::placeholder {
  color: var(--text-muted);
}

.modal-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.modal-btn {
  flex: 1;
  padding: var(--spacing-md);
  border-radius: var(--radius-full);
  font-weight: 600;
}

.modal-btn.cancel {
  background: var(--bg-highlight);
}

.modal-btn.confirm {
  background: var(--accent);
  color: var(--bg-primary);
}

.modal-btn.confirm:disabled {
  opacity: 0.5;
}
</style>

