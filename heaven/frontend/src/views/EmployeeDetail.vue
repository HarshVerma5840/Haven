<template>
  <div class="employee-view">
    <div v-if="loading" class="loading-state">
      <div class="spinner" /> Loading employee profile…
    </div>
    <div v-else-if="error" class="error-state">⚠ {{ error }}</div>
    <template v-else>
      <!-- Employee Profile Header (Pseudonymized Hash Only) -->
      <NeoCard class="profile-card">
        <div class="profile-header">
          <div class="profile-avatar">🛡</div>
          <div class="profile-info">
            <h2 class="profile-name">{{ truncateHash(hash) }}</h2>
            <div class="profile-meta">
              <span class="meta-tag">Identity-Vault Pseudonymized</span>
              <span class="meta-tag">Department: {{ metrics.department || '—' }}</span>
              <span class="meta-tag">Completeness: <strong>{{ metrics.data_completeness != null ? `${Math.round(metrics.data_completeness)}%` : '—' }}</strong></span>
            </div>
          </div>
          <div class="profile-actions">
            <RiskBadge :risk="latestRisk" size="lg" />
            <NeoButton variant="secondary" size="sm" @click="$router.back()">← Back</NeoButton>
          </div>
        </div>
      </NeoCard>

      <!-- Behavioral & Work Pattern Metrics Grid -->
      <div class="metrics-grid">
        <NeoCard class="metric-block">
          <div class="metric-block__label">Attendance & Working Hours</div>
          <div class="metric-block__val">{{ metrics.avg_daily_work_hours != null ? `${metrics.avg_daily_work_hours} hrs/day` : '—' }}</div>
          <div class="metric-block__sub">
            Overtime: <strong>{{ metrics.overtime_hours != null ? `${metrics.overtime_hours} hrs/wk` : '—' }}</strong> · Late entries: <strong>{{ metrics.late_entry_count != null ? metrics.late_entry_count : '—' }}</strong>
          </div>
        </NeoCard>

        <NeoCard class="metric-block">
          <div class="metric-block__label">Leave & Workday Pattern</div>
          <div class="metric-block__val">{{ metrics.leave_days_taken != null ? `${metrics.leave_days_taken} days taken` : '—' }}</div>
          <div class="metric-block__sub">
            Weekend work days: <strong>{{ metrics.weekend_work_days != null ? metrics.weekend_work_days : '0' }}</strong>
          </div>
        </NeoCard>

        <NeoCard class="metric-block">
          <div class="metric-block__label">Collaboration & Timesheets</div>
          <div class="metric-block__val">{{ metrics.weekly_timesheet_hours != null ? `${metrics.weekly_timesheet_hours} hrs` : '—' }}</div>
          <div class="metric-block__sub">
            Designation: <strong>{{ metrics.designation || '—' }}</strong>
          </div>
        </NeoCard>

        <NeoCard class="metric-block">
          <div class="metric-block__label">Assessment & Model Version</div>
          <div class="metric-block__val">Risk: {{ metrics.current_burnout_risk || '—' }}</div>
          <div class="metric-block__sub">
            Model: <strong>{{ metrics.model_version || 'v1.2.0-prod' }}</strong> · Date: <strong>{{ metrics.prediction_date || '—' }}</strong>
          </div>
        </NeoCard>
      </div>

      <!-- Prediction History Table -->
      <NeoCard>
        <div class="section-header">
          <h3 class="section-title">Burnout Prediction History</h3>
          <span class="section-badge">{{ metrics.model_version || 'CatBoost Model v1.2.0' }}</span>
        </div>

        <DataTable :columns="columns" :rows="predictions" :loading="predLoading" :error="predError">
          <template #cell-predicted_risk="{ value }">
            <RiskBadge :risk="value" />
          </template>
          <template #cell-probabilities="{ value }">
            <div v-if="value" class="prob-bars">
              <span class="prob-tag" :title="`High: ${pct(value.High)}`">H: {{ pct(value.High) }}</span>
              <span class="prob-tag" :title="`Medium: ${pct(value.Medium)}`">M: {{ pct(value.Medium) }}</span>
              <span class="prob-tag" :title="`Low: ${pct(value.Low)}`">L: {{ pct(value.Low) }}</span>
            </div>
            <span v-else class="text-muted">—</span>
          </template>
          <template #cell-shap_explanations="{ value }">
            <NeoButton v-if="value" variant="ghost" size="sm" @click="showShap(value)">
              View Factors →
            </NeoButton>
            <span v-else class="text-muted">—</span>
          </template>
        </DataTable>

        <p v-if="!predLoading && !predError && predictions.length === 0" class="empty-history-msg">
          No prediction history recorded for this employee.
        </p>
      </NeoCard>
    </template>

    <!-- SHAP Modal -->
    <ModalDialog :open="shapModal" title="SHAP Explainability Factors" @close="shapModal = false">
      <div class="shap-modal-list">
        <p v-if="Object.keys(shapData).length" class="shap-intro">Features increasing (+) or decreasing (-) burnout risk for this employee.</p>
        <div v-for="(val, feat) in shapData" :key="feat" class="shap-row">
          <span class="shap-row__feat">{{ formatFeatureName(feat) }}</span>
          <span class="shap-row__val" :class="val >= 0 ? 'pos' : 'neg'">
            {{ val >= 0 ? '+' : '' }}{{ typeof val === 'number' ? val.toFixed(4) : val }}
          </span>
        </div>
        <p v-if="!Object.keys(shapData).length" class="empty-shap">
          No SHAP feature explanation recorded for this prediction.
        </p>
      </div>
    </ModalDialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { vaultApi, employeesApi } from '@/api/client'
