<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="modal-overlay" @click.self="$emit('close')">
        <div class="modal-box" :style="{ maxWidth: width }">
          <div class="modal-header">
            <h3 class="modal-title">{{ title }}</h3>
            <button class="modal-close" @click="$emit('close')">✕</button>
          </div>
          <div class="modal-body">
            <slot />
          </div>
          <div v-if="$slots.footer" class="modal-footer">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
defineProps({
  open:  { type: Boolean, required: true },
  title: { type: String,  required: true },
  width: { type: String,  default: '480px' }
})
defineEmits(['close'])
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(26, 32, 53, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 500;
  padding: 1rem;
}

.modal-box {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: 0 24px 60px rgba(0,0,0,0.18);
  width: 100%;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
}
.modal-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
}
.modal-close {
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 0.8rem;
  transition: background var(--transition-fast), color var(--transition-fast);
}
.modal-close:hover { background: var(--bg-base); color: var(--text-primary); }

.modal-body  { padding: 1.5rem; }
.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* Transition */
.modal-enter-active, .modal-leave-active { transition: opacity var(--transition-fast); }
.modal-enter-from,  .modal-leave-to      { opacity: 0; }
.modal-enter-active .modal-box,
.modal-leave-active  .modal-box { transition: transform var(--transition-fast); }
.modal-enter-from .modal-box,
.modal-leave-to   .modal-box   { transform: scale(0.95); }
</style>
