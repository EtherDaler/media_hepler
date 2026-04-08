import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './styles/main.css'

// Инициализация Telegram WebApp (на части клиентов, в т.ч. Desktop macOS, ready/expand теоретически могут бросить — тогда не выполнится весь модуль и будет белый экран)
const tg = window.Telegram?.WebApp

if (tg) {
  try {
    if (typeof tg.ready === 'function') tg.ready()
    if (typeof tg.expand === 'function') tg.expand()
  } catch (e) {
    console.error('Telegram WebApp ready/expand:', e)
  }

  try {
    document.documentElement.setAttribute('data-theme', tg.colorScheme || 'dark')
    if (typeof tg.onEvent === 'function') {
      tg.onEvent('themeChanged', () => {
        document.documentElement.setAttribute('data-theme', tg.colorScheme || 'dark')
      })
    }
  } catch (e) {
    console.error('Telegram WebApp theme:', e)
  }
}

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Глобально доступный Telegram WebApp
app.config.globalProperties.$tg = tg

app.mount('#app')

