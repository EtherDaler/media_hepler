<template>
  <Teleport to="body">
    <Transition name="menu">
      <div
        v-if="modelValue"
        class="sheet-overlay"
        @click.self="close"
      >
        <div
          class="sheet"
          @click.stop
          @touchstart="swipe.touchStart"
          @touchmove.passive="swipe.touchMove"
          @touchend="swipe.touchEnd"
        >
          <div class="sheet-handle" />
          <h2 class="sheet-title">Добавить в плейлист</h2>
          <p v-if="trackTitle" class="sheet-subtitle truncate">{{ trackTitle }}</p>

          <div v-if="loadError" class="sheet-error">{{ loadError }}</div>
          <div v-else-if="loading" class="sheet-loading">
            <span class="loader" />
          </div>
          <div v-else class="sheet-list">
            <button
              v-for="row in rows"
              :key="row.is_favorites ? 'fav' : `pl-${row.playlist_id}`"
              type="button"
              class="picker-row"
              :disabled="rowBusyKey === rowKey(row)"
              @click="toggleRow(row)"
            >
              <div class="picker-row-text">
                <span class="picker-name truncate">{{ row.name }}</span>
                <span class="picker-meta">{{ row.track_count }} треков</span>
              </div>
              <span
                class="round-check"
                :class="{ on: row.has_track, busy: rowBusyKey === rowKey(row) }"
                aria-hidden="true"
              />
            </button>
          </div>

          <button type="button" class="sheet-done" @click="close">Готово</button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { api } from '../../api/client'
import { useSwipeDownDismiss } from '../../composables/useSwipeDownDismiss'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  audioId: { type: Number, required: true },
  trackTitle: { type: String, default: '' }
})

const emit = defineEmits([
  'update:modelValue',
  'favorite-changed',
  'playlist-membership'
])

const loading = ref(false)
const loadError = ref('')
const rows = ref([])
const rowBusyKey = ref(null)

const swipe = useSwipeDownDismiss(() => {
  emit('update:modelValue', false)
}, { threshold: 85 })

function rowKey(row) {
  return row.is_favorites ? 'fav' : `p-${row.playlist_id}`
}

function close() {
  emit('update:modelValue', false)
}

async function loadPicker() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await api.getPlaylistPicker(props.audioId)
    rows.value = data.items || []
  } catch (e) {
    loadError.value = e?.message || 'Не удалось загрузить плейлисты'
    rows.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      loadPicker()
    } else {
      rowBusyKey.value = null
    }
  }
)

async function toggleRow(row) {
  const key = rowKey(row)
  if (rowBusyKey.value) return
  const was = row.has_track
  rowBusyKey.value = key
  try {
    if (row.is_favorites) {
      const result = await api.toggleFavorite(props.audioId)
      row.has_track = result.is_favorite
      if (result.is_favorite && !was) {
        row.track_count = (row.track_count || 0) + 1
      } else if (!result.is_favorite && was) {
        row.track_count = Math.max(0, (row.track_count || 0) - 1)
      }
      emit('favorite-changed', {
        audioId: props.audioId,
        isFavorite: result.is_favorite
      })
    } else if (was) {
      await api.removeTrackFromPlaylist(row.playlist_id, props.audioId)
      row.has_track = false
      row.track_count = Math.max(0, (row.track_count || 0) - 1)
      emit('playlist-membership', {
        playlistId: row.playlist_id,
        audioId: props.audioId,
        hasTrack: false
      })
    } else {
      await api.addTrackToPlaylist(row.playlist_id, props.audioId)
      row.has_track = true
      row.track_count = (row.track_count || 0) + 1
      emit('playlist-membership', {
        playlistId: row.playlist_id,
        audioId: props.audioId,
        hasTrack: true
      })
    }
  } catch (e) {
    row.has_track = was
    console.error(e)
  } finally {
    rowBusyKey.value = null
  }
}
</script>

<style scoped>
.sheet-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: flex-end;
  z-index: 1200;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}

.sheet {
  background: var(--bg-elevated);
  width: 100%;
  max-height: min(78vh, 640px);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  padding: var(--spacing-sm) var(--spacing-md) var(--spacing-md);
  padding-bottom: calc(var(--spacing-lg) + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.sheet-handle {
  width: 36px;
  height: 4px;
  background: var(--text-muted);
  border-radius: 2px;
  margin: 0 auto var(--spacing-md);
  opacity: 0.5;
}

.sheet-title {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-xs);
  text-align: center;
}

.sheet-subtitle {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin: 0 0 var(--spacing-md);
  text-align: center;
}

.sheet-loading {
  display: flex;
  justify-content: center;
  padding: var(--spacing-xl);
}

.sheet-error {
  color: #f87171;
  font-size: var(--font-size-sm);
  text-align: center;
  padding: var(--spacing-md);
}

.sheet-list {
  overflow-y: auto;
  flex: 1;
  min-height: 120px;
  -webkit-overflow-scrolling: touch;
}

.picker-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  width: 100%;
  padding: var(--spacing-md) var(--spacing-sm);
  border: none;
  background: transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  text-align: left;
  color: inherit;
  font: inherit;
}

.picker-row:active:not(:disabled) {
  background: var(--bg-highlight);
}

.picker-row:disabled {
  opacity: 0.85;
}

.picker-row-text {
  min-width: 0;
  flex: 1;
}

.picker-name {
  display: block;
  font-weight: 600;
  color: var(--text-primary);
  font-size: var(--font-size-md);
}

.picker-meta {
  display: block;
  font-size: var(--font-size-sm);
  color: var(--text-muted);
  margin-top: 2px;
}

/* Круглый чекбокс в стиле Spotify */
.round-check {
  position: relative;
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid var(--text-muted);
  box-sizing: border-box;
  transition:
    background 0.15s ease,
    border-color 0.15s ease;
}

.round-check.on {
  border-color: var(--accent);
  background: var(--accent);
}

.round-check.on::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 45%;
  width: 5px;
  height: 9px;
  border: solid var(--bg-primary);
  border-width: 0 2px 2px 0;
  transform: translate(-50%, -50%) rotate(45deg);
  box-sizing: border-box;
}

.round-check.busy {
  opacity: 0.5;
}

.sheet-done {
  margin-top: var(--spacing-md);
  width: 100%;
  padding: var(--spacing-md);
  border: none;
  border-radius: var(--radius-full);
  background: var(--bg-highlight);
  color: var(--text-primary);
  font-weight: 600;
  font-size: var(--font-size-md);
}

.menu-enter-active,
.menu-leave-active {
  transition: opacity var(--motion-duration-overlay) var(--motion-ease-standard);
}

.menu-enter-active .sheet,
.menu-leave-active .sheet {
  transition: transform var(--motion-duration-sheet) var(--motion-ease-sheet);
}

.menu-enter-from,
.menu-leave-to {
  opacity: 0;
}

.menu-enter-from .sheet,
.menu-leave-to .sheet {
  transform: translateY(100%);
}

.menu-leave-active {
  pointer-events: none;
}

.loader {
  width: 28px;
  height: 28px;
  border: 3px solid var(--bg-highlight);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
