<template>
  <div
    class="yt-row"
    :class="{ loading: busy }"
    @click="handleClick"
  >
    <div class="track-left">
      <div class="track-cover">
        <img
          v-if="item.thumbnail_url"
          :src="item.thumbnail_url"
          :alt="item.title"
          class="cover-image"
          @error="onImgError"
        />
        <div v-else class="cover-placeholder">
          <IconMusic />
        </div>
        <div v-if="busy" class="loading-overlay">
          <span class="spinner" />
        </div>
      </div>
    </div>
    <div class="track-info">
      <span class="track-title truncate">{{ item.title || 'Unknown' }}</span>
      <span class="track-artist truncate">{{ item.channel || 'YouTube' }}</span>
    </div>
    <div class="track-actions">
      <span v-if="item.duration_seconds" class="track-duration">
        {{ formatDuration(item.duration_seconds) }}
      </span>
      <button type="button" class="action-btn add-btn" :disabled="busy" @click.stop="handleClick">
        <IconPlus />
      </button>
    </div>
  </div>
</template>

<script setup>
import IconMusic from '../Common/icons/IconMusic.vue'
import IconPlus from '../Common/icons/IconPlus.vue'

const props = defineProps({
  item: { type: Object, required: true },
  /** Родитель ставит true, пока идёт импорт этого video_id */
  busy: { type: Boolean, default: false }
})

const emit = defineEmits(['add'])

function formatDuration(seconds) {
  if (!seconds) return ''
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function onImgError(e) {
  e.target.style.display = 'none'
}

function handleClick() {
  if (props.busy) return
  emit('add', props.item)
}
</script>

<style scoped>
.yt-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.yt-row:hover {
  background: var(--bg-elevated);
}

.yt-row.loading {
  opacity: 0.85;
  pointer-events: none;
}

.track-left {
  width: 48px;
  height: 48px;
  flex-shrink: 0;
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

.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner {
  width: 22px;
  height: 22px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
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

.truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

.add-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
  border-radius: var(--radius-full);
}

.add-btn:disabled {
  opacity: 0.5;
}

.add-btn svg {
  width: 20px;
  height: 20px;
}
</style>
