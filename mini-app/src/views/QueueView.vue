<template>
  <div class="queue-view">
    <header class="header">
      <button class="back-btn" @click="$router.back()">
        <IconBack />
      </button>
      <h1 class="title">Очередь</h1>
      <button 
        v-if="playerStore.upcomingCount > 0" 
        class="clear-btn"
        @click="clearUpcoming"
      >
        Очистить
      </button>
    </header>

    <!-- Now Playing -->
    <section v-if="playerStore.currentTrack" class="section">
      <h2 class="section-title">Сейчас играет</h2>
      <div class="current-track">
        <div class="track-cover">
          <img 
            v-if="playerStore.currentTrack.thumbnail_url" 
            :src="playerStore.currentTrack.thumbnail_url" 
            class="cover-image"
            alt=""
          />
          <div v-else class="cover-placeholder">
            <IconMusic />
          </div>
          <div class="playing-indicator" v-if="playerStore.isPlaying">
            <span></span><span></span><span></span>
          </div>
        </div>
        <div class="track-info">
          <span class="track-title truncate">{{ playerStore.currentTrack.title || 'Unknown' }}</span>
          <span class="track-artist truncate">{{ playerStore.currentTrack.artist || 'Unknown Artist' }}</span>
        </div>
      </div>
    </section>

    <!-- Upcoming Tracks -->
    <section class="section">
      <h2 class="section-title">
        Далее
        <span v-if="playerStore.upcomingCount" class="count">({{ playerStore.upcomingCount }})</span>
      </h2>

      <draggable
        v-if="upcomingList.length"
        v-model="upcomingList"
        item-key="id"
        handle=".drag-handle"
        :animation="200"
        ghost-class="queue-item-ghost"
        chosen-class="queue-item-chosen"
        drag-class="queue-item-drag"
        class="queue-list"
        @start="onDragStart"
        @end="onDragEnd"
      >
        <template #item="{ element: track, index }">
          <div
            class="queue-item"
            @click="playTrack(index)"
          >
            <div class="drag-handle" @click.stop>
              <IconDrag />
            </div>
            <div class="track-cover-small">
              <img 
                v-if="track.thumbnail_url" 
                :src="track.thumbnail_url" 
                class="cover-image"
                alt=""
              />
              <div v-else class="cover-placeholder">
                <IconMusic />
              </div>
            </div>
            <div class="track-info">
              <span class="track-title truncate">{{ track.title || 'Unknown' }}</span>
              <span class="track-artist truncate">{{ track.artist || 'Unknown Artist' }}</span>
            </div>
            <button class="remove-btn" @click.stop="removeTrack(index)">
              <IconClear />
            </button>
          </div>
        </template>
      </draggable>

      <div v-else class="empty-state">
        <p>Очередь пуста</p>
        <p class="text-secondary">Добавляйте треки через меню "⋮"</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import draggable from 'vuedraggable'
import { usePlayerStore } from '../stores/playerStore'
import IconBack from '../components/Common/icons/IconBack.vue'
import IconMusic from '../components/Common/icons/IconMusic.vue'
import IconDrag from '../components/Common/icons/IconDrag.vue'
import IconClear from '../components/Common/icons/IconClear.vue'

const playerStore = usePlayerStore()
const isDragging = ref(false)

// Computed с getter и setter для синхронизации с очередью
const upcomingList = computed({
  get() {
    return playerStore.upcomingTracks
  },
  set(newList) {
    // Воссоздаём очередь: треки до текущего + текущий + новый порядок upcoming
    const currentIdx = playerStore.queueIndex
    const beforeCurrent = playerStore.queue.slice(0, currentIdx)
    const currentTrack = playerStore.queue[currentIdx]
    
    playerStore.queue.splice(0, playerStore.queue.length, ...beforeCurrent, currentTrack, ...newList)
  }
})

function onDragStart() {
  isDragging.value = true
  // Haptic feedback если доступен
  if (window.Telegram?.WebApp?.HapticFeedback) {
    window.Telegram.WebApp.HapticFeedback.selectionChanged()
  }
}

