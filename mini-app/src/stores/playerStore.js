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
    })

    audio.addEventListener('timeupdate', () => {
      currentTime.value = audio.currentTime
    })

    audio.addEventListener('ended', () => {
      handleTrackEnd()
    })

    audio.addEventListener('playing', () => {
      isPlaying.value = true
      isLoading.value = false
    })

    audio.addEventListener('pause', () => {
      isPlaying.value = false
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

    return audio
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

  function toggleShuffle() {
    isShuffled.value = !isShuffled.value
    // TODO: Реализовать shuffle логику
  }

  function handleTrackEnd() {
    if (repeatMode.value === 'one') {
      audio.currentTime = 0
      audio.play()
      return
    }
    playNext()
  }

  function addToQueue(track) {
    queue.value.push(track)
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
    clearQueue
  }
})

