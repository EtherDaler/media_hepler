<template>
  <div 
    class="track-item" 
    :class="{ playing: isPlaying, active: isActive }"
    @click="handleClick"
  >
    <!-- Cover / Index -->
    <div class="track-left">
      <div v-if="showIndex" class="track-index">
        <span v-if="isPlaying" class="playing-indicator">
          <span></span><span></span><span></span>
        </span>
        <span v-else>{{ index }}</span>
      </div>
      <div v-else class="track-cover">
        <img 
          v-if="track.thumbnail_url" 
          :src="track.thumbnail_url" 
          :alt="track.title"
          class="cover-image"
          @error="handleImageError"
        />
        <div v-else class="cover-placeholder">
          <IconMusic />
        </div>
        <div v-if="isPlaying" class="playing-overlay">
          <span class="playing-indicator">
            <span></span><span></span><span></span>
          </span>
        </div>
      </div>
    </div>

    <!-- Track Info -->
    <div class="track-info">
      <span class="track-title truncate" :class="{ accent: isPlaying }">
        {{ track.title || 'Unknown' }}
      </span>
      <span class="track-artist truncate">
        {{ track.artist || 'Unknown Artist' }}
      </span>
    </div>

    <!-- Actions -->
    <div class="track-actions" @click.stop>
      <span v-if="track.duration" class="track-duration">
        {{ formatDuration(track.duration) }}
      </span>
      <button 
        class="action-btn"
        :class="{ active: track.is_favorite }"
        @click="$emit('toggleFavorite', track)"
      >
        <IconHeart :filled="track.is_favorite" />
      </button>
      <button class="action-btn menu-btn" @click="showMenu = true">
        <IconMore />
      </button>
    </div>

    <!-- Context Menu -->
    <Teleport to="body">
      <Transition name="menu">
        <div v-if="showMenu" class="menu-overlay" @click="showMenu = false">
          <div class="menu" @click.stop>
            <div class="menu-handle"></div>
            <div class="menu-track-info">
              <div class="menu-track-cover">
                <IconMusic />
              </div>
              <div class="menu-track-meta">
                <span class="menu-track-title">{{ track.title || 'Unknown' }}</span>
                <span class="menu-track-artist">{{ track.artist || 'Unknown Artist' }}</span>
              </div>
            </div>
            <div class="menu-divider"></div>
            <button class="menu-item" @click="addToQueueNext">
              <IconNext />
              <span>Воспроизвести следующим</span>
            </button>
            <button class="menu-item" @click="addToQueue">
              <IconQueue />
              <span>Добавить в очередь</span>
            </button>
            <button 
              class="menu-item"
              :class="{ active: track.is_favorite }"
              @click="toggleFavorite"
            >
              <IconHeart :filled="track.is_favorite" />
              <span>{{ track.is_favorite ? 'Удалить из избранного' : 'В избранное' }}</span>
            </button>
            <button class="menu-item cancel" @click="showMenu = false">
              <span>Отмена</span>
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { usePlayerStore } from '../../stores/playerStore'
import IconMusic from '../Common/icons/IconMusic.vue'
import IconHeart from '../Common/icons/IconHeart.vue'
import IconMore from '../Common/icons/IconMore.vue'
import IconNext from '../Common/icons/IconNext.vue'
import IconQueue from '../Common/icons/IconQueue.vue'

const props = defineProps({
  track: {
    type: Object,
    required: true
  },
  index: {
    type: Number,
    default: null
  },
  showIndex: {
    type: Boolean,
    default: false
  },
  tracklist: {
    type: Array,
    default: null
  }
})

const emit = defineEmits(['toggleFavorite'])

const playerStore = usePlayerStore()
const showMenu = ref(false)

const isPlaying = computed(() => 
  playerStore.currentTrack?.id === props.track.id && playerStore.isPlaying
)

const isActive = computed(() => 
  playerStore.currentTrack?.id === props.track.id
)

