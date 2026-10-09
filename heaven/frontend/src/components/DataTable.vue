<template>
  <div class="data-table-wrap">
    <div v-if="loading" class="table-loader">
      <div class="table-loader__spinner" />
      <span>Loading…</span>
    </div>
    <div v-else-if="error" class="table-empty table-empty--error">
      <span>⚠ {{ error }}</span>
    </div>
    <div v-else-if="!rows.length" class="table-empty">
      <span>No records found.</span>
    </div>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th v-for="col in columns" :key="col.key" :style="{ width: col.width }">
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, i) in rows"
          :key="i"
          class="data-table__row"
          :class="{ 'data-table__row--clickable': !!onRowClick }"
          @click="onRowClick ? onRowClick(row) : undefined"
        >
          <td v-for="col in columns" :key="col.key">
            <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
              {{ row[col.key] ?? '—' }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({
  columns:    { type: Array,    required: true },
  rows:       { type: Array,    default: () => [] },
  loading:    { type: Boolean,  default: false },
  error:      { type: String,   default: null },
  onRowClick: { type: Function, default: null }
})
</script>

<style scoped>
.data-table-wrap {
  overflow-x: auto;
  border-radius: var(--radius-md);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.data-table thead th {
  padding: 0.75rem 1rem;
  text-align: left;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}
.data-table thead th:first-child { border-radius: var(--radius-sm) 0 0 0; }
.data-table thead th:last-child  { border-radius: 0 var(--radius-sm) 0 0; }

.data-table tbody td {
  padding: 0.85rem 1rem;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
  vertical-align: middle;
}

.data-table__row { transition: background var(--transition-fast); }
.data-table__row:hover  { background: var(--bg-surface); }
.data-table__row--clickable { cursor: pointer; }
.data-table__row:last-child td { border-bottom: none; }

.table-loader {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 2.5rem;
  color: var(--text-muted);
  font-size: 0.875rem;
}
.table-loader__spinner {
  width: 20px; height: 20px;
  border: 2px solid var(--border-color);
  border-top-color: var(--brand-navy);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.table-empty {
  padding: 2.5rem;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.875rem;
}
.table-empty--error { color: var(--risk-high); }
</style>
