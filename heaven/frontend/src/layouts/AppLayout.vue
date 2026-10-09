<template>
  <div class="app-layout">
    <!-- Sidebar -->
    <aside class="sidebar" :class="{ 'sidebar--open': sidebarOpen }">
      <div class="sidebar__brand">
        <span class="brand-icon">🛡</span>
        <span class="brand-name">Haven</span>
      </div>

      <nav class="sidebar__nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          active-class="nav-item--active"
          @click="sidebarOpen = false"
        >
          <span class="nav-item__icon">{{ item.icon }}</span>
          <span class="nav-item__label">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar__footer">
        <div class="user-pill">
          <div class="user-pill__avatar">{{ userInitial }}</div>
          <div class="user-pill__info">
            <div class="user-pill__name truncate">{{ auth.username }}</div>
            <div class="user-pill__role">{{ formatRole(auth.role) }}</div>
          </div>
        </div>
        <button class="logout-btn" @click="handleLogout" title="Sign out">
          <span>⎋</span>
        </button>
      </div>
    </aside>

    <!-- Overlay for mobile -->
    <div
      v-if="sidebarOpen"
      class="sidebar-overlay"
      @click="sidebarOpen = false"
    />

    <!-- Main -->
    <div class="main-wrapper">
      <header class="top-bar">
        <button class="hamburger" @click="sidebarOpen = !sidebarOpen">
          <span /><span /><span />
        </button>
        <h1 class="page-title">{{ currentPageTitle }}</h1>
        <div class="top-bar__right">
          <a href="/app" class="desk-nav-btn" title="Back to HRMS Desk">← HRMS Desk</a>
          <span class="status-dot" :class="statusClass" />
          <span class="status-text">{{ statusText }}</span>
        </div>
      </header>

      <main class="page-content">
        <RouterView v-slot="{ Component }">
          <Transition name="fade" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { healthApi } from '@/api/client'

const auth   = useAuthStore()
const router = useRouter()
const route  = useRoute()

const sidebarOpen = ref(false)
const apiOnline   = ref(null) // null = checking, true = up, false = down

// Build nav based on HR-only roles
const allNavItems = [
  { to: '/dashboard',   label: 'HR Dashboard',       icon: '📊', roles: ['HR_ADMIN', 'MANAGER'] },
  { to: '/directory',   label: 'Employee Directory', icon: '👥', roles: ['HR_ADMIN', 'MANAGER'] },
  { to: '/burnout',     label: 'Burnout Analysis',   icon: '🔥', roles: ['HR_ADMIN', 'MANAGER'] },
  { to: '/network',     label: 'Network Graph',      icon: '🕸', roles: ['HR_ADMIN', 'MANAGER'] },
  { to: '/integration', label: 'HRMS Integration',   icon: '🔄', roles: ['HR_ADMIN', 'MANAGER'] },
  { to: '/health',      label: 'System Health',      icon: '🩺', roles: ['HR_ADMIN', 'MANAGER'] },
  { to: '/admin/users', label: 'User Management',    icon: '⚙',  roles: ['HR_ADMIN'] },
]
const navItems = computed(() =>
  allNavItems.filter(i => i.roles.includes(auth.role))
)

const userInitial = computed(() =>
  (auth.username ?? '?').charAt(0).toUpperCase()
)

const currentPageTitle = computed(() => {
  const map = {
    dashboard:    'HR Overview Dashboard',
    directory:    'Employee Risk Directory',
    burnout:      'Burnout Analysis',
    employee:     'Employee Burnout Profile',
    network:      'Organizational Network Graph',
    integration:  'HRMS Integration Status',
    health:       'System Health & Infrastructure',
    'admin-users':'User Management',
  }
  return map[route.name] ?? 'Haven'
})

const statusClass = computed(() => ({
  'status-dot--up':   apiOnline.value === true,
  'status-dot--down': apiOnline.value === false,
  'status-dot--idle': apiOnline.value === null,
}))
const statusText = computed(() => {
  if (apiOnline.value === null)  return 'Connecting…'
  if (apiOnline.value === true)  return 'API online'
  return 'API offline'
})

function formatRole(r) {
  const map = { HR_ADMIN: 'HR Admin', MANAGER: 'HR Manager' }
  return map[r] ?? r
}

