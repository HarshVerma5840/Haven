import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Dashboard from './views/Dashboard.vue'
import BurnoutAnalysis from './views/BurnoutAnalysis.vue'
import ChatInterface from './views/ChatInterface.vue'
import './style.css'

const router = createRouter({
  history: createWebHistory('/heaven/app/'),
  routes: [
    { path: '/', component: Dashboard },
    { path: '/burnout', component: BurnoutAnalysis },
    { path: '/chat', component: ChatInterface },
  ],
})

createApp(App).use(router).mount('#app')

