<template>
  <div class="directory-view">
    <!-- Header & Filter Card -->
    <NeoCard class="directory-header-card">
      <div class="section-header">
        <div>
          <h2 class="section-title">HR Employee Risk Directory</h2>
          <p class="section-sub">Behavioral workforce directory with automated burnout risk assessments. Identity-vault protected.</p>
        </div>
        <NeoButton variant="secondary" size="sm" :loading="loading" @click="fetchDirectory">
          ↻ Refresh
        </NeoButton>
      </div>

      <div class="filters-grid">
        <NeoInput
          v-model="searchQuery"
          placeholder="Search by Employee Hash, Department, or Designation…"
          id="search-input"
          @keyup.enter="applyFilters"
        />
        <select v-model="selectedDepartment" class="filter-select" @change="applyFilters">
          <option value="">All Departments</option>
          <option value="Engineering">Engineering</option>
          <option value="Sales">Sales</option>
          <option value="HR">HR</option>
          <option value="Finance">Finance</option>
          <option value="Customer Support">Customer Support</option>
          <option value="Operations">Operations</option>
        </select>
        <select v-model="selectedRisk" class="filter-select" @change="applyFilters">
          <option value="">All Risk Levels</option>
          <option value="High">High Risk</option>
          <option value="Medium">Medium Risk</option>
          <option value="Low">Low Risk</option>
        </select>
        <select v-model="sortBy" class="filter-select" @change="applyFilters">
          <option value="risk_desc">Sort: Risk (High → Low)</option>
          <option value="risk_asc">Sort: Risk (Low → High)</option>
          <option value="date_desc">Sort: Evaluation Date (Newest)</option>
          <option value="date_asc">Sort: Evaluation Date (Oldest)</option>
          <option value="completeness_desc">Sort: Completeness (High → Low)</option>
        </select>
      </div>
    </NeoCard>

    <!-- Error State with Retry -->
    <NeoCard v-if="error" class="state-card error-card">
      <div class="state-content">
        <span class="state-icon">⚠</span>
        <div class="state-text">
          <h3 class="state-title">Failed to load employee directory</h3>
          <p class="state-desc">{{ error }}</p>
        </div>
        <NeoButton variant="primary" size="sm" @click="fetchDirectory">
          Retry
        </NeoButton>
      </div>
    </NeoCard>

    <!-- Loading State -->
    <NeoCard v-else-if="loading" class="state-card">
      <div class="state-content">
        <div class="spinner" />
        <p class="state-desc">Loading behavioral employee directory from PostgreSQL…</p>
      </div>
    </NeoCard>

    <!-- Empty State -->
    <NeoCard v-else-if="!items.length" class="state-card empty-card">
      <div class="state-content">
        <span class="state-icon">🔍</span>
        <div class="state-text">
          <h3 class="state-title">No employees found</h3>
          <p class="state-desc">No behavioral records match your current filter and search criteria.</p>
        </div>
        <NeoButton variant="secondary" size="sm" @click="resetFilters">
          Reset Filters
        </NeoButton>
      </div>
    </NeoCard>

    <!-- Data Table -->
    <NeoCard v-else class="table-card">
      <DataTable
        :columns="columns"
        :rows="items"
        :on-row-click="openEmployee"
      >
        <template #cell-employee_hash="{ value }">
          <div class="emp-hash-cell">
            <span class="hash-tag">#</span>
            <span class="hash-text" :title="value">{{ truncateHash(value) }}</span>
          </div>
        </template>

        <template #cell-department="{ value }">
          <span class="dept-text">{{ value || '—' }}</span>
        </template>

        <template #cell-designation="{ value }">
          <span class="designation-text">{{ value || '—' }}</span>
        </template>

        <template #cell-current_burnout_risk="{ value }">
          <RiskBadge :risk="value" />
        </template>

        <template #cell-prediction_date="{ value }">
          <span class="date-text">{{ formatDate(value) }}</span>
        </template>

        <template #cell-model_version="{ value }">
          <code class="model-badge">{{ value || 'v1.2.0-prod' }}</code>
        </template>

        <template #cell-data_completeness="{ value }">
          <span class="completeness-badge" :class="value >= 90 ? 'good' : 'warning'">
            {{ Math.round(value) }}%
          </span>
        </template>

        <template #cell-actions="{ row }">
          <NeoButton variant="ghost" size="sm" @click.stop="openEmployee(row)">
            View Profile →
          </NeoButton>
        </template>
      </DataTable>

      <!-- Pagination Footer -->
      <div class="pagination-footer">
        <span class="pagination-info">
          Showing page <strong>{{ page }}</strong> of <strong>{{ totalPages }}</strong> ({{ totalItems }} total records)
        </span>
        <div class="pagination-actions">
          <NeoButton
            variant="secondary"
            size="sm"
            :disabled="page <= 1"
            @click="changePage(page - 1)"
          >
            ← Previous
          </NeoButton>
          <NeoButton
            variant="secondary"
            size="sm"
            :disabled="page >= totalPages"
            @click="changePage(page + 1)"
          >
            Next →
          </NeoButton>
        </div>
      </div>
    </NeoCard>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { employeesApi } from '@/api/client'