async function handleLogout() {
  auth.logout()
  await router.push({ name: 'login' })
}

onMounted(async () => {
  try {
    await healthApi.check()
    apiOnline.value = true
  } catch {
    apiOnline.value = false
  }
})
</script>

<style scoped>
/* ── Layout Shell ─────────────────────────── */
.app-layout {
  display: flex;
  min-height: 100vh;
}

/* ── Sidebar ──────────────────────────────── */
.sidebar {
  position: fixed;
  top: 0; left: 0; bottom: 0;
  width: var(--sidebar-width);
  background: var(--bg-sidebar);
  box-shadow: var(--shadow-raised);
  display: flex;
  flex-direction: column;
  z-index: 200;
  transition: transform var(--transition-med);
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 1.25rem 1.25rem 1rem;
  border-bottom: 1px solid var(--border-color);
}
.brand-icon { font-size: 1.5rem; }
.brand-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--brand-navy);
  letter-spacing: -0.02em;
}

/* Nav */
.sidebar__nav {
  flex: 1;
  padding: 0.75rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0.65rem 0.9rem;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
  transition: background var(--transition-fast), color var(--transition-fast), box-shadow var(--transition-fast);
}
.nav-item:hover {
  background: var(--bg-base);
  color: var(--text-primary);
}
.nav-item--active {
  background: var(--bg-base);
  color: var(--brand-navy);
  box-shadow: var(--shadow-inset-sm);
  font-weight: 600;
}
.nav-item__icon { font-size: 1rem; width: 20px; text-align: center; }

/* Sidebar footer */
.sidebar__footer {
  padding: 1rem;
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 8px;
}
.user-pill {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.user-pill__avatar {
  width: 34px; height: 34px;
  border-radius: 50%;
  background: var(--brand-navy);
  color: var(--text-inverse);
  font-size: 0.875rem;
  font-weight: 600;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.user-pill__info { min-width: 0; }
.user-pill__name { font-size: 0.8rem; font-weight: 600; color: var(--text-primary); }
.user-pill__role { font-size: 0.7rem; color: var(--text-muted); }

.logout-btn {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  transition: background var(--transition-fast), color var(--transition-fast);
  flex-shrink: 0;
}
.logout-btn:hover { background: var(--risk-high-bg); color: var(--risk-high); }

/* ── Main Wrapper ─────────────────────────── */
.main-wrapper {
  margin-left: var(--sidebar-width);
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ── Top Bar ──────────────────────────────── */
.top-bar {
  height: var(--header-height);
  background: var(--bg-card);
  box-shadow: var(--shadow-raised-sm);
  display: flex;
  align-items: center;
  padding: 0 1.5rem;
  gap: 1rem;
  position: sticky; top: 0; z-index: 100;
}
.hamburger {
  display: none;
  flex-direction: column;
  gap: 5px;
  padding: 4px;
}
.hamburger span {
  display: block; width: 22px; height: 2px;
  background: var(--text-primary);
  border-radius: 2px;
  transition: transform var(--transition-fast);
}
.page-title {
  flex: 1;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}
.top-bar__right {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.75rem;
  color: var(--text-muted);
}
.desk-nav-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  box-shadow: var(--shadow-raised-sm);
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 600;
  text-decoration: none;
  transition: all var(--transition-fast);
}
.desk-nav-btn:hover {
  color: var(--brand-navy);
  box-shadow: var(--shadow-inset-sm);
}
.status-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
}
.status-dot--up   { background: var(--risk-low); }
.status-dot--down { background: var(--risk-high); }
.status-dot--idle { background: var(--risk-medium); }

/* ── Page Content ─────────────────────────── */
.page-content {
  flex: 1;
  padding: 1.75rem;
  overflow-y: auto;
}

/* ── Route Transition ─────────────────────── */
.fade-enter-active, .fade-leave-active { transition: opacity var(--transition-fast); }
.fade-enter-from, .fade-leave-to       { opacity: 0; }

/* ── Sidebar Overlay (mobile) ─────────────── */
.sidebar-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.3);
  z-index: 150;
}

/* ── Responsive ───────────────────────────── */
@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
  }
  .sidebar--open {
    transform: translateX(0);
  }
  .main-wrapper {
    margin-left: 0;
  }
  .hamburger {
    display: flex;
  }
  .page-content {
    padding: 1rem;
  }
}
</style>
