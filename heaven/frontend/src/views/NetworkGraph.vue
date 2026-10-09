<template>
  <div class="network-view">
    <!-- Controls Card -->
    <NeoCard class="controls-card">
      <div class="section-header">
        <div>
          <h2 class="section-title">Organizational Network & Collaboration Graph</h2>
          <p class="section-sub">Analyze cross-department interaction density, team isolation, and burnout risk centrality.</p>
        </div>
        <div class="view-toggles">
          <NeoButton
            :variant="viewMode === 'graph' ? 'primary' : 'secondary'"
            size="sm"
            @click="viewMode = 'graph'"
          >
            🕸 Visual Graph
          </NeoButton>
          <NeoButton
            :variant="viewMode === 'table' ? 'primary' : 'secondary'"
            size="sm"
            @click="viewMode = 'table'"
          >
            📋 Centrality Table
          </NeoButton>
        </div>
      </div>

      <div class="filters-row">
        <select v-model="selectedDepartment" class="filter-select" @change="loadNetworkData">
          <option value="">All Departments</option>
          <option value="Engineering">Engineering</option>
          <option value="Sales">Sales</option>
          <option value="HR">HR</option>
          <option value="Finance">Finance</option>
        </select>
        <select v-model="graphType" class="filter-select" @change="loadNetworkData">
          <option value="collaboration">Collaboration (Projects & Reviews)</option>
          <option value="communication">Communication Frequency</option>
          <option value="timesheet">Cross-Functional Timesheets</option>
        </select>
        <input
          type="date"
          v-model="dateFilter"
          class="filter-select filter-date"
          title="Filter by evaluation date"
          @change="loadNetworkData"
        />
        <NeoButton variant="secondary" size="sm" :loading="loading" @click="loadNetworkData">
          ↻ Recompute Graph
        </NeoButton>
      </div>
    </NeoCard>

    <!-- Error State with Retry -->
    <NeoCard v-if="error" class="state-card error-card">
      <div class="state-content">
        <span class="state-icon">⚠</span>
        <div class="state-text">
          <h3 class="state-title">Failed to load collaboration network</h3>
          <p class="state-desc">{{ error }}</p>
        </div>
        <NeoButton variant="primary" size="sm" @click="loadNetworkData">
          Retry
        </NeoButton>
      </div>
    </NeoCard>

    <!-- Loading State -->
    <NeoCard v-else-if="loading" class="state-card">
      <div class="state-content">
        <div class="spinner" />
        <p class="state-desc">Computing organizational collaboration nodes from PostgreSQL…</p>
      </div>
    </NeoCard>

    <!-- Empty State -->
    <NeoCard v-else-if="!nodes.length" class="state-card empty-card">
      <div class="state-content">
        <span class="state-icon">🌐</span>
        <div class="state-text">
          <h3 class="state-title">No Collaboration Network Data</h3>
          <p class="state-desc">{{ emptyMessage || 'No behavioral data available. Ingest employee metrics from HRMS to populate the network graph.' }}</p>
        </div>
      </div>
    </NeoCard>

    <!-- Visual Graph Mode -->
    <NeoCard v-else-if="viewMode === 'graph'" class="graph-card">
      <div class="graph-header">
        <div class="legend">
          <span class="legend-item"><span class="dot high" /> High Burnout Risk</span>
          <span class="legend-item"><span class="dot medium" /> Medium Risk</span>
          <span class="legend-item"><span class="dot low" /> Low Risk</span>
          <span class="legend-item"><span class="edge-line" /> Collaboration Edge</span>
        </div>
        <div v-if="selectedNode" class="node-inspector">
          Selected: <strong>{{ truncateHash(selectedNode.id) }}</strong> | Centrality: <strong>{{ selectedNode.centrality }}</strong> | Dept: <strong>{{ selectedNode.department || selectedNode.dept }}</strong>
        </div>
      </div>

      <div class="svg-container">
        <svg viewBox="0 0 800 500" class="network-svg">
          <!-- Edges -->
          <line
            v-for="(edge, idx) in edges"
            :key="`edge-${idx}`"
            :x1="getNodeX(edge.source)"
            :y1="getNodeY(edge.source)"
            :x2="getNodeX(edge.target)"
            :y2="getNodeY(edge.target)"
            class="graph-edge"
            :stroke-width="edge.weight || 1.5"
          />

          <!-- Nodes -->
          <g
            v-for="node in nodes"
            :key="node.id"
            class="node-group"
            :class="{ 'node-group--selected': selectedNode && selectedNode.id === node.id }"
            @click="selectedNode = node"
            @dblclick="onNodeClick(node)"
          >
            <circle
              :cx="node.x"
              :cy="node.y"
              :r="14 + (node.centrality * 10)"
              :class="`node-circle node-circle--${(node.risk || 'low').toLowerCase()}`"
            />
            <text :x="node.x" :y="node.y + 4" class="node-label">
              {{ node.id.slice(0, 3) }}
            </text>
          </g>
        </svg>
      </div>
    </NeoCard>

    <!-- Accessible Centrality Table Mode (Fallback) -->
    <NeoCard v-else class="table-card">
      <DataTable
        :columns="tableColumns"
        :rows="nodes"
        :on-row-click="onNodeClick"
      >
        <template #cell-id="{ value }">
          <span class="hash-text font-mono">{{ truncateHash(value) }}</span>
        </template>
        <template #cell-department="{ value, row }">
          <span>{{ value || row.dept || '—' }}</span>
        </template>
        <template #cell-risk="{ value }">
          <RiskBadge :risk="value || 'Low'" />
        </template>
        <template #cell-centrality="{ value }">
          <div class="centrality-bar-wrap">
            <div class="centrality-bar" :style="{ width: `${Math.round(value * 100)}%` }" />
            <span>{{ value.toFixed(3) }}</span>
          </div>
        </template>
        <template #cell-actions="{ row }">
          <NeoButton variant="ghost" size="sm" @click.stop="onNodeClick(row)">
            View Profile →
          </NeoButton>
        </template>
      </DataTable>
    </NeoCard>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { analyticsApi } from '@/api/client'
