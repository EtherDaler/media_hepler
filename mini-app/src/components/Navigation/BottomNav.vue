<template>
  <nav class="bottom-nav safe-bottom">
    <router-link 
      v-for="item in navItems" 
      :key="item.path"
      :to="item.path"
      class="nav-item"
      :class="{ active: isActive(item.path) }"
    >
      <component :is="item.icon" class="nav-icon" />
      <span class="nav-label">{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import IconHome from '../Common/icons/IconHome.vue'
import IconSearch from '../Common/icons/IconSearch.vue'
import IconLibrary from '../Common/icons/IconLibrary.vue'

const route = useRoute()

const navItems = [
  { path: '/', label: 'Главная', icon: IconHome },
  { path: '/search', label: 'Поиск', icon: IconSearch },
  { path: '/library', label: 'Библиотека', icon: IconLibrary }
]

function isActive(path) {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path.startsWith(path)
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
  z-index: 100;
  border-top: 1px solid var(--border);
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: var(--spacing-sm) var(--spacing-lg);
  color: var(--text-secondary);
  transition: color var(--transition-fast);
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