import NeoCard    from '@/components/NeoCard.vue'
import NeoButton  from '@/components/NeoButton.vue'
import DataTable  from '@/components/DataTable.vue'
import RiskBadge  from '@/components/RiskBadge.vue'
import ModalDialog from '@/components/ModalDialog.vue'

const route = useRoute()
const hash  = computed(() => route.params.hash)

const loading     = ref(false)
const error       = ref(null)
const predLoading = ref(false)
const predError   = ref(null)
const predictions = ref([])
const metrics     = ref({})

const shapModal = ref(false)
const shapData  = ref({})

const latestRisk = computed(() => {
  if (metrics.value?.current_burnout_risk) return metrics.value.current_burnout_risk
  if (predictions.value.length) return predictions.value[0].predicted_risk
  return 'Low'
})

function truncateHash(h) {
  if (!h) return ''
  return h.length > 24 ? h.slice(0, 16) + '…' + h.slice(-8) : h
}

function pct(v) {
  if (v === undefined || v === null) return '0%'
  return `${Math.round(v * 100)}%`
}

function formatFeatureName(feat) {
  return feat.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function showShap(raw) {
  shapData.value = {}
  if (!raw) {
    shapModal.value = true
    return
  }
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
    shapData.value = (parsed && typeof parsed === 'object') ? parsed : {}
  } catch {
    shapData.value = {}
  }
  shapModal.value = true
}

const columns = [
  { key: 'week_start_date',   label: 'Evaluation Week', width: '130px' },
  { key: 'predicted_risk',    label: 'Risk Level',      width: '110px' },
  { key: 'probabilities',     label: 'Probability',     width: '170px' },
  { key: 'model_version',     label: 'Model Version',   width: '100px' },
  { key: 'shap_explanations', label: 'SHAP Factors',    width: '120px' },
]

onMounted(async () => {
  if (!hash.value) return

  loading.value = true
  try {
    const empData = await employeesApi.get(hash.value)
    if (empData) {
      metrics.value = empData
    }
  } catch (err) {
    error.value = err.message || 'Failed to load employee metrics'
  } finally {
    loading.value = false
  }

  predLoading.value = true
  try {
    const preds = await vaultApi.getPredictions(hash.value)
    if (Array.isArray(preds)) {
      predictions.value = preds.map(p => ({
        ...p,
        probabilities: {
          High: p.high_probability ?? 0,
          Medium: p.medium_probability ?? 0,
          Low: p.low_probability ?? 0
        }
      }))
    } else {
      predictions.value = []
    }
  } catch (err) {
    predError.value = err.message || 'Unable to retrieve prediction history'
    predictions.value = []
  } finally {
    predLoading.value = false
  }
})
</script>

<style scoped>
.employee-view { display: flex; flex-direction: column; gap: 1.5rem; }

.profile-card {}
.profile-header {
  display: flex; align-items: center; gap: 1.25rem; flex-wrap: wrap;
}
.profile-avatar {
  width: 52px; height: 52px;
  border-radius: 50%;
  background: var(--brand-navy);
  color: #fff;
  font-size: 1.5rem;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.profile-info { flex: 1; }
.profile-name { font-size: 1.05rem; font-weight: 700; color: var(--text-primary); font-family: monospace; }
.profile-meta { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 6px; }
.meta-tag {
  font-size: 0.725rem;
  padding: 0.2rem 0.55rem;
  border-radius: 12px;
  background: var(--bg-base);
  box-shadow: var(--shadow-inset-sm);
  color: var(--text-secondary);
}

.profile-actions {
  display: flex; align-items: center; gap: 12px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.metric-block {
  padding: 1.25rem;
  display: flex; flex-direction: column; gap: 6px;
}
.metric-block__label {
  font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;
}
.metric-block__val {
  font-size: 1.15rem; font-weight: 700; color: var(--text-primary);
}
.metric-block__sub {
  font-size: 0.75rem; color: var(--text-secondary);
}

.section-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 1rem;
}
.section-title { font-size: 0.95rem; font-weight: 700; color: var(--text-primary); }
.section-badge { font-size: 0.75rem; color: var(--text-muted); }

.prob-bars { display: flex; gap: 6px; font-size: 0.75rem; }
.prob-tag {
  padding: 2px 6px; border-radius: 4px; background: var(--bg-base); box-shadow: var(--shadow-inset-sm);
}

.shap-intro { font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.75rem; }
.shap-modal-list { display: flex; flex-direction: column; gap: 8px; max-height: 400px; overflow-y: auto; }
.shap-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.shap-row__feat { font-size: 0.8rem; color: var(--text-secondary); }
.shap-row__val  { font-size: 0.8rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.shap-row__val.pos { color: var(--risk-high); }
.shap-row__val.neg { color: var(--risk-low); }

.loading-state, .error-state {
  padding: 3rem; text-align: center; color: var(--text-muted);
  font-size: 0.875rem; display: flex; align-items: center; justify-content: center; gap: 12px;
}
.error-state { color: var(--risk-high); }
.spinner {
  width: 20px; height: 20px;
  border: 2px solid var(--border-color); border-top-color: var(--brand-navy);
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
