/**
 * Haven API Client
 * Strictly HR-only integration.
 * Credentials and tokens are stored in sessionStorage — never in source code.
 */

const BASE_URL = (typeof window !== 'undefined' && window.haven_api_base)
  ? window.haven_api_base
  : (import.meta.env?.VITE_API_BASE_URL ?? '/api/v1')

function getToken() {
  return sessionStorage.getItem('haven_token')
}

async function request(method, path, { body, params } = {}) {
  const url = new URL(BASE_URL + path, window.location.origin)

  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) url.searchParams.set(k, v)
    })
  }

  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(url.toString(), {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined
  })

function getLoginUrl() {
  if (typeof window !== 'undefined' && import.meta.env?.DEV && !window.location.pathname.startsWith('/heaven/app')) {
    return '/login'
  }
  return '/heaven/app/login'
}

  if (res.status === 401) {
    sessionStorage.removeItem('haven_token')
    sessionStorage.removeItem('haven_user')
    sessionStorage.removeItem('haven_role')
    window.location.href = getLoginUrl()
    return
  }

  if (res.status === 403) {
    // Non-HR users blocked
    window.location.href = '/app'
    throw new Error('Access forbidden: HR authorization required.')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Request failed')
  }

  if (res.status === 204) return null
  return res.json()
}

// ── Auth ──────────────────────────────────────────────────────
export const authApi = {
  login(username, password) {
    const body = new URLSearchParams({ username, password, grant_type: 'password' })
    const token = getToken()
    return fetch(BASE_URL + '/auth/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: body.toString()
    }).then(async res => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail ?? 'Login failed')
      }
      return res.json()
    })
  },
  exchange(exchangeToken) {
    return fetch(BASE_URL + '/auth/exchange', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ exchange_token: exchangeToken })
    }).then(async res => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail ?? 'Exchange failed')
      }
      return res.json()
    })
  },
  async fetchHrmsExchangeToken() {
    try {
      const res = await fetch('/api/method/hrms.api.haven_auth.get_sso_exchange_token', {
        method: 'GET',
        headers: {
          'X-Frappe-CSRF-Token': window.csrf_token || ''
        }
      })
      if (!res.ok) return null
      const data = await res.json()
      return data.message?.exchange_token ?? null
    } catch {
      return null
    }
  },
  createUser(userData) {
    return request('POST', '/auth/register', { body: userData })
  }
}

// ── Predictions ───────────────────────────────────────────────
export const predictionsApi = {
  predict(metrics, includeExplanations = false) {
    return request('POST', '/predictions', {
      body: { metrics, include_explanations: includeExplanations }
    })
  },
  explain(metrics) {
    return request('POST', '/predictions/explain', {
      body: { metrics, include_explanations: true }
    })
  }
}

// ── Analytics ─────────────────────────────────────────────────
export const analyticsApi = {
  dashboard(params = {}) {
    return request('GET', '/analytics/dashboard', { params })
  },
  network(params = {}) {
    return request('GET', '/analytics/network', { params })
  }
}

// ── Employees ─────────────────────────────────────────────────
export const employeesApi = {
  get(employeeHash) {
    return request('GET', `/employees/${employeeHash}`)
  },
  directory(params = {}) {
    return request('GET', '/employees/directory', { params })
  }
}

// ── Vault ─────────────────────────────────────────────────────
export const vaultApi = {
  listIdentityMappings(skip = 0, limit = 100) {
    return request('GET', '/vault/identity', { params: { skip, limit } })
  },
  getPredictions(employeeHash, skip = 0, limit = 50) {
    return request('GET', `/vault/behavioral/predictions/${employeeHash}`, {
      params: { skip, limit }
    })
  }
}

// ── HRMS Integration ──────────────────────────────────────────
export const integrationApi = {
  getStatus() {
    return request('GET', '/analytics/integration')
  }
}

// ── Health ────────────────────────────────────────────────────
export const healthApi = {
  async check() {
    let res = await fetch(BASE_URL + '/health').catch(() => null)
    if (!res || !res.ok) {
      res = await fetch('/health').catch(() => null)
    }
    if (!res || !res.ok) throw new Error(`Health check failed: ${res ? res.statusText : 'Offline'}`)
    return res.json()
  },
  async ready() {
    const token = getToken()
    const headers = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`
    let res = await fetch(BASE_URL + '/ready', { headers }).catch(() => null)
    if (!res || !res.ok) {
      res = await fetch('/ready', { headers }).catch(() => null)
    }
    if (res && res.status === 401) {
      sessionStorage.removeItem('haven_token')
      window.location.href = getLoginUrl()
      return
    }
    if (!res || !res.ok) throw new Error(`Readiness check failed: ${res ? res.statusText : 'Offline'}`)
    return res.json()
  }
}

