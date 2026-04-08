<template>
  <nav class="bottom-nav safe-bottom">
    <button
      v-for="item in navItems"
      :key="item.path"
      type="button"
      class="nav-item"
      :class="{ active: isActive(item.path) }"
      :aria-current="isActive(item.path) ? 'page' : undefined"
      @click="go(item.path)"
    >
      <component :is="item.icon" class="nav-icon" />
      <span class="nav-label">{{ item.label }}</span>
    </button>
  </nav>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'
import IconHome from '../Common/icons/IconHome.vue'
import IconSearch from '../Common/icons/IconSearch.vue'
import IconLibrary from '../Common/icons/IconLibrary.vue'

const route = useRoute()
const router = useRouter()

const navItems = [
  { path: '/', label: 'Главная', icon: IconHome },
  { path: '/search', label: 'Поиск', icon: IconSearch },
  { path: '/library', label: 'Библиотека', icon: IconLibrary }
]

function isActive(path) {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path === path || route.path.startsWith(`${path}/`)
}

function go(path) {
  router.push(path).catch(() => {})
}
</script>

<style scoped>
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: var(--nav-height);
  background: linear-gradient(to top, var(--bg-primary) 85%, transparent);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  display: flex;
  justify-content: space-around;
  align-items: center;
  z-index: 1000;
  border-top: 1px solid var(--border);
  touch-action: manipulation;
}

.nav-item {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: var(--spacing-sm) var(--spacing-md);
  color: var(--text-secondary);
  transition: color var(--transition-fast);
  background: none;
  border: none;
  font: inherit;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.nav-item.active {
  color: var(--text-primary);
}

.nav-icon {
  width: 24px;
  height: 24px;
}

.nav-label {
  font-size: var(--font-size-xs);
  font-weight: 500;
}
</style>

