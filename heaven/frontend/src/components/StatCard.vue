<template>
  <div class="stat-card">
    <div class="stat-card__label">{{ label }}</div>
    <div class="stat-card__value" :class="valueClass">{{ value }}</div>
    <div v-if="sub" class="stat-card__sub">{{ sub }}</div>
  </div>
</template>

<script setup>
defineProps({
  label:      { type: String, required: true },
  value:      { type: [String, Number], required: true },
  sub:        { type: String, default: null },
  valueClass: { type: String, default: '' }
})
</script>

<style scoped>
.stat-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-raised);
  padding: 1.25rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: box-shadow var(--transition-fast);
}
.stat-card:hover { box-shadow: var(--shadow-hover); }

.stat-card__label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.stat-card__value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}
.stat-card__sub {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* Risk color variants */
.stat-card__value.high   { color: var(--risk-high); }
.stat-card__value.medium { color: var(--risk-medium); }
.stat-card__value.low    { color: var(--risk-low); }
</style>
