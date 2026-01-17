import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './styles/main.css'

// Инициализация Telegram WebApp
const tg = window.Telegram?.WebApp

if (tg) {
  tg.ready()
  tg.expand()
  
  // Устанавливаем тему
  document.documentElement.setAttribute('data-theme', tg.colorScheme || 'dark')
  
  // Слушаем изменение темы
  tg.onEvent('themeChanged', () => {
    document.documentElement.setAttribute('data-theme', tg.colorScheme)
  })
}

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Глобально доступный Telegram WebApp
app.config.globalProperties.$tg = tg

app.mount('#app')

