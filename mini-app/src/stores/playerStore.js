import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api/client'

export const usePlayerStore = defineStore('player', () => {
  // State
  const currentTrack = ref(null)
  const queue = ref([])
  const queueIndex = ref(0)
  const isPlaying = ref(false)
  const duration = ref(0)
  const currentTime = ref(0)
  const volume = ref(1)
  const isMuted = ref(false)
  const isLoading = ref(false)
  const repeatMode = ref('off') // 'off', 'all', 'one'
  const isShuffled = ref(false)
  
  // Stream URL (временный, обновляется каждый час)
  const streamUrl = ref(null)
  const streamUrlExpiresAt = ref(null)
  
  // Audio element
  let audio = null

  // Computed
  const progress = computed(() => {
    if (!duration.value) return 0
    return (currentTime.value / duration.value) * 100
  })

  const hasNext = computed(() => {
    return queueIndex.value < queue.value.length - 1
  })

  const hasPrev = computed(() => {
    return queueIndex.value > 0
  })

  // Треки которые будут играть после текущего
  const upcomingTracks = computed(() => {
    if (queueIndex.value >= queue.value.length - 1) return []
    return queue.value.slice(queueIndex.value + 1)
  })

  // Количество треков в очереди после текущего
  const upcomingCount = computed(() => upcomingTracks.value.length)

  const formattedTime = computed(() => formatTime(currentTime.value))
  const formattedDuration = computed(() => formatTime(duration.value))

  // Helpers
  function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Initialize audio element
  function initAudio() {
    if (audio) return audio

    audio = new Audio()
    audio.volume = volume.value

    audio.addEventListener('loadedmetadata', () => {
      duration.value = audio.duration
      updateMediaSessionPosition()
    })

    audio.addEventListener('timeupdate', () => {
      currentTime.value = audio.currentTime
      // Обновляем позицию каждые 5 секунд для экономии ресурсов
      if (Math.floor(currentTime.value) % 5 === 0) {
        updateMediaSessionPosition()
      }
    })

    audio.addEventListener('ended', () => {
      handleTrackEnd()
    })

    audio.addEventListener('playing', () => {
      isPlaying.value = true
      isLoading.value = false
      updateMediaSessionPlaybackState()
    })

    audio.addEventListener('pause', () => {
      isPlaying.value = false
      updateMediaSessionPlaybackState()
    })

    audio.addEventListener('waiting', () => {
      isLoading.value = true
    })

    audio.addEventListener('canplay', () => {
      isLoading.value = false
    })

    audio.addEventListener('error', async (e) => {
      console.error('Audio error:', e)
      // Попробуем обновить URL если истёк
      if (currentTrack.value) {
        await refreshStreamUrl()
      }
    })

    // Setup Media Session API for lock screen controls
    setupMediaSession()

    return audio
  }

  // Media Session API - для кнопок на экране блокировки
  function setupMediaSession() {
    if (!('mediaSession' in navigator)) return

    navigator.mediaSession.setActionHandler('play', () => {
      audio?.play()
    })

    navigator.mediaSession.setActionHandler('pause', () => {
      audio?.pause()
    })

    navigator.mediaSession.setActionHandler('previoustrack', () => {
      playPrev()
    })

    navigator.mediaSession.setActionHandler('nexttrack', () => {
      playNext()
    })

    navigator.mediaSession.setActionHandler('seekto', (details) => {
      if (audio && details.seekTime !== undefined) {
        audio.currentTime = details.seekTime
      }
    })

    navigator.mediaSession.setActionHandler('seekbackward', (details) => {
      if (audio) {
        audio.currentTime = Math.max(0, audio.currentTime - (details.seekOffset || 10))
      }
    })

    navigator.mediaSession.setActionHandler('seekforward', (details) => {
      if (audio) {
        audio.currentTime = Math.min(audio.duration, audio.currentTime + (details.seekOffset || 10))
      }
    })
  }

  // Обновить метаданные Media Session
  function updateMediaSessionMetadata(track) {
    if (!('mediaSession' in navigator) || !track) return

    // Создаём SVG как Data URL для обложки (некоторые системы требуют artwork)
    const defaultArtwork = 'data:image/svg+xml,' + encodeURIComponent(`
      <svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
        <rect width="512" height="512" fill="#1a1a2e"/>
        <circle cx="256" cy="256" r="120" fill="none" stroke="#4a4a6a" stroke-width="8"/>
        <circle cx="256" cy="256" r="40" fill="#4a4a6a"/>
        <path d="M220 180 L320 256 L220 332 Z" fill="#6366f1"/>
      </svg>
    `.trim())

    navigator.mediaSession.metadata = new MediaMetadata({
      title: track.title || 'Unknown',
      artist: track.artist || 'Unknown Artist',
      album: track.album || 'Media Helper',
      artwork: [
        { src: defaultArtwork, sizes: '512x512', type: 'image/svg+xml' }
      ]
    })
  }

  // Обновить состояние воспроизведения в Media Session
  function updateMediaSessionPlaybackState() {
    if (!('mediaSession' in navigator)) return
    
    navigator.mediaSession.playbackState = isPlaying.value ? 'playing' : 'paused'
  }

  // Обновить позицию в Media Session
  function updateMediaSessionPosition() {
    if (!('mediaSession' in navigator) || !audio) return
    
    try {
      navigator.mediaSession.setPositionState({
        duration: duration.value || 0,
        playbackRate: audio.playbackRate || 1,
        position: currentTime.value || 0
      })
    } catch (e) {
      // Игнорируем ошибки (может быть если duration = 0)
    }
  }

  // Get stream URL
  async function getStreamUrl(audioId) {
    // Проверяем, не истёк ли текущий URL
    if (streamUrl.value && streamUrlExpiresAt.value && Date.now() < streamUrlExpiresAt.value) {
      return streamUrl.value
    }

    try {
      const data = await api.getStreamUrl(audioId)
      streamUrl.value = data.url
      // Ставим время истечения с запасом в 5 минут
      streamUrlExpiresAt.value = Date.now() + (data.expires_in * 1000) - 300000
      return data.url
    } catch (error) {
      console.error('Failed to get stream URL:', error)
      throw error
    }
  }

  // Refresh stream URL
  async function refreshStreamUrl() {
    if (!currentTrack.value) return

    try {
      isLoading.value = true
      
      // Сбрасываем кэш чтобы принудительно получить новый URL
      streamUrl.value = null
      streamUrlExpiresAt.value = null
      
      const url = await getStreamUrl(currentTrack.value.id)
      const wasPlaying = isPlaying.value
      const savedTime = currentTime.value
      
      audio.src = url
      audio.currentTime = savedTime
      
      if (wasPlaying) {
        await audio.play()
      }
    } catch (error) {
      console.error('Failed to refresh stream URL:', error)
    } finally {
      isLoading.value = false
    }
  }

  // Actions
  async function playTrack(track, tracklist = null) {
    initAudio()

    // Если передан список треков, устанавливаем очередь
    if (tracklist) {
      queue.value = tracklist
      queueIndex.value = tracklist.findIndex(t => t.id === track.id)
    }

    // Сбрасываем кэш URL при смене трека
    if (currentTrack.value?.id !== track.id) {
      streamUrl.value = null
      streamUrlExpiresAt.value = null
    }

    currentTrack.value = track
    isLoading.value = true
    currentTime.value = 0
    duration.value = 0

    // Обновляем метаданные на экране блокировки
    updateMediaSessionMetadata(track)

    try {
      const url = await getStreamUrl(track.id)
      audio.src = url
      await audio.play()
    } catch (error) {
      console.error('Failed to play track:', error)
      isLoading.value = false
    }
  }

  function togglePlay() {
    if (!audio || !currentTrack.value) return

    if (isPlaying.value) {
      audio.pause()
    } else {
      audio.play()
    }
  }

  function pause() {
    audio?.pause()
  }

  function play() {
    audio?.play()
  }

  async function playNext() {
    if (!hasNext.value) {
      if (repeatMode.value === 'all' && queue.value.length > 0) {
        queueIndex.value = 0
        // Не передаём tracklist, чтобы не сбросить очередь
        await playTrackFromQueue(queue.value[0])
      }
      return
    }

    queueIndex.value++
    await playTrackFromQueue(queue.value[queueIndex.value])
  }

  async function playPrev() {
    // Если прошло больше 3 секунд, начинаем трек сначала
    if (currentTime.value > 3) {
      seek(0)
      return
    }

    if (!hasPrev.value) {
      if (repeatMode.value === 'all' && queue.value.length > 0) {
        queueIndex.value = queue.value.length - 1
        await playTrackFromQueue(queue.value[queueIndex.value])
      }
      return
    }

    queueIndex.value--
    await playTrackFromQueue(queue.value[queueIndex.value])
  }

  // Внутренняя функция для воспроизведения из очереди (не сбрасывает очередь)
  async function playTrackFromQueue(track) {
    initAudio()

    // Сбрасываем кэш URL при смене трека
    if (currentTrack.value?.id !== track.id) {
      streamUrl.value = null
      streamUrlExpiresAt.value = null
    }

    currentTrack.value = track
    isLoading.value = true
    currentTime.value = 0
    duration.value = 0

    // Обновляем метаданные на экране блокировки
    updateMediaSessionMetadata(track)

    try {
      const url = await getStreamUrl(track.id)
      audio.src = url
      await audio.play()
    } catch (error) {
      console.error('Failed to play track:', error)
      isLoading.value = false
    }
  }

  function seek(percent) {
    if (!audio || !duration.value) return
    audio.currentTime = (percent / 100) * duration.value
  }

  function seekTo(time) {
    if (!audio) return
    audio.currentTime = time
  }

  function setVolume(value) {
    volume.value = value
    if (audio) {
      audio.volume = value
    }
    if (value > 0) {
      isMuted.value = false
    }
  }

  function toggleMute() {
    isMuted.value = !isMuted.value
    if (audio) {
      audio.muted = isMuted.value
    }
  }

  function toggleRepeat() {
    const modes = ['off', 'all', 'one']
    const currentIndex = modes.indexOf(repeatMode.value)
    repeatMode.value = modes[(currentIndex + 1) % modes.length]
  }

  // Оригинальный порядок очереди (до shuffle)
  const originalQueue = ref([])

  function toggleShuffle() {
    isShuffled.value = !isShuffled.value
    
    if (queue.value.length <= 1) return
    
    if (isShuffled.value) {
      // Сохраняем оригинальный порядок
      originalQueue.value = [...queue.value]
      
      // Перемешиваем все треки кроме текущего
      const currentTrackItem = queue.value[queueIndex.value]
      const beforeCurrent = queue.value.slice(0, queueIndex.value)
      const afterCurrent = queue.value.slice(queueIndex.value + 1)
      
      // Перемешиваем треки после текущего (Fisher-Yates shuffle)
      const toShuffle = [...afterCurrent]
      for (let i = toShuffle.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [toShuffle[i], toShuffle[j]] = [toShuffle[j], toShuffle[i]]
      }
      
      // Собираем новую очередь: до текущего + текущий + перемешанные
      queue.value = [...beforeCurrent, currentTrackItem, ...toShuffle]
    } else {
      // Восстанавливаем оригинальный порядок
      if (originalQueue.value.length > 0) {
        const currentTrackItem = currentTrack.value
        queue.value = [...originalQueue.value]
        // Находим текущий трек в восстановленной очереди
        queueIndex.value = queue.value.findIndex(t => t.id === currentTrackItem?.id)
        if (queueIndex.value === -1) queueIndex.value = 0
        originalQueue.value = []
      }
    }
  }

  function handleTrackEnd() {
    if (repeatMode.value === 'one') {
      audio.currentTime = 0
      audio.play()
      return
    }
    playNext()
  }

  // Добавить трек в конец очереди
  function addToQueue(track) {
    // Проверяем что трек ещё не в очереди
    const exists = queue.value.some(t => t.id === track.id)
    if (!exists) {
      queue.value.push(track)
    }
  }

  // Добавить трек следующим (после текущего)
  function addToQueueNext(track) {
    // Проверяем что трек ещё не в очереди
    const existingIndex = queue.value.findIndex(t => t.id === track.id)
    if (existingIndex !== -1) {
      // Если трек уже в очереди, перемещаем его
      queue.value.splice(existingIndex, 1)
      if (existingIndex <= queueIndex.value) {
        queueIndex.value--
      }
    }
    // Вставляем после текущего трека
    queue.value.splice(queueIndex.value + 1, 0, track)
  }

  // Удалить трек из очереди по индексу
  function removeFromQueue(index) {
    if (index < 0 || index >= queue.value.length) return
    if (index === queueIndex.value) return // Нельзя удалить текущий трек
    
    queue.value.splice(index, 1)
    
    // Корректируем индекс если удалили трек до текущего
    if (index < queueIndex.value) {
      queueIndex.value--
    }
  }

  // Переместить трек в очереди
  function moveInQueue(fromIndex, toIndex) {
    if (fromIndex === toIndex) return
    if (fromIndex === queueIndex.value || toIndex === queueIndex.value) return // Не перемещаем текущий
    
    const [track] = queue.value.splice(fromIndex, 1)
    queue.value.splice(toIndex, 0, track)
    
    // Корректируем индекс текущего трека
    if (fromIndex < queueIndex.value && toIndex >= queueIndex.value) {
      queueIndex.value--
    } else if (fromIndex > queueIndex.value && toIndex <= queueIndex.value) {
      queueIndex.value++
    }
  }

  // Воспроизвести трек из очереди по индексу
  function playFromQueue(index) {
    if (index < 0 || index >= queue.value.length) return
    queueIndex.value = index
    playTrackFromQueue(queue.value[index])
  }

  function clearQueue() {
    queue.value = []
    queueIndex.value = 0
  }

  return {
    // State
    currentTrack,
    queue,
    queueIndex,
    isPlaying,
    duration,
    currentTime,
    volume,
    isMuted,
    isLoading,
    repeatMode,
    isShuffled,
    
    // Computed
    progress,
    hasNext,
    hasPrev,
    formattedTime,
    formattedDuration,
    upcomingTracks,
    upcomingCount,
    
    // Actions
    playTrack,
    togglePlay,
    pause,
    play,
    playNext,
    playPrev,
    seek,
    seekTo,
    setVolume,
    toggleMute,
    toggleRepeat,
    toggleShuffle,
    addToQueue,
    addToQueueNext,
    removeFromQueue,
    moveInQueue,
    playFromQueue,
    clearQueue
  }
})

