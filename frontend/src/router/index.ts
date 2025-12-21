import { createRouter, createWebHistory } from 'vue-router'
import CharacterView from '../views/CharacterView.vue'
import HomeView from '../views/HomeView.vue' // <--- Import the new view

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView // <--- Use the Hub here
    },
    {
      path: '/character/:id',
      name: 'character',
      component: CharacterView
    }
  ]
})

export default router