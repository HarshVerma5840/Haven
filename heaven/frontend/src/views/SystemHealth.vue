<template>
  <div class="system-health-view">
    <NeoCard class="header-card">
      <div class="section-header">
        <div>
          <h2 class="section-title">System Infrastructure & Health</h2>
          <p class="section-sub">Real-time health telemetry across API, Dual-Vault PostgreSQL, Redis, CatBoost ML model, and JWE encryption.</p>
        </div>
        <div class="header-actions">
          <NeoButton variant="secondary" size="sm" :loading="checking" @click="checkHealth">
            ↻ Refresh Health Checks
          </NeoButton>
        </div>
      </div>
    </NeoCard>

    <!-- Services Grid -->
    <div class="services-grid">
      <!-- Haven Core API -->
      <NeoCard class="service-card">
        <div class="service-header">
          <div class="service-icon">⚡</div>
          <div>
            <h3 class="service-name">Haven Core API</h3>
            <span class="service-type">FastAPI Microservice</span>
          </div>
        </div>
        <div class="status-indicator-box" :class="apiUp ? 'up' : 'down'">
          <span class="dot" />
          <span class="status-label">{{ apiUp ? 'Operational' : 'API Unavailable' }}</span>
        </div>
        <div class="service-meta">
          <div class="meta-row"><span>Endpoint:</span> <code>/health</code></div>
          <div class="meta-row"><span>Latency:</span> <strong>{{ apiLatency }}ms</strong></div>
          <div class="meta-row"><span>Version:</span> <strong>{{ apiVersion }}</strong></div>
        </div>
      </NeoCard>

      <!-- PostgreSQL Database -->
      <NeoCard class="service-card">
        <div class="service-header">
          <div class="service-icon">🗄</div>
          <div>
            <h3 class="service-name">PostgreSQL Database</h3>
            <span class="service-type">Dual-Vault (Identity + Behavioral)</span>
          </div>
        </div>
        <div class="status-indicator-box" :class="dbUp ? 'up' : 'down'">
          <span class="dot" />
          <span class="status-label">{{ dbUp ? 'Operational' : 'Connection Failed' }}</span>
        </div>
        <div class="service-meta">
          <div class="meta-row"><span>Readiness:</span> <code>SELECT 1</code></div>
          <div class="meta-row"><span>Driver:</span> <strong>asyncpg / psycopg2</strong></div>
          <div class="meta-row"><span>Status:</span> <strong>{{ readyStatus.database ?? (dbUp ? 'ok' : 'error') }}</strong></div>
        </div>
      </NeoCard>

      <!-- ML Burnout Model -->
      <NeoCard class="service-card">
        <div class="service-header">
          <div class="service-icon">🧠</div>
          <div>
            <h3 class="service-name">Burnout ML Model</h3>
            <span class="service-type">CatBoost + TreeSHAP Engine</span>
          </div>
        </div>
        <div class="status-indicator-box" :class="modelUp ? 'up' : 'down'">
          <span class="dot" />
          <span class="status-label">{{ modelUp ? 'Model Loaded & Ready' : 'Model Unavailable' }}</span>
        </div>
        <div class="service-meta">
          <div class="meta-row"><span>Version:</span> <strong>v1.2.0-prod</strong></div>
          <div class="meta-row"><span>Inference Engine:</span> <strong>{{ modelUp ? 'Active' : 'Offline' }}</strong></div>
          <div class="meta-row"><span>Status:</span> <strong>{{ readyStatus.model ?? (modelUp ? 'ok' : 'unavailable') }}</strong></div>
        </div>
      </NeoCard>

      <!-- Redis Cache -->
      <NeoCard class="service-card">
        <div class="service-header">
          <div class="service-icon">🚀</div>
          <div>
            <h3 class="service-name">Redis Cache & Queues</h3>
            <span class="service-type">Rate Limiting & Rate Throttling</span>
          </div>
        </div>
        <div class="status-indicator-box" :class="redisUp ? 'up' : 'down'">
          <span class="dot" />
          <span class="status-label">{{ redisUp ? 'Operational' : 'Unavailable' }}</span>
        </div>
        <div class="service-meta">
          <div class="meta-row"><span>Cluster Status:</span> <strong>{{ redisUp ? 'Connected' : 'Disconnected' }}</strong></div>
          <div class="meta-row"><span>Sync Queue:</span> <strong>Idle</strong></div>
          <div class="meta-row"><span>Status:</span> <strong>{{ readyStatus.redis ?? (redisUp ? 'ok' : 'error') }}</strong></div>
        </div>
      </NeoCard>

      <!-- JWE Encryption & Keys -->
      <NeoCard class="service-card">
        <div class="service-header">
          <div class="service-icon">🛡</div>
          <div>
            <h3 class="service-name">JWE Encryption Engine</h3>
            <span class="service-type">Zero-Knowledge Key Cryptography</span>
          </div>
        </div>
        <div class="status-indicator-box" :class="encryptionUp ? 'up' : 'down'">
          <span class="dot" />
          <span class="status-label">{{ encryptionUp ? 'Keys Active & Validated' : 'Encryption Degraded' }}</span>
        </div>
        <div class="service-meta">
          <div class="meta-row"><span>Algorithm:</span> <strong>RSA-OAEP-256 + A256GCM</strong></div>
          <div class="meta-row"><span>Key Format:</span> <strong>PKCS#8 / PEM</strong></div>
          <div class="meta-row"><span>Status:</span> <strong>{{ readyStatus.encryption ?? (encryptionUp ? 'ok' : 'error') }}</strong></div>
        </div>
      </NeoCard>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { healthApi } from '@/api/client'