import NeoCard from '@/components/NeoCard.vue'
import NeoButton from '@/components/NeoButton.vue'
import NeoInput from '@/components/NeoInput.vue'
import DataTable from '@/components/DataTable.vue'
import RiskBadge from '@/components/RiskBadge.vue'

const router = useRouter()

const loading = ref(false)
const error = ref(null)
const items = ref([])
const totalItems = ref(0)
const totalPages = ref(1)
const page = ref(1)
const pageSize = ref(20)

const searchQuery = ref('')
const selectedDepartment = ref('')
const selectedRisk = ref('')
const sortBy = ref('risk_desc')

const columns = [
  { key: 'employee_hash',        label: 'Employee Identifier' },
  { key: 'department',           label: 'Department' },
  { key: 'designation',          label: 'Designation' },
  { key: 'current_burnout_risk', label: 'Burnout Risk' },
  { key: 'prediction_date',      label: 'Prediction Date' },
  { key: 'model_version',        label: 'Model Version' },
  { key: 'data_completeness',    label: 'Completeness' },
  { key: 'actions',              label: '' },
]

async function fetchDirectory() {
  loading.value = true
  error.value = null
  try {
    const res = await employeesApi.directory({
      search: searchQuery.value.trim() || undefined,
      department: selectedDepartment.value || undefined,
      risk: selectedRisk.value || undefined,
      sort_by: sortBy.value,
      page: page.value,
      page_size: pageSize.value
    })
    items.value = res.items || []
    totalItems.value = res.total || 0
    totalPages.value = res.pages || 1
    page.value = res.page || 1
  } catch (err) {
    error.value = err.message || 'Unable to retrieve employee directory'
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  fetchDirectory()
}

function resetFilters() {
  searchQuery.value = ''
  selectedDepartment.value = ''
  selectedRisk.value = ''
  sortBy.value = 'risk_desc'
  page.value = 1
  fetchDirectory()
}

function changePage(newPage) {
  if (newPage >= 1 && newPage <= totalPages.value) {
    page.value = newPage
    fetchDirectory()
  }
}

function truncateHash(h) {
  if (!h) return '—'
  return h.length > 20 ? `${h.slice(0, 10)}…${h.slice(-6)}` : h
}

function formatDate(d) {
  if (!d) return '—'
  return d
}

function openEmployee(row) {
  if (row && row.employee_hash) {
    router.push({ name: 'employee', params: { hash: row.employee_hash } })
  }
}

onMounted(() => {
  fetchDirectory()
})
</script>

<style scoped>
.directory-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.directory-header-card {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
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
  margin-bottom: 4px;
}
.section-sub {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.filters-grid {
  display: grid;
  grid-template-columns: 2fr 1.2fr 1fr 1.5fr;
  gap: 1rem;
}

.filter-select {
  padding: 0.65rem 0.9rem;
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-inset-sm);
  color: var(--text-primary);
  font-size: 0.825rem;
  outline: none;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.filter-select:focus {
  border-color: var(--brand-navy);
}

.state-card {
  padding: 3rem 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.state-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  max-width: 480px;
}
.state-icon {
  font-size: 2.2rem;
}
.state-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}
.state-desc {
  font-size: 0.85rem;
  color: var(--text-muted);
}
.error-card {
  border-left: 4px solid var(--risk-high);
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--border-color);
  border-top-color: var(--brand-navy);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.emp-hash-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: monospace;
  font-size: 0.8rem;
}
.hash-tag {
  color: var(--brand-navy);
  font-weight: 700;
}
.hash-text {
  color: var(--text-primary);
}

.dept-text {
  font-size: 0.825rem;
  font-weight: 600;
  color: var(--text-primary);
}
.designation-text {
  font-size: 0.8rem;
  color: var(--text-secondary);
}
.date-text {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.model-badge {
  font-size: 0.75rem;
  padding: 2px 6px;
  background: var(--bg-base);
  box-shadow: var(--shadow-inset-sm);
  border-radius: 4px;
  color: var(--text-secondary);
}

.completeness-badge {
  display: inline-block;
  padding: 0.2rem 0.55rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}
.completeness-badge.good {
  background: var(--risk-low-bg);
  color: var(--risk-low);
}
.completeness-badge.warning {
  background: var(--risk-medium-bg);
  color: var(--risk-medium);
}

.pagination-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
  font-size: 0.8rem;
  color: var(--text-muted);
  flex-wrap: wrap;
  gap: 1rem;
}
.pagination-actions {
  display: flex;
  gap: 8px;
}

@media (max-width: 900px) {
  .filters-grid {
    grid-template-columns: 1fr;
  }
}
</style>
