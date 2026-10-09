<template>
  <button
    class="neo-btn"
    :class="[`neo-btn--${variant}`, `neo-btn--${size}`, { 'neo-btn--loading': loading }]"
    :disabled="disabled || loading"
    v-bind="$attrs"
  >
    <span v-if="loading" class="spinner" />
    <slot v-else />
  </button>
</template>

<script setup>
defineProps({
  variant:  { type: String, default: 'primary' }, // primary | secondary | danger | ghost
  size:     { type: String, default: 'md' },       // sm | md | lg
  loading:  { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})
</script>

<style scoped>
.neo-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: var(--radius-sm);
  font-weight: 600;
  cursor: pointer;
  transition: box-shadow var(--transition-fast), transform var(--transition-fast), background var(--transition-fast);
  border: none;
  font-family: inherit;
  white-space: nowrap;
}
.neo-btn:active { transform: translateY(1px); }
.neo-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

/* Sizes */
.neo-btn--sm { padding: 0.4rem 0.9rem; font-size: 0.8rem; }
.neo-btn--md { padding: 0.55rem 1.25rem; font-size: 0.875rem; }
.neo-btn--lg { padding: 0.75rem 1.75rem; font-size: 1rem; }

/* Variants */
.neo-btn--primary {
  background: var(--brand-navy);
  color: #fff;
  box-shadow: var(--shadow-raised-sm);
}
.neo-btn--primary:hover:not(:disabled) {
  background: var(--brand-navy-mid);
  box-shadow: var(--shadow-hover);
}

.neo-btn--secondary {
  background: var(--bg-card);
  color: var(--text-primary);
  box-shadow: var(--shadow-raised-sm);
}
.neo-btn--secondary:hover:not(:disabled) {
  box-shadow: var(--shadow-hover);
}

.neo-btn--danger {
  background: var(--risk-high);
  color: #fff;
  box-shadow: var(--shadow-raised-sm);
}
.neo-btn--danger:hover:not(:disabled) {
  opacity: 0.9;
  box-shadow: var(--shadow-hover);
}

.neo-btn--ghost {
  background: transparent;
  color: var(--text-secondary);
  box-shadow: none;
}
.neo-btn--ghost:hover:not(:disabled) {
  background: var(--bg-base);
  color: var(--text-primary);
}

/* Spinner */
.spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
