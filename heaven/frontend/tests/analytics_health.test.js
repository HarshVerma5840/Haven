import test from 'node:test'
import assert from 'node:assert/strict'

// Mock environment
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

import { analyticsApi, integrationApi, healthApi } from '../src/api/client.js'

test('analyticsApi.network passes department, graph_type, and date params', async () => {
  let capturedUrl = null
  sessionStorage.setItem('haven_token', 'test_jwt_token')

  global.fetch = async (url) => {
    capturedUrl = url
    return {
      ok: true,
      status: 200,
      json: async () => ({
        nodes: [
          { id: 'hash1', department: 'Engineering', risk: 'High', centrality: 0.82, degree: 6 }
        ],
        edges: [
          { source: 'hash1', target: 'hash2', weight: 2.0 }
        ]
      })
    }
  }

  const res = await analyticsApi.network({
    department: 'Engineering',
    graph_type: 'collaboration',
    date: '2026-10-09'
  })

  assert.ok(capturedUrl.includes('/api/v1/analytics/network'))
  assert.ok(capturedUrl.includes('department=Engineering'))
  assert.ok(capturedUrl.includes('graph_type=collaboration'))
  assert.ok(capturedUrl.includes('date=2026-10-09'))

  assert.equal(res.nodes.length, 1)
  assert.equal(res.nodes[0].risk, 'High')
  assert.equal(res.edges.length, 1)
})

test('integrationApi.getStatus retrieves HRMS encryption and ingestion status', async () => {
  sessionStorage.setItem('haven_token', 'test_jwt_token')

  global.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      hrms_connection_status: 'Connected',
      last_successful_ingestion: '2026-10-09T23:45:00Z',
      records_received: 156,
      records_failed: 0,
      jwe_encryption_status: 'RSA-OAEP-256 + A256GCM (Zero-Knowledge Transmitted)',
      service_token_status: 'Active & Validated',
      data_completeness: 96.4,
      is_live: true
    })
  })

  const res = await integrationApi.getStatus()

  assert.equal(res.hrms_connection_status, 'Connected')
  assert.equal(res.records_received, 156)
  assert.equal(res.records_failed, 0)
  assert.ok(res.jwe_encryption_status.includes('RSA-OAEP-256'))
  assert.ok(res.service_token_status.includes('Active'))
  assert.equal(res.data_completeness, 96.4)
})

test('healthApi.ready retrieves status for database, model, redis, and encryption', async () => {
  sessionStorage.setItem('haven_token', 'test_jwt_token')

  global.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      status: 'ok',
      database: 'ok',
      model: 'ok',
      redis: 'ok',
      encryption: 'ok'
    })
  })

  const res = await healthApi.ready()

  assert.equal(res.status, 'ok')
  assert.equal(res.database, 'ok')
  assert.equal(res.model, 'ok')
  assert.equal(res.redis, 'ok')
  assert.equal(res.encryption, 'ok')
})
