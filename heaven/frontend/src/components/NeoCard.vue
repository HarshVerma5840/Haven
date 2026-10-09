<template>
  <div class="neo-card" :class="{ 'neo-card--inset': inset }">
    <slot />
  </div>
</template>

<script setup>
defineProps({
  inset: { type: Boolean, default: false }
})
</script>

<style scoped>
.neo-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-raised);
  padding: 1.5rem;
  transition: box-shadow var(--transition-fast);
}
.neo-card--inset {
  background: var(--bg-base);
  box-shadow: var(--shadow-inset);
}
</style>
