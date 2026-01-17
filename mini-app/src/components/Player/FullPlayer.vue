<template>
  <div class="full-player">
    <!-- Header -->
    <header class="header">
      <button class="close-btn" @click="$emit('close')">
        <IconChevron class="chevron-down" />
      </button>
      <span class="header-title">Сейчас играет</span>
      <button class="menu-btn" @click="showMenu = true">
        <IconMore />
      </button>
    </header>

    <!-- Cover Art -->
    <div class="cover-section">
      <div class="cover-art">
        <div class="cover-placeholder">
          <IconMusic />
        </div>
      </div>
    </div>

    <!-- Track Info -->
    <div class="track-info">
      <h2 class="track-title">{{ currentTrack?.title || 'Unknown' }}</h2>
      <p class="track-artist">{{ currentTrack?.artist || 'Unknown Artist' }}</p>
    </div>

    <!-- Progress Bar -->
    <div class="progress-section">
      <div class="progress-bar" @click="handleSeek">
        <div class="progress-fill" :style="{ width: playerStore.progress + '%' }"></div>
        <div class="progress-thumb" :style="{ left: playerStore.progress + '%' }"></div>
      </div>
      <div class="time-info">
        <span>{{ playerStore.formattedTime }}</span>
        <span>{{ playerStore.formattedDuration }}</span>
      </div>
    </div>

    <!-- Controls -->
    <div class="controls">
      <button 
        class="control-btn secondary"
        :class="{ active: playerStore.isShuffled }"
        @click="playerStore.toggleShuffle()"
      >
        <IconShuffle />
      </button>

      <button 
        class="control-btn"
        @click="playerStore.playPrev()"
      >
        <IconPrev />
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

      <button 
        class="control-btn"
        @click="playerStore.playNext()"
      >
        <IconNext />
      </button>

      <button 
        class="control-btn secondary"
        :class="{ active: playerStore.repeatMode !== 'off' }"
        @click="playerStore.toggleRepeat()"
      >
        <IconRepeat v-if="playerStore.repeatMode !== 'one'" />
        <IconRepeatOne v-else />
      </button>
    </div>

    <!-- Bottom Actions -->
    <div class="bottom-actions">
      <button 
        class="action-btn"
        :class="{ active: currentTrack?.is_favorite }"
        @click="toggleFavorite"
      >
        <IconHeart :filled="currentTrack?.is_favorite" />
      </button>
      
      <button class="action-btn queue-btn" @click="openQueue">
        <IconQueue />
        <span v-if="playerStore.upcomingCount" class="queue-badge">{{ playerStore.upcomingCount }}</span>
      </button>
      
      <button class="action-btn" @click="openInTelegram">
        <IconShare />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePlayerStore } from '../../stores/playerStore'
import { api } from '../../api/client'
import IconMusic from '../Common/icons/IconMusic.vue'
import IconChevron from '../Common/icons/IconChevron.vue'
import IconMore from '../Common/icons/IconMore.vue'
import IconPlay from '../Common/icons/IconPlay.vue'
import IconPause from '../Common/icons/IconPause.vue'
import IconPrev from '../Common/icons/IconPrev.vue'
import IconNext from '../Common/icons/IconNext.vue'
import IconShuffle from '../Common/icons/IconShuffle.vue'
import IconRepeat from '../Common/icons/IconRepeat.vue'
import IconRepeatOne from '../Common/icons/IconRepeatOne.vue'
import IconHeart from '../Common/icons/IconHeart.vue'
import IconQueue from '../Common/icons/IconQueue.vue'
import IconShare from '../Common/icons/IconShare.vue'

const emit = defineEmits(['close'])
const router = useRouter()

const playerStore = usePlayerStore()
const showMenu = ref(false)

const currentTrack = computed(() => playerStore.currentTrack)

function handleSeek(e) {
  const rect = e.currentTarget.getBoundingClientRect()
  const percent = ((e.clientX - rect.left) / rect.width) * 100
  playerStore.seek(Math.max(0, Math.min(100, percent)))
}

