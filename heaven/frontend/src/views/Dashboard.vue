<template>
  <div class="dashboard-view">
    <!-- Top Info Bar -->
    <div class="meta-strip">
      <div class="meta-strip__item">
        <span class="meta-label">Model Version:</span>
        <span class="meta-value">{{ modelVersion || '—' }}</span>
      </div>
      <div class="meta-strip__item">
        <span class="meta-label">Data Completeness:</span>
        <span class="meta-value text-success">{{ avgCompleteness }}</span>
      </div>
      <div class="meta-strip__item">
        <span class="meta-label">Last Ingestion:</span>
        <span class="meta-value">{{ lastRefreshTime }}</span>
      </div>
    </div>

    <!-- KPI Row -->
    <div class="kpi-grid">
      <StatCard label="Total Employees" :value="kpis.total"      sub="evaluated active records" />
      <StatCard label="High Risk"        :value="kpis.high"       value-class="high"   sub="immediate intervention" />
      <StatCard label="Medium Risk"      :value="kpis.medium"     value-class="medium" sub="monitoring recommended" />
      <StatCard label="Low Risk"         :value="kpis.low"        value-class="low"    sub="healthy baseline" />
    </div>

    <!-- Filters + Table -->
    <NeoCard class="table-section">
      <div class="section-header">
        <h2 class="section-title">Department Overview</h2>
        <div class="filter-row">
          <select v-model="filters.department" class="filter-select">
            <option value="">All Departments</option>
            <option v-for="d in departments" :key="d" :value="d">{{ d }}</option>
          </select>
          <select v-model="filters.risk" class="filter-select">
            <option value="">All Risk Levels</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
          <NeoButton variant="secondary" size="sm" @click="loadData">Refresh</NeoButton>
        </div>
      </div>

      <DataTable
        :columns="columns"
        :rows="filteredRows"
        :loading="loading"
        :error="error"
        :on-row-click="openEmployee"
      >
        <template #cell-current_burnout_risk="{ value }">
          <RiskBadge :risk="value" />
        </template>
      </DataTable>

      <p v-if="!loading && !error && rows.length === 0" class="empty-msg">
        No employee records found. Ingest metrics from HRMS to populate the dashboard.
      </p>
    </NeoCard>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { employeesApi } from '@/api/client'
import StatCard  from '@/components/StatCard.vue'
import NeoCard   from '@/components/NeoCard.vue'
import NeoButton from '@/components/NeoButton.vue'
import DataTable from '@/components/DataTable.vue'
import RiskBadge from '@/components/RiskBadge.vue'

const router  = useRouter()
const loading = ref(false)
const error   = ref(null)
const rows    = ref([])
const modelVersion     = ref(null)
const avgCompleteness  = ref('—')
const lastRefreshTime  = ref('—')

const filters = reactive({ department: '', risk: '' })

const departments = computed(() => {
  const depts = new Set(rows.value.map(r => r.department).filter(Boolean))
  return [...depts].sort()
})

const kpis = computed(() => {
  const total  = rows.value.length
  const high   = rows.value.filter(r => r.current_burnout_risk === 'High').length
  const medium = rows.value.filter(r => r.current_burnout_risk === 'Medium').length
  const low    = rows.value.filter(r => r.current_burnout_risk === 'Low').length
  return { total, high, medium, low }
})

const filteredRows = computed(() =>
  rows.value.filter(r => {
    if (filters.department && r.department !== filters.department) return false
    if (filters.risk       && r.current_burnout_risk !== filters.risk) return false
    return true
  })
)

const columns = [
  { key: 'employee_hash',        label: 'Employee Hash',  width: '200px' },
  { key: 'department',           label: 'Department',     width: '140px' },
  { key: 'current_burnout_risk', label: 'Risk Level',     width: '120px' },
  { key: 'data_completeness',    label: 'Completeness',   width: '120px' },
  { key: 'prediction_date',      label: 'Prediction Date', width: '120px' },
  { key: 'model_version',        label: 'Model',          width: '100px' },
]

function openEmployee(row) {
  if (row.employee_hash) {
    router.push({ name: 'employee', params: { hash: row.employee_hash } })
  }
}

async function loadData() {
  loading.value = true
  error.value   = null
  try {
    const result = await employeesApi.directory({
      page_size: 100,
      sort_by: 'risk_desc'
    })
    rows.value = result?.items ?? []

    // Derive meta from actual data
    if (rows.value.length > 0) {
      const versions = rows.value.map(r => r.model_version).filter(Boolean)
      modelVersion.value = versions.length > 0 ? versions[0] : null

      const completeness = rows.value.map(r => r.data_completeness).filter(v => v != null)
      if (completeness.length > 0) {
        const avg = completeness.reduce((a, b) => a + b, 0) / completeness.length
        avgCompleteness.value = `${avg.toFixed(1)}% avg`
      } else {
        avgCompleteness.value = '—'
      }

      const dates = rows.value.map(r => r.prediction_date).filter(Boolean).sort().reverse()
      lastRefreshTime.value = dates.length > 0 ? dates[0] : '—'
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.dashboard-view { display: flex; flex-direction: column; gap: 1.5rem; }

.meta-strip {
  display: flex;
  gap: 1.5rem;
  padding: 0.75rem 1.25rem;
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  box-shadow: var(--shadow-inset-sm);
  font-size: 0.8rem;
  flex-wrap: wrap;
}
.meta-strip__item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.meta-label {
  color: var(--text-muted);
  font-weight: 500;
}
.meta-value {
  color: var(--text-primary);
  font-weight: 600;
}
.text-success { color: var(--risk-low); }

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}
@media (max-width: 900px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 500px) { .kpi-grid { grid-template-columns: 1fr; } }

.table-section {}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}
.section-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
}
.filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.filter-select {
  padding: 0.45rem 0.85rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: var(--bg-base);
  box-shadow: var(--shadow-inset-sm);
  font-size: 0.8rem;
  color: var(--text-primary);
  cursor: pointer;
  outline: none;
}
.filter-select:focus { border-color: var(--brand-accent); }

/* Probability bars */
.prob-bars {
  display: flex;
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  gap: 1px;
  width: 120px;
}
.prob-bar { height: 100%; min-width: 2px; border-radius: 2px; }
</style>