function formatDuration(seconds) {
  if (!seconds) return ''
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function handleClick() {
  playerStore.playTrack(props.track, props.tracklist)
}

function handleImageError(e) {
  // Если обложка не загрузилась, скрываем img
  e.target.style.display = 'none'
}

function addToQueue() {
  playerStore.addToQueue(props.track)
  showMenu.value = false
}

function addToQueueNext() {
  playerStore.addToQueueNext(props.track)
  showMenu.value = false
}

function toggleFavorite() {
  emit('toggleFavorite', props.track)
  showMenu.value = false
}
</script>

<style scoped>
.track-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.track-item:hover {
  background: var(--bg-elevated);
}

.track-item:active {
  background: var(--bg-highlight);
}

.track-item.active {
  background: var(--bg-elevated);
}

.track-left {
  width: 48px;
  height: 48px;
  flex-shrink: 0;
}

.track-index {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-md);
  color: var(--text-secondary);
}

.track-cover {
  width: 100%;
  height: 100%;
  border-radius: var(--radius-sm);
  overflow: hidden;
  position: relative;
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

.playing-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
}

.playing-indicator {
  display: flex;
  gap: 2px;
  height: 16px;
  align-items: flex-end;
}

.playing-indicator span {
  width: 3px;
  background: var(--accent);
  border-radius: 1px;
  animation: bounce 0.6s ease-in-out infinite;
}

.playing-indicator span:nth-child(1) {
  height: 8px;
  animation-delay: 0s;
}

.playing-indicator span:nth-child(2) {
  height: 16px;
  animation-delay: 0.2s;
}

.playing-indicator span:nth-child(3) {
  height: 12px;
  animation-delay: 0.4s;
}

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

.track-title.accent {
  color: var(--accent);
}

.track-artist {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.track-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.track-duration {
  font-size: var(--font-size-sm);
  color: var(--text-muted);
  min-width: 40px;
  text-align: right;
}

.action-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  opacity: 0;
  transition: all var(--transition-fast);
}

.track-item:hover .action-btn,
.action-btn.active {
  opacity: 1;
}

.action-btn.active {
  color: var(--accent);
}

.action-btn svg {
  width: 18px;
  height: 18px;
}

.menu-btn {
  opacity: 0.5;
}

.track-item:hover .menu-btn {
  opacity: 1;
}

/* Context Menu */
.menu-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: flex-end;
  z-index: 200;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}

.menu {
  background: var(--bg-elevated);
  width: 100%;
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  padding: var(--spacing-sm) var(--spacing-md) var(--spacing-md);
  padding-bottom: calc(var(--spacing-lg) + env(safe-area-inset-bottom));
}

.menu-handle {
  width: 36px;
  height: 4px;
  background: var(--text-muted);
  border-radius: 2px;
  margin: 0 auto var(--spacing-md);
  opacity: 0.5;
}

.menu-track-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
}

.menu-track-cover {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-sm);
  background: var(--bg-highlight);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  flex-shrink: 0;
}

.menu-track-cover svg {
  width: 24px;
  height: 24px;
}

.menu-track-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.menu-track-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.menu-track-artist {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.menu-divider {
  height: 1px;
  background: var(--bg-highlight);
  margin: var(--spacing-sm) 0;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  width: 100%;
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--font-size-md);
  transition: background var(--transition-fast);
}

.menu-item:active {
  background: var(--bg-highlight);
}

.menu-item.active {
  color: var(--accent);
}

.menu-item.cancel {
  justify-content: center;
  color: var(--text-secondary);
  margin-top: var(--spacing-sm);
  border-top: 1px solid var(--bg-highlight);
  padding-top: var(--spacing-lg);
}

.menu-item svg {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  color: var(--text-secondary);
}

.menu-item.active svg {
  color: var(--accent);
}

/* Menu Animation */
.menu-enter-active,
.menu-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.menu-enter-active .menu,
.menu-leave-active .menu {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.menu-enter-from,
.menu-leave-to {
  background: rgba(0, 0, 0, 0);
  backdrop-filter: blur(0);
}

.menu-enter-from .menu,
.menu-leave-to .menu {
  transform: translateY(100%);
}
</style>

