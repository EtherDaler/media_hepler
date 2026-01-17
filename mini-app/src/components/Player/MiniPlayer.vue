<template>
  <div class="mini-player" @click="openFullPlayer">
    <!-- Progress Bar -->
    <div class="progress-bar">
      <div class="progress-fill" :style="{ width: playerStore.progress + '%' }"></div>
    </div>

    <!-- Player Content -->
    <div class="player-content">
      <!-- Track Info -->
      <div class="track-info">
        <div class="track-cover">
          <div class="cover-placeholder">
            <IconMusic />
          </div>
        </div>
        <div class="track-meta">
          <span class="track-title truncate">{{ currentTrack.title || 'Unknown' }}</span>
          <span class="track-artist truncate">{{ currentTrack.artist || 'Unknown Artist' }}</span>
        </div>
      </div>

      <!-- Controls -->
      <div class="controls" @click.stop>
        <button 
          class="control-btn favorite-btn"
          :class="{ active: currentTrack.is_favorite }"
          @click="toggleFavorite"
        >
          <IconHeart :filled="currentTrack.is_favorite" />
        </button>
        
        <button 
          class="control-btn play-btn"
          @click="playerStore.togglePlay()"
          :disabled="playerStore.isLoading"
        >
          <span v-if="playerStore.isLoading" class="loader"></span>
          <IconPause v-else-if="playerStore.isPlaying" />
          <IconPlay v-else />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePlayerStore } from '../../stores/playerStore'
import { api } from '../../api/client'
import IconMusic from '../Common/icons/IconMusic.vue'
import IconPlay from '../Common/icons/IconPlay.vue'
import IconPause from '../Common/icons/IconPause.vue'
import IconHeart from '../Common/icons/IconHeart.vue'

const playerStore = usePlayerStore()

const currentTrack = computed(() => playerStore.currentTrack)

async function toggleFavorite() {
  if (!currentTrack.value) return
  
  try {
    const result = await api.toggleFavorite(currentTrack.value.id)
    currentTrack.value.is_favorite = result.is_favorite
  } catch (error) {
    console.error('Failed to toggle favorite:', error)
  }
}

function openFullPlayer() {
  // TODO: Открыть полноэкранный плеер
  console.log('Open full player')
}
</script>

<style scoped>
.mini-player {
  position: fixed;
  bottom: var(--nav-height);
  left: 0;
  right: 0;
  height: var(--player-height);
  background: var(--bg-elevated);
  z-index: 99;
  cursor: pointer;
  transition: transform var(--transition-normal);
}

.mini-player:active {
  transform: scale(0.98);
}

.progress-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--bg-highlight);
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  transition: width 0.1s linear;
}

.player-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
}

.track-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex: 1;
  min-width: 0;
}

.track-cover {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-sm);
  overflow: hidden;
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

.track-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
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

.controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.control-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  transition: all var(--transition-fast);
  color: var(--text-primary);
}

.control-btn:active {
  transform: scale(0.9);
}

.favorite-btn {
  color: var(--text-secondary);
}

.favorite-btn.active {
  color: var(--accent);
}

.favorite-btn svg {
  width: 22px;
  height: 22px;
}

.play-btn {
  background: var(--text-primary);
  color: var(--bg-primary);
}

.play-btn svg {
  width: 20px;
  height: 20px;
}

.play-btn:disabled {
  opacity: 0.7;
}

.loader {
  width: 16px;
  height: 16px;
  border: 2px solid var(--bg-primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
</style>

