import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'
import Result from '@/views/Result.vue'
import History from '@/views/History.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: Home },
    { path: '/result', name: 'result', component: Result },
    { path: '/history', name: 'history', component: History }
  ],
  scrollBehavior: () => ({ top: 0 })
})
