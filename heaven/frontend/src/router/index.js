import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Layouts
import AppLayout from '@/layouts/AppLayout.vue'
import AuthLayout from '@/layouts/AuthLayout.vue'

// Views
import Login from '@/views/Login.vue'
import Dashboard from '@/views/Dashboard.vue'
import BurnoutAnalysis from '@/views/BurnoutAnalysis.vue'
import EmployeeDirectory from '@/views/EmployeeDirectory.vue'
import EmployeeDetail from '@/views/EmployeeDetail.vue'
import NetworkGraph from '@/views/NetworkGraph.vue'
import IntegrationStatus from '@/views/IntegrationStatus.vue'
import SystemHealth from '@/views/SystemHealth.vue'
import AdminUsers from '@/views/AdminUsers.vue'
import NotFound from '@/views/NotFound.vue'

const routes = [
  {
    path: '/login',
    component: AuthLayout,
    children: [{ path: '', name: 'login', component: Login }],
    meta: { public: true }
  },
  {
    path: '/',
    component: AppLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '',           redirect: '/dashboard' },
      { path: 'dashboard',  name: 'dashboard',  component: Dashboard,          meta: { roles: ['HR_ADMIN', 'MANAGER'] } },
      { path: 'burnout',    name: 'burnout',    component: BurnoutAnalysis,    meta: { roles: ['HR_ADMIN', 'MANAGER'] } },
      { path: 'directory',  name: 'directory',  component: EmployeeDirectory,  meta: { roles: ['HR_ADMIN', 'MANAGER'] } },
      { path: 'employee/:hash', name: 'employee', component: EmployeeDetail,   meta: { roles: ['HR_ADMIN', 'MANAGER'] } },
      { path: 'network',    name: 'network',    component: NetworkGraph,       meta: { roles: ['HR_ADMIN', 'MANAGER'] } },
      { path: 'integration',name: 'integration',component: IntegrationStatus,  meta: { roles: ['HR_ADMIN', 'MANAGER'] } },
      { path: 'health',     name: 'health',     component: SystemHealth,       meta: { roles: ['HR_ADMIN', 'MANAGER'] } },
      { path: 'admin/users',name: 'admin-users',component: AdminUsers,         meta: { roles: ['HR_ADMIN'] } },
      // Legacy or employee routes redirect immediately to HRMS Desk
      { path: 'my-risk',    beforeEnter: () => { window.location.href = '/app' } },
    ]
  },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFound }
]

const historyBase = (typeof window !== 'undefined' && import.meta.env.DEV && !window.location.pathname.startsWith('/heaven/app'))
  ? '/'
  : '/heaven/app/'

const router = createRouter({
  history: createWebHistory(historyBase),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

let ssoAttempted = false

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()

  // 1. One-time SSO session exchange handshake
  if (!auth.isAuthenticated && !ssoAttempted) {
    let exchangeToken = null

    // Check query parameter
    if (to.query?.exchange_token) {
      exchangeToken = to.query.exchange_token
      // Remove exchange token from URL immediately to prevent exposure in history
      try {
        const cleanUrl = new URL(window.location.href)
        cleanUrl.searchParams.delete('exchange_token')
        window.history.replaceState({}, document.title, cleanUrl.pathname + cleanUrl.search)
      } catch {}
    } else if (window.haven_exchange_token) {
      // Pick up token from window and clear immediately from memory
      exchangeToken = window.haven_exchange_token
      window.haven_exchange_token = null
    }

    if (exchangeToken) {
      ssoAttempted = true
      try {
        await auth.exchangeLogin(exchangeToken)
      } catch (err) {
        console.warn('SSO exchange failed, falling back to login:', err.message)
      }
    }
  }

  // If already authenticated and visiting login page, redirect to dashboard
  if (to.name === 'login' && auth.isAuthenticated) {
    const target = to.query.redirect || '/dashboard'
    return next(target)
  }

  if (to.meta.public) return next()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return next({ name: 'login', query: { redirect: to.fullPath } })
  }

  // Strictly HR-only: any employee or unauthorized user is redirected to HRMS Desk
  if (!auth.isAuthorizedHr) {
    window.location.href = '/app'
    return
  }

  if (to.meta.roles && !to.meta.roles.includes(auth.role)) {
    // If manager hits HR_ADMIN-only route, redirect to dashboard
    return next({ name: 'dashboard' })
  }

  next()
})

export default router
