import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('./views/HomeView.vue')
  },
  {
    path: '/library',
    name: 'Library',
    component: () => import('./views/LibraryView.vue')
  },
  {
    path: '/playlist/:id',
    name: 'Playlist',
    component: () => import('./views/PlaylistView.vue')
  },
  {
    path: '/favorites',
    name: 'Favorites',
    component: () => import('./views/FavoritesView.vue')
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('./views/SearchView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