function onDragEnd() {
  isDragging.value = false
  // Haptic feedback при завершении
  if (window.Telegram?.WebApp?.HapticFeedback) {
    window.Telegram.WebApp.HapticFeedback.impactOccurred('light')
  }
}

function playTrack(upcomingIndex) {
  if (isDragging.value) return
  const queueIndex = playerStore.queueIndex + 1 + upcomingIndex
  playerStore.playFromQueue(queueIndex)
}

function removeTrack(upcomingIndex) {
  const queueIndex = playerStore.queueIndex + 1 + upcomingIndex
  playerStore.removeFromQueue(queueIndex)
}

function clearUpcoming() {
  const currentIdx = playerStore.queueIndex
  playerStore.queue.splice(currentIdx + 1)
}
</script>

<style scoped>
.queue-view {
  padding: var(--spacing-md);
  padding-bottom: calc(var(--nav-height) + var(--player-height) + var(--spacing-lg));
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
  flex: 1;
  font-size: var(--font-size-xl);
  font-weight: 700;
}

.clear-btn {
  font-size: var(--font-size-sm);
  color: var(--accent);
  font-weight: 500;
}

.section {
  margin-bottom: var(--spacing-xl);
}

.section-title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: var(--spacing-md);
}

.count {
  color: var(--text-muted);
  font-weight: 400;
}

/* Current Track */
.current-track {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
}

.track-cover {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  position: relative;
  flex-shrink: 0;
}

.track-cover-small {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-xs);
  overflow: hidden;
  flex-shrink: 0;
}

.cover-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  background: var(--bg-highlight);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.cover-placeholder svg {
  width: 24px;
  height: 24px;
}

.track-cover-small .cover-placeholder svg {
  width: 18px;
  height: 18px;
}

.playing-indicator {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
}

.playing-indicator span {
  width: 3px;
  background: var(--accent);
  border-radius: 1px;
  animation: bounce 0.6s ease-in-out infinite;
}

.playing-indicator span:nth-child(1) { height: 8px; animation-delay: 0s; }
.playing-indicator span:nth-child(2) { height: 16px; animation-delay: 0.2s; }
.playing-indicator span:nth-child(3) { height: 12px; animation-delay: 0.4s; }

@keyframes bounce {
  0%, 100% { transform: scaleY(1); }
  50% { transform: scaleY(0.5); }
}

.track-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.track-title {
  font-size: var(--font-size-md);
  font-weight: 500;
  color: var(--text-primary);
}

.track-artist {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* Queue List */
.queue-list {
  display: flex;
  flex-direction: column;
}

.queue-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  margin: 0 calc(-1 * var(--spacing-sm));
  border-radius: var(--radius-md);
  cursor: pointer;
  background: var(--bg-primary);
  transition: background 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
  touch-action: manipulation;
}

.queue-item:active {
  background: var(--bg-elevated);
}

/* Drag and Drop States - Spotify-like animations */
.queue-item-ghost {
  opacity: 0.4;
  background: var(--bg-elevated);
}

.queue-item-chosen {
  background: var(--bg-elevated);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  transform: scale(1.02);
  z-index: 10;
  border-radius: var(--radius-md);
}

.queue-item-drag {
  opacity: 1;
  background: var(--bg-elevated);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
  transform: scale(1.03);
}

.drag-handle {
  width: 32px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  cursor: grab;
  touch-action: none;
  transition: color 0.15s ease;
}

.drag-handle:active {
  cursor: grabbing;
  color: var(--text-secondary);
}

.drag-handle svg {
  width: 20px;
  height: 20px;
}

.remove-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  transition: color var(--transition-fast), opacity var(--transition-fast);
}

.remove-btn:active {
  color: var(--error);
}

.remove-btn svg {
  width: 18px;
  height: 18px;
}

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--text-secondary);
}

/* Smooth reorder animation */
.queue-list :deep(.sortable-fallback) {
  opacity: 0 !important;
}
</style>

