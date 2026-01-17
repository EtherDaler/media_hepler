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
          <div class="cover-placeholder">
            <IconMusic />
          </div>
          <div class="playing-indicator">
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

      <div v-if="playerStore.upcomingTracks.length" class="queue-list">
        <div
          v-for="(track, index) in playerStore.upcomingTracks"
          :key="track.id"
          class="queue-item"
          @click="playTrack(index)"
        >
          <div class="drag-handle">
            <IconDrag />
          </div>
          <div class="track-info">
            <span class="track-title truncate">{{ track.title || 'Unknown' }}</span>
            <span class="track-artist truncate">{{ track.artist || 'Unknown Artist' }}</span>
          </div>
          <button class="remove-btn" @click.stop="removeTrack(index)">
            <IconClear />
          </button>
        </div>
      </div>

      <div v-else class="empty-state">
        <p>Очередь пуста</p>
        <p class="text-secondary">Добавляйте треки через меню "⋮"</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { usePlayerStore } from '../stores/playerStore'
import IconBack from '../components/Common/icons/IconBack.vue'
import IconMusic from '../components/Common/icons/IconMusic.vue'
import IconDrag from '../components/Common/icons/IconDrag.vue'
import IconClear from '../components/Common/icons/IconClear.vue'

const playerStore = usePlayerStore()

function playTrack(upcomingIndex) {
  // upcomingIndex — индекс в upcomingTracks, нужно преобразовать в индекс в queue
  const queueIndex = playerStore.queueIndex + 1 + upcomingIndex
  playerStore.playFromQueue(queueIndex)
}

function removeTrack(upcomingIndex) {
  const queueIndex = playerStore.queueIndex + 1 + upcomingIndex
  playerStore.removeFromQueue(queueIndex)
}

function clearUpcoming() {
  // Удаляем все треки после текущего
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
  padding: var(--spacing-sm) 0;
  border-bottom: 1px solid var(--bg-elevated);
  cursor: pointer;
}

.queue-item:active {
  background: var(--bg-elevated);
}

.drag-handle {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  cursor: grab;
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
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.queue-item:hover .remove-btn {
  opacity: 1;
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
</style>