import NeoCard from '@/components/NeoCard.vue'
import NeoButton from '@/components/NeoButton.vue'

const checking = ref(false)
const apiUp = ref(true)
const dbUp = ref(true)
const modelUp = ref(true)
const redisUp = ref(true)
const encryptionUp = ref(true)
const apiLatency = ref(18)
const apiVersion = ref('1.0')
const readyStatus = ref({})

async function checkHealth() {
  checking.value = true
  const start = performance.now()
  try {
    const health = await healthApi.check()
    apiUp.value = Boolean(health && (health.status === 'ok' || health.status === 200))
    apiVersion.value = health?.version || '1.0'
    apiLatency.value = Math.max(1, Math.round(performance.now() - start))

    const ready = await healthApi.ready()
    readyStatus.value = ready || {}
    dbUp.value = ready?.database === 'ok'
    modelUp.value = ready?.model === 'ok'
    redisUp.value = ready?.redis === 'ok'
    encryptionUp.value = ready?.encryption === 'ok'
  } catch {
    apiUp.value = false
    dbUp.value = false
    modelUp.value = false
    redisUp.value = false
    encryptionUp.value = false
  } finally {
    checking.value = false
  }
}

onMounted(() => {
  checkHealth()
})
</script>

<style scoped>
.system-health-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.header-card {
  display: flex;
  flex-direction: column;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}
.section-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--brand-navy);
}
.section-sub {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.25rem;
}

.service-card {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 1.5rem;
}

.service-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.service-icon {
  font-size: 1.75rem;
}
.service-name {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 2px;
}
.service-type {
  font-size: 0.725rem;
  color: var(--text-muted);
}

.status-indicator-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0.65rem 1rem;
  border-radius: var(--radius-sm);
  font-size: 0.825rem;
  font-weight: 600;
}
.status-indicator-box.up {
  background: var(--risk-low-bg);
  color: var(--risk-low);
}
.status-indicator-box.down {
  background: var(--risk-high-bg);
  color: var(--risk-high);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.service-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.775rem;
  color: var(--text-secondary);
  border-top: 1px solid var(--border-color);
  padding-top: 0.75rem;
}
.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
