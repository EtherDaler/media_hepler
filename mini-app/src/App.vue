<template>
  <div class="app" :class="{ 'player-open': playerStore.currentTrack }">
    <!-- Main Content -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- Bottom Player -->
    <MiniPlayer v-if="playerStore.currentTrack" />

    <!-- Bottom Navigation -->
    <BottomNav />
  </div>
</template>

<script setup>
import { usePlayerStore } from './stores/playerStore'
import MiniPlayer from './components/Player/MiniPlayer.vue'
import BottomNav from './components/Navigation/BottomNav.vue'

const playerStore = usePlayerStore()
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
</style>

