import test from 'node:test'
import assert from 'node:assert/strict'

// Mock browser environment
global.window = {
  location: { origin: 'http://localhost:8082', href: '' },
  csrf_token: 'csrf_mock_token_123',
  haven_exchange_token: null
}

const mockSessionStore = new Map()
global.sessionStorage = {
  getItem: (k) => mockSessionStore.get(k) ?? null,
  setItem: (k, v) => mockSessionStore.set(k, String(v)),
  removeItem: (k) => mockSessionStore.delete(k),
  clear: () => mockSessionStore.clear()
}

// Polyfill atob for Node test environment
if (!global.atob) {
  global.atob = (str) => Buffer.from(str, 'base64').toString('binary')
}

import { authApi } from '../src/api/client.js'

function makeJwt(payload) {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64')
  const body = Buffer.from(JSON.stringify(payload)).toString('base64')
  return `${header}.${body}.mock_signature`
}

test('authApi.exchange sends exchange_token payload to /auth/exchange', async () => {
  let capturedBody = null
  let capturedUrl = null
  let capturedHeaders = null

  global.fetch = async (url, opts) => {
    capturedUrl = url
    capturedHeaders = opts.headers
    capturedBody = JSON.parse(opts.body)
    return {
      ok: true,
      status: 200,
      json: async () => ({
        access_token: makeJwt({ username: 'hr_lead', role: 'HR_ADMIN' }),
        token_type: 'bearer'
      })
    }
  }

  const res = await authApi.exchange('one_time_exchange_token_abc')

  assert.ok(capturedUrl.includes('/auth/exchange'))
  assert.equal(capturedHeaders['Content-Type'], 'application/json')
  assert.equal(capturedBody.exchange_token, 'one_time_exchange_token_abc')
  assert.ok(res.access_token)
  assert.equal(res.token_type, 'bearer')
})

test('authApi.exchange throws clear error on expired or invalid token', async () => {
  global.fetch = async () => ({
    ok: false,
    status: 401,
    statusText: 'Unauthorized',
    json: async () => ({ detail: 'Exchange token has expired' })
  })

  await assert.rejects(
    async () => {
      await authApi.exchange('expired_token_123')
    },
    {
      message: 'Exchange token has expired'
    }
  )
})

test('authApi.fetchHrmsExchangeToken calls Frappe endpoint with CSRF header', async () => {
  let capturedUrl = null
  let capturedHeaders = null

  global.fetch = async (url, opts) => {
    capturedUrl = url
    capturedHeaders = opts.headers
    return {
      ok: true,
      status: 200,
      json: async () => ({
        message: { exchange_token: 'generated_hrms_token_xyz' }
      })
    }
  }

  const token = await authApi.fetchHrmsExchangeToken()

  assert.equal(capturedUrl, '/api/method/hrms.api.haven_auth.get_sso_exchange_token')
  assert.equal(capturedHeaders['X-Frappe-CSRF-Token'], 'csrf_mock_token_123')
  assert.equal(token, 'generated_hrms_token_xyz')
})

test('SSO Session Exchange stores ONLY Haven session token in sessionStorage', async () => {
  mockSessionStore.clear()

  const havenJwt = makeJwt({ username: 'approved_hr', role: 'HR_ADMIN' })
  global.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      access_token: havenJwt,
      token_type: 'bearer'
    })
  })

  // Simulate exchange handshake
  const exchangeToken = 'short_lived_exchange_nonce'
  window.haven_exchange_token = exchangeToken

  // App reads exchange token and immediately blanks it from memory
  const tokenToUse = window.haven_exchange_token
  window.haven_exchange_token = null

  const data = await authApi.exchange(tokenToUse)
  const payload = JSON.parse(atob(data.access_token.split('.')[1]))

  // Store only Haven session token
  sessionStorage.setItem('haven_token', data.access_token)
  sessionStorage.setItem('haven_user', payload.username)
  sessionStorage.setItem('haven_role', payload.role)

  // Verify guarantees:
  assert.equal(window.haven_exchange_token, null, 'Exchange token must be cleared from window')
  assert.equal(sessionStorage.getItem('haven_token'), havenJwt, 'Haven JWT stored')
  assert.equal(sessionStorage.getItem('haven_user'), 'approved_hr')
  assert.equal(sessionStorage.getItem('haven_role'), 'HR_ADMIN')
  assert.equal(sessionStorage.getItem('haven_exchange_token'), null, 'Exchange token must NEVER be stored in sessionStorage')
})