import NeoCard from '@/components/NeoCard.vue'
import NeoButton from '@/components/NeoButton.vue'
import DataTable from '@/components/DataTable.vue'
import RiskBadge from '@/components/RiskBadge.vue'

const router = useRouter()
const viewMode = ref('graph')
const selectedDepartment = ref('')
const graphType = ref('collaboration')
const dateFilter = ref('')
const selectedNode = ref(null)
const loading = ref(false)
const error = ref(null)
const emptyMessage = ref('')

const tableColumns = [
  { key: 'id',          label: 'Employee Hash' },
  { key: 'department',  label: 'Department' },
  { key: 'risk',        label: 'Burnout Risk' },
  { key: 'centrality',  label: 'Betweenness Centrality' },
  { key: 'degree',      label: 'Connection Degree' },
  { key: 'actions',     label: '' },
]

const nodes = ref([])
const edges = ref([])

function getNodeX(id) {
  const n = nodes.value.find(n => n.id === id)
  return n?.x ?? 400
}

function getNodeY(id) {
  const n = nodes.value.find(n => n.id === id)
  return n?.y ?? 250
}

function truncateHash(h) {
  if (!h) return '—'
  return `${h.slice(0, 8)}…`
}

function onNodeClick(node) {
  const id = node.id || node.employee_hash
  if (id) {
    router.push({ name: 'employee', params: { hash: id } })
  }
}

async function loadNetworkData() {
  loading.value = true
  error.value = null
  emptyMessage.value = ''
  try {
    const res = await analyticsApi.network({
      department: selectedDepartment.value || undefined,
      graph_type: graphType.value || undefined,
      date: dateFilter.value || undefined
    })
    if (res && res.nodes) {
      nodes.value = res.nodes
      edges.value = res.edges || []
      emptyMessage.value = res.message || ''
    }
  } catch (err) {
    error.value = err.message || 'Unable to compute network graph'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadNetworkData()
})
</script>

<style scoped>
.network-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.controls-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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

.view-toggles {
  display: flex;
  gap: 8px;
}

.filters-row {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
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

.graph-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  font-size: 0.8rem;
}

.legend {
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.dot.high   { background: var(--risk-high); }
.dot.medium { background: var(--risk-medium); }
.dot.low    { background: var(--risk-low); }
.edge-line {
  display: inline-block;
  width: 16px;
  height: 2px;
  background: #cbd5e1;
}

.svg-container {
  width: 100%;
  height: 480px;
  background: var(--bg-base);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-inset);
  overflow: hidden;
}

.network-svg {
  width: 100%;
  height: 100%;
}

.graph-edge {
  stroke: #cbd5e1;
  stroke-linecap: round;
  transition: stroke var(--transition-fast);
}

.node-group {
  cursor: pointer;
  transition: transform var(--transition-fast);
}
.node-group:hover {
  transform: scale(1.15);
}
.node-group--selected circle {
  stroke: var(--brand-navy);
  stroke-width: 3px;
}

.node-circle--high   { fill: var(--risk-high); }
.node-circle--medium { fill: var(--risk-medium); }
.node-circle--low    { fill: var(--risk-low); }

.node-label {
  fill: #ffffff;
  font-size: 9px;
  font-weight: 700;
  text-anchor: middle;
  pointer-events: none;
}

.centrality-bar-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.centrality-bar {
  height: 6px;
  background: var(--brand-navy);
  border-radius: 3px;
  max-width: 80px;
}
</style>
