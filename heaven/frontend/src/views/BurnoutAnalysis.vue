<template>
  <div class="burnout-view">
    <NeoCard class="filter-card">
      <h2 class="section-title">Run Burnout Analysis</h2>
      <p class="section-sub">Submit employee metrics to generate a burnout risk prediction and SHAP explanation.</p>

      <form class="metrics-form" @submit.prevent="runPrediction">
        <div class="form-grid">
          <NeoInput v-model="form.employee_hash"    label="Employee Hash *"  id="emp_hash"    placeholder="sha256:…" />
          <NeoInput v-model="form.week_start_date"  label="Week Start Date *" id="week_date"  type="date" />
          <NeoInput v-model="form.avg_daily_work_hours" label="Avg Daily Work Hours" id="avg_hours" type="number" step="0.1" placeholder="8.0" />
          <NeoInput v-model="form.overtime_hours"   label="Overtime Hours"   id="ot_hours"  type="number" step="0.1" />
          <NeoInput v-model="form.leave_days_taken" label="Leave Days Taken" id="leave"     type="number" />
          <NeoInput v-model="form.late_entry_count" label="Late Entries"     id="late"      type="number" />
          <NeoInput v-model="form.missing_checkout_count" label="Missing Checkouts" id="miss_co" type="number" />
          <NeoInput v-model="form.weekend_work_days" label="Weekend Workdays" id="wknd"      type="number" />
          <NeoInput v-model="form.tenure_months"    label="Tenure (months)"  id="tenure"    type="number" />
          <NeoInput v-model="form.department"       label="Department"       id="dept"      placeholder="Engineering" />
        </div>

        <div class="form-actions">
          <label class="explain-toggle">
            <input v-model="includeExplanations" type="checkbox" />
            Include SHAP explanations
          </label>
          <NeoButton type="submit" variant="primary" :loading="loading">
            Run Prediction
          </NeoButton>
        </div>

        <p v-if="formError" class="form-error">{{ formError }}</p>
      </form>
    </NeoCard>

    <!-- Result Panel -->
    <Transition name="fade">
      <NeoCard v-if="result" class="result-card">
        <div class="result-header">
          <h3 class="result-title">Prediction Result</h3>
          <RiskBadge :risk="result.predicted_risk" />
        </div>

        <div class="prob-grid">
          <div v-for="(prob, label) in result.probabilities" :key="label" class="prob-item">
            <div class="prob-item__label">{{ label }}</div>
            <div class="prob-item__bar-wrap">
              <div class="prob-item__bar" :class="`prob-item__bar--${label.toLowerCase()}`" :style="{ width: pct(prob) }" />
            </div>
            <div class="prob-item__pct">{{ pct(prob) }}</div>
          </div>
        </div>

        <div v-if="result.explanation" class="shap-section">
          <h4 class="shap-title">SHAP Feature Importances</h4>
          <div class="shap-list">
            <div
              v-for="(val, feat) in sortedShap"
              :key="feat"
              class="shap-row"
            >
              <span class="shap-row__feat">{{ feat }}</span>
              <div class="shap-row__bar-wrap">
                <div
                  class="shap-row__bar"
                  :class="val >= 0 ? 'shap-row__bar--pos' : 'shap-row__bar--neg'"
                  :style="{ width: shapWidth(val) }"
                />
              </div>
              <span class="shap-row__val" :class="val >= 0 ? 'pos' : 'neg'">
                {{ val >= 0 ? '+' : '' }}{{ val.toFixed(3) }}
              </span>
            </div>
          </div>
        </div>

        <div class="result-meta">
          Model: <strong>{{ result.model_type }}</strong> · v{{ result.model_version }}
        </div>
      </NeoCard>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { predictionsApi } from '@/api/client'
import NeoCard   from '@/components/NeoCard.vue'
import NeoInput  from '@/components/NeoInput.vue'
import NeoButton from '@/components/NeoButton.vue'
import RiskBadge from '@/components/RiskBadge.vue'

const loading            = ref(false)
const formError          = ref(null)
const result             = ref(null)
const includeExplanations = ref(false)

const form = reactive({
  employee_hash:           '',
  week_start_date:         '',
  avg_daily_work_hours:    '',
  overtime_hours:          '',
  leave_days_taken:        '',
  late_entry_count:        '',
  missing_checkout_count:  '',
  weekend_work_days:       '',
  tenure_months:           '',
  department:              ''
})

function parseNum(v) { return v === '' || v === null ? null : Number(v) }

