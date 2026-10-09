import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/client'

/**
 * Authentication store — powered by Pinia.
 * Strictly HR-only: only HR_ADMIN and approved HR/manager roles are permitted.
 * Any non-HR role (e.g., EMPLOYEE) is blocked and redirected to /app.
 * Token persists in sessionStorage (cleared on tab close).
 * No Firebase, no credentials in source code.
 */
export const useAuthStore = defineStore('auth', () => {
  const token    = ref(sessionStorage.getItem('haven_token') ?? null)
  const username = ref(sessionStorage.getItem('haven_user') ?? null)
  const role     = ref(sessionStorage.getItem('haven_role') ?? null)

  // Enforce HR-only check immediately on store load
  if (role.value && role.value !== 'HR_ADMIN' && role.value !== 'MANAGER') {
    sessionStorage.clear()
    token.value = null
    username.value = null
    role.value = null
  }

  const isAuthenticated = computed(() => !!token.value && (role.value === 'HR_ADMIN' || role.value === 'MANAGER'))
  const isHrAdmin  = computed(() => role.value === 'HR_ADMIN')
  const isManager  = computed(() => role.value === 'MANAGER')
  const isAuthorizedHr = computed(() => isHrAdmin.value || isManager.value)

  async function login(usernameInput, password) {
    const data = await authApi.login(usernameInput, password)

    // Decode JWT payload (no signature verification needed client-side)
    const payload = JSON.parse(atob(data.access_token.split('.')[1]))
    const userRole = payload.role ?? null

    // Enforce strictly HR-only roles
    if (userRole !== 'HR_ADMIN' && userRole !== 'MANAGER') {
      logout()
      window.location.href = '/app'
      throw new Error('Access denied: Haven is strictly restricted to HR administrators and managers.')
    }

    token.value    = data.access_token
    username.value = payload.username ?? usernameInput
    role.value     = userRole

    sessionStorage.setItem('haven_token', data.access_token)
    sessionStorage.setItem('haven_user',  username.value)
    sessionStorage.setItem('haven_role',  role.value)
  }

  async function exchangeLogin(exchangeToken) {
    const data = await authApi.exchange(exchangeToken)

    // Decode JWT payload (standard Base64 decoding client-side)
    const payload = JSON.parse(atob(data.access_token.split('.')[1]))
    const userRole = payload.role ?? null

    // Enforce strictly HR-only roles
    if (userRole !== 'HR_ADMIN' && userRole !== 'MANAGER') {
      logout()
      window.location.href = '/app'
      throw new Error('Access denied: Haven is strictly restricted to HR administrators and managers.')
    }

    token.value    = data.access_token
    username.value = payload.username ?? payload.sub ?? 'HR User'
    role.value     = userRole

    // Frontend stores ONLY the Haven session token in sessionStorage
    sessionStorage.setItem('haven_token', data.access_token)
    sessionStorage.setItem('haven_user',  username.value)
    sessionStorage.setItem('haven_role',  role.value)

    return data
  }

  function logout() {
    token.value    = null
    username.value = null
    role.value     = null
    sessionStorage.removeItem('haven_token')
    sessionStorage.removeItem('haven_user')
    sessionStorage.removeItem('haven_role')
    sessionStorage.removeItem('haven_emp_hash')
  }

  return {
    token, username, role,
    isAuthenticated, isHrAdmin, isManager, isAuthorizedHr,
    login, exchangeLogin, logout
  }
})
