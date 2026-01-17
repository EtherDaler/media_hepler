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
        <div class="cover-placeholder">
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
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePlayerStore } from '../../stores/playerStore'
import IconMusic from '../Common/icons/IconMusic.vue'
import IconHeart from '../Common/icons/IconHeart.vue'

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
</style>