async function toggleFavorite() {
  if (!currentTrack.value) return
  
  try {
    const result = await api.toggleFavorite(currentTrack.value.id)
    currentTrack.value.is_favorite = result.is_favorite
  } catch (error) {
    console.error('Failed to toggle favorite:', error)
  }
}

function openQueue() {
  emit('close')
  router.push('/queue')
}

function openInTelegram() {
  // Открыть аудио в Telegram плеере через file_id
  const tg = window.Telegram?.WebApp
  if (tg && currentTrack.value?.file_id) {
    // Можно отправить сообщение боту для пересылки аудио
    tg.sendData(JSON.stringify({
      action: 'play_audio',
      file_id: currentTrack.value.file_id
    }))
  }
}
</script>

<style scoped>
.full-player {
  position: fixed;
  inset: 0;
  background: var(--bg-primary);
  z-index: 150;
  display: flex;
  flex-direction: column;
  padding: var(--spacing-md);
  padding-bottom: calc(var(--spacing-lg) + env(safe-area-inset-bottom));
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm) 0;
}

.close-btn,
.menu-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-primary);
}

.close-btn svg,
.menu-btn svg {
  width: 24px;
  height: 24px;
}

.chevron-down {
  transform: rotate(90deg);
}

.header-title {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.cover-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-lg);
}

.cover-art {
  width: 100%;
  max-width: 320px;
  aspect-ratio: 1;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, var(--bg-elevated), var(--bg-highlight));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.cover-placeholder svg {
  width: 80px;
  height: 80px;
}

.track-info {
  text-align: center;
  padding: var(--spacing-md) 0;
}

.track-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
}

.track-artist {
  font-size: var(--font-size-md);
  color: var(--text-secondary);
}

.progress-section {
  padding: var(--spacing-md) 0;
}

.progress-bar {
  height: 4px;
  background: var(--bg-highlight);
  border-radius: 2px;
  position: relative;
  cursor: pointer;
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  transition: width 0.1s linear;
}

.progress-thumb {
  position: absolute;
  top: 50%;
  width: 12px;
  height: 12px;
  background: var(--accent);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.progress-bar:hover .progress-thumb,
.progress-bar:active .progress-thumb {
  opacity: 1;
}

.time-info {
  display: flex;
  justify-content: space-between;
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-xs);
  color: var(--text-muted);
}

.controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-lg);
  padding: var(--spacing-lg) 0;
}

.control-btn {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-primary);
  border-radius: var(--radius-full);
  transition: all var(--transition-fast);
}

.control-btn:active {
  transform: scale(0.9);
}

.control-btn.secondary {
  width: 40px;
  height: 40px;
  color: var(--text-secondary);
}

.control-btn.secondary.active {
  color: var(--accent);
}

.control-btn.secondary svg {
  width: 22px;
  height: 22px;
}

.control-btn svg {
  width: 28px;
  height: 28px;
}

.play-btn {
  width: 64px;
  height: 64px;
  background: var(--accent);
  color: var(--bg-primary);
}

.play-btn svg {
  width: 32px;
  height: 32px;
}

.play-btn:disabled {
  opacity: 0.7;
}

.loader {
  width: 24px;
  height: 24px;
  border: 3px solid var(--bg-primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.bottom-actions {
  display: flex;
  justify-content: center;
  gap: var(--spacing-xl);
  padding: var(--spacing-md) 0;
}

.action-btn {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  transition: color var(--transition-fast);
}

.action-btn.active {
  color: var(--accent);
}

.action-btn svg {
  width: 24px;
  height: 24px;
}

.queue-btn {
  position: relative;
}

.queue-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  min-width: 16px;
  height: 16px;
  background: var(--accent);
  color: var(--bg-primary);
  font-size: 10px;
  font-weight: 700;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
}
</style>

