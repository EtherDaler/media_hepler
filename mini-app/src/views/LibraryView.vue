<template>
  <div class="library-view">
    <header class="header">
      <h1 class="title">Библиотека</h1>
      <button class="header-sync-btn" @click="openSyncInstructions" title="Синхронизировать">
        <IconSync />
      </button>
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
        <div class="empty-icon">
          <IconMusic />
        </div>
        <h3>Библиотека пуста</h3>
        <p>Скачивайте музыку через бота или синхронизируйте существующие треки</p>
        <button class="sync-btn" @click="openSyncInstructions">
          <IconSync />
          <span>Синхронизировать</span>
        </button>
      </div>
    </section>

    <!-- Sync Instructions Modal -->
    <Teleport to="body">
      <Transition name="menu">
        <div v-if="showSyncModal" class="modal-overlay bottom" @click.self="showSyncModal = false">
          <div class="sync-modal">
            <div class="sync-modal-handle"></div>
            <h3 class="sync-modal-title">Синхронизация треков</h3>
            <div class="sync-instructions">
              <div class="sync-step">
                <span class="step-number">1</span>
                <span>Откройте чат с ботом</span>
              </div>
              <div class="sync-step">
                <span class="step-number">2</span>
                <span>Найдите аудио, которые хотите добавить</span>
              </div>
              <div class="sync-step">
                <span class="step-number">3</span>
                <span>Перешлите их боту (Forward)</span>
              </div>
            </div>
            <p class="sync-hint">Бот автоматически добавит каждый трек в вашу библиотеку</p>
            <div class="sync-actions">
              <button class="sync-action-btn primary" @click="openBotChat">
                Открыть бота
              </button>
              <button class="sync-action-btn secondary" @click="showSyncModal = false">
                Закрыть
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

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
import IconMusic from '../components/Common/icons/IconMusic.vue'
import IconSync from '../components/Common/icons/IconSync.vue'

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
const showSyncModal = ref(false)

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

function openSyncInstructions() {
  showSyncModal.value = true
}

function openBotChat() {
  const tg = window.Telegram?.WebApp
  if (tg) {
    // Закрываем Mini App и открываем чат с ботом
    tg.close()
  }
  showSyncModal.value = false
}
</script>

<style scoped>
.library-view {
  padding: var(--spacing-md);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) 0;
}

.title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
}

.header-sync-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  transition: color var(--transition-fast);
}

.header-sync-btn:active {
  color: var(--accent);
}

.header-sync-btn svg {
  width: 22px;
  height: 22px;
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
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}

.modal-overlay.bottom {
  align-items: flex-end;
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

/* Empty State */
.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
}

.empty-state .empty-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto var(--spacing-md);
  background: var(--bg-highlight);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.empty-state .empty-icon svg {
  width: 32px;
  height: 32px;
}

.empty-state h3 {
  font-size: var(--font-size-lg);
  font-weight: 600;
  margin-bottom: var(--spacing-xs);
}

.empty-state p {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-lg);
}

.sync-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--accent);
  color: var(--bg-primary);
  border-radius: var(--radius-full);
  font-weight: 600;
}

.sync-btn svg {
  width: 18px;
  height: 18px;
}

/* Sync Modal */
.sync-modal {
  background: var(--bg-elevated);
  width: 100%;
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  padding: var(--spacing-md);
  padding-bottom: calc(var(--spacing-lg) + env(safe-area-inset-bottom));
}

.sync-modal-handle {
  width: 36px;
  height: 4px;
  background: var(--text-muted);
  border-radius: 2px;
  margin: 0 auto var(--spacing-lg);
  opacity: 0.5;
}

.sync-modal-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  text-align: center;
  margin-bottom: var(--spacing-lg);
}

.sync-instructions {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.sync-step {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--bg-highlight);
  border-radius: var(--radius-md);
}

.step-number {
  width: 28px;
  height: 28px;
  background: var(--accent);
  color: var(--bg-primary);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--font-size-sm);
  flex-shrink: 0;
}

.sync-hint {
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-lg);
}

.sync-actions {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.sync-action-btn {
  width: 100%;
  padding: var(--spacing-md);
  border-radius: var(--radius-full);
  font-weight: 600;
  font-size: var(--font-size-md);
}

.sync-action-btn.primary {
  background: var(--accent);
  color: var(--bg-primary);
}

.sync-action-btn.secondary {
  background: var(--bg-highlight);
  color: var(--text-primary);
}

/* Menu Animation */
.menu-enter-active,
.menu-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.menu-enter-active .sync-modal,
.menu-leave-active .sync-modal {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.menu-enter-from,
.menu-leave-to {
  background: rgba(0, 0, 0, 0);
}

.menu-enter-from .sync-modal,
.menu-leave-to .sync-modal {
  transform: translateY(100%);
}
</style>

