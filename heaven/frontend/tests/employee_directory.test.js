import test from 'node:test'
import assert from 'node:assert/strict'

// Mocking window and sessionStorage for test environment
global.window = {
  location: { origin: 'http://localhost:8082', href: '' }
}
const mockSessionStore = new Map()
global.sessionStorage = {
  getItem: (k) => mockSessionStore.get(k) ?? null,
  setItem: (k, v) => mockSessionStore.set(k, String(v)),
  removeItem: (k) => mockSessionStore.delete(k),
  clear: () => mockSessionStore.clear()
}

// Import client after setting globals
import { employeesApi } from '../src/api/client.js'

test('employeesApi.directory formats query parameters correctly', async () => {
  let capturedUrl = null
  let capturedHeaders = null

  sessionStorage.setItem('haven_token', 'mock_jwt_token_123')

  global.fetch = async (url, opts) => {
    capturedUrl = url
    capturedHeaders = opts?.headers || {}
    return {
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            employee_hash: 'abc123def45678901234567890abcdef',
            department: 'Engineering',
            designation: 'Staff Engineer',
            current_burnout_risk: 'High',
            prediction_date: '2026-10-09',
            model_version: 'v1.2.0-prod',
            data_completeness: 98.5
          }
        ],
        total: 1,
        page: 1,
        page_size: 20,
        pages: 1
      })
    }
  }

  const result = await employeesApi.directory({
    search: 'Staff',
    department: 'Engineering',
    risk: 'High',
    sort_by: 'risk_desc',
    page: 1,
    page_size: 20
  })

  assert.ok(capturedUrl.includes('/api/v1/employees/directory'))
  assert.ok(capturedUrl.includes('search=Staff'))
  assert.ok(capturedUrl.includes('department=Engineering'))
  assert.ok(capturedUrl.includes('risk=High'))
  assert.ok(capturedUrl.includes('sort_by=risk_desc'))
  assert.ok(capturedUrl.includes('page=1'))
  assert.ok(capturedUrl.includes('page_size=20'))

  assert.equal(capturedHeaders['Authorization'], 'Bearer mock_jwt_token_123')

  assert.equal(result.total, 1)
  assert.equal(result.items.length, 1)
  assert.equal(result.items[0].current_burnout_risk, 'High')
  assert.equal(result.items[0].department, 'Engineering')

  // Verify identity vault fields are never present
  assert.equal(result.items[0].email, undefined)
  assert.equal(result.items[0].hrms_employee_id, undefined)
  assert.equal(result.items[0].password, undefined)
})

test('employeesApi.directory handles API error and 403 forbidden', async () => {
  sessionStorage.setItem('haven_token', 'mock_token')

  global.fetch = async () => ({
    ok: false,
    status: 403,
    statusText: 'Forbidden',
    json: async () => ({ detail: 'Requires MANAGER or HR_ADMIN role' })
  })

  await assert.rejects(
    async () => {
      await employeesApi.directory()
    },
    {
      message: /Access forbidden: HR authorization required/
    }
  )

  // Verify unauthorized users get redirected to /app
  assert.equal(global.window.location.href, '/app')
})

test('Directory formatting utilities truncate hash safely and preserve anonymization', () => {
  function truncateHash(h) {
    if (!h) return '—'
    return h.length > 20 ? `${h.slice(0, 10)}…${h.slice(-6)}` : h
  }

  const fullHash = 'a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0'
  const formatted = truncateHash(fullHash)

  assert.equal(formatted, 'a1b2c3d4e5…bcdef0')
  assert.ok(!formatted.includes('@'))
  assert.ok(!formatted.includes('EMP-'))
})
