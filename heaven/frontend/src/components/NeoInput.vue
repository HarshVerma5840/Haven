<template>
  <div class="neo-input-wrap" :class="{ 'neo-input-wrap--error': error }">
    <label v-if="label" :for="id" class="neo-label">{{ label }}</label>
    <input
      :id="id"
      class="neo-input"
      v-bind="$attrs"
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <span v-if="error" class="neo-input-error">{{ error }}</span>
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: String, default: '' },
  label:      { type: String, default: null },
  id:         { type: String, default: null },
  error:      { type: String, default: null }
})
defineEmits(['update:modelValue'])
</script>

<style scoped>
.neo-input-wrap { display: flex; flex-direction: column; gap: 6px; }
.neo-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
}
.neo-input {
  width: 100%;
  padding: 0.65rem 1rem;
  background: var(--bg-base);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-inset-sm);
  color: var(--text-primary);
  font-size: 0.875rem;
  transition: box-shadow var(--transition-fast), border-color var(--transition-fast);
  outline: none;
}
.neo-input:focus {
  border-color: var(--brand-accent);
  box-shadow: var(--shadow-inset-sm), 0 0 0 3px rgba(37,99,235,0.1);
}
.neo-input-wrap--error .neo-input {
  border-color: var(--risk-high);
  box-shadow: var(--shadow-inset-sm), 0 0 0 3px rgba(220,38,38,0.08);
}
.neo-input-error {
  font-size: 0.75rem;
  color: var(--risk-high);
}
</style>
