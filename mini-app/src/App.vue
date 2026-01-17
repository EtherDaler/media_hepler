<template>
  <!-- Проверка что открыто в Telegram -->
  <div v-if="!isTelegram" class="not-telegram">
    <div class="not-telegram-content">
      <div class="tg-icon">📱</div>
      <h1>Media Helper</h1>
      <p>Это приложение работает только в Telegram</p>
      <a href="https://t.me/your_bot" class="tg-link">Открыть в Telegram</a>
    </div>
  </div>

  <div v-else class="app" :class="{ 'player-open': playerStore.currentTrack }">
    <!-- Main Content -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- Full Player (overlay) -->
    <FullPlayer v-if="showFullPlayer" @close="showFullPlayer = false" />

    <!-- Bottom Player -->
    <MiniPlayer 
      v-if="playerStore.currentTrack && !showFullPlayer" 
      @open-full="showFullPlayer = true"
    />

    <!-- Bottom Navigation -->
    <BottomNav v-if="!showFullPlayer" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { usePlayerStore } from './stores/playerStore'
import MiniPlayer from './components/Player/MiniPlayer.vue'
import FullPlayer from './components/Player/FullPlayer.vue'
import BottomNav from './components/Navigation/BottomNav.vue'

const playerStore = usePlayerStore()
const showFullPlayer = ref(false)

// Проверяем что открыто в Telegram
const isTelegram = computed(() => {
  return !!window.Telegram?.WebApp?.initData
})
</script>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--bg-primary);
}

.main-content {
  flex: 1;
  overflow-y: auto;
  padding-bottom: calc(var(--nav-height) + env(safe-area-inset-bottom));
}

.app.player-open .main-content {
  padding-bottom: calc(var(--nav-height) + var(--player-height) + env(safe-area-inset-bottom));
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Not Telegram Screen */
.not-telegram {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  padding: var(--spacing-lg);
}

.not-telegram-content {
  text-align: center;
}

.tg-icon {
  font-size: 64px;
  margin-bottom: var(--spacing-lg);
}

.not-telegram h1 {
  font-size: var(--font-size-2xl);
  margin-bottom: var(--spacing-sm);
  color: var(--text-primary);
}

.not-telegram p {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-lg);
}

.tg-link {
  display: inline-block;
  padding: var(--spacing-md) var(--spacing-xl);
  background: var(--accent);
  color: var(--bg-primary);
  border-radius: var(--radius-full);
  font-weight: 600;
}
</style>

