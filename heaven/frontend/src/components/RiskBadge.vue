<template>
  <span class="risk-badge" :class="`risk-badge--${risk.toLowerCase()}`">
    {{ risk }}
  </span>
</template>

<script setup>
defineProps({
  risk: { type: String, required: true }
})
</script>

<style scoped>
.risk-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  border: 1px solid transparent;
}
.risk-badge--high {
  background: var(--risk-high-bg);
  color: var(--risk-high);
  border-color: var(--risk-high-border);
}
.risk-badge--medium {
  background: var(--risk-medium-bg);
  color: var(--risk-medium);
  border-color: var(--risk-medium-border);
}
.risk-badge--low {
  background: var(--risk-low-bg);
  color: var(--risk-low);
  border-color: var(--risk-low-border);
}
</style>