async function runPrediction() {
  if (!form.employee_hash || !form.week_start_date) {
    formError.value = 'Employee Hash and Week Start Date are required.'
    return
  }
  formError.value = null
  loading.value   = true
  result.value    = null

  const metrics = {
    employee_hash:          form.employee_hash.trim(),
    week_start_date:        form.week_start_date,
    avg_daily_work_hours:   parseNum(form.avg_daily_work_hours),
    overtime_hours:         parseNum(form.overtime_hours),
    leave_days_taken:       parseNum(form.leave_days_taken),
    late_entry_count:       parseNum(form.late_entry_count),
    missing_checkout_count: parseNum(form.missing_checkout_count),
    weekend_work_days:      parseNum(form.weekend_work_days),
    tenure_months:          parseNum(form.tenure_months),
    department:             form.department || null
  }

  try {
    result.value = await predictionsApi.predict(metrics, includeExplanations.value)
  } catch (err) {
    formError.value = err.message
  } finally {
    loading.value = false
  }
}

function pct(v) { return `${Math.round((v ?? 0) * 100)}%` }

const sortedShap = computed(() => {
  if (!result.value?.explanation) return {}
  return Object.fromEntries(
    Object.entries(result.value.explanation).sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
  )
})

const maxShap = computed(() => {
  if (!result.value?.explanation) return 1
  return Math.max(...Object.values(result.value.explanation).map(Math.abs), 0.001)
})

function shapWidth(val) {
  return `${Math.round((Math.abs(val) / maxShap.value) * 100)}%`
}
</script>

<style scoped>
.burnout-view { display: flex; flex-direction: column; gap: 1.5rem; }

.section-title { font-size: 1rem; font-weight: 700; color: var(--text-primary); margin-bottom: 4px; }
.section-sub   { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1.25rem; }

.metrics-form { display: flex; flex-direction: column; gap: 1.25rem; }

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}
@media (max-width: 768px) { .form-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 480px) { .form-grid { grid-template-columns: 1fr; } }

.form-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}
.explain-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--text-secondary);
  cursor: pointer;
}
.explain-toggle input { accent-color: var(--brand-navy); }

.form-error {
  padding: 0.65rem 1rem;
  background: var(--risk-high-bg);
  color: var(--risk-high);
  border: 1px solid var(--risk-high-border);
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
}

/* Result */
.result-card {}
.result-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 1.25rem;
}
.result-title { font-size: 1rem; font-weight: 700; color: var(--text-primary); }

.prob-grid { display: flex; flex-direction: column; gap: 10px; margin-bottom: 1.5rem; }
.prob-item { display: flex; align-items: center; gap: 12px; }
.prob-item__label { width: 70px; font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); }
.prob-item__bar-wrap { flex: 1; height: 10px; background: var(--bg-inset); border-radius: 5px; overflow: hidden; box-shadow: var(--shadow-inset-sm); }
.prob-item__bar { height: 100%; border-radius: 5px; transition: width 0.5s ease; }
.prob-item__bar--high   { background: var(--risk-high); }
.prob-item__bar--medium { background: var(--risk-medium); }
.prob-item__bar--low    { background: var(--risk-low); }
.prob-item__pct { width: 42px; text-align: right; font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); }

/* SHAP */
.shap-section { padding-top: 1.25rem; border-top: 1px solid var(--border-color); }
.shap-title { font-size: 0.875rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.875rem; }
.shap-list { display: flex; flex-direction: column; gap: 8px; }
.shap-row { display: flex; align-items: center; gap: 10px; }
.shap-row__feat { width: 200px; font-size: 0.75rem; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.shap-row__bar-wrap { flex: 1; height: 8px; background: var(--bg-inset); border-radius: 4px; overflow: hidden; }
.shap-row__bar { height: 100%; border-radius: 4px; transition: width 0.4s ease; }
.shap-row__bar--pos { background: var(--risk-high); }
.shap-row__bar--neg { background: var(--risk-low); }
.shap-row__val { width: 55px; text-align: right; font-size: 0.73rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.shap-row__val.pos { color: var(--risk-high); }
.shap-row__val.neg { color: var(--risk-low); }

.result-meta { margin-top: 1.25rem; font-size: 0.75rem; color: var(--text-muted); }

/* Transition */
.fade-enter-active, .fade-leave-active { transition: opacity 0.25s ease; }
.fade-enter-from, .fade-leave-to       { opacity: 0; }
</style>
