<template>
  <div class="auth-layout">
    <div class="auth-card">
      <router-view />
    </div>
  </div>
</template>

<style scoped>
.auth-layout {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-base);
}

.auth-card {
  width: 100%;
  max-width: 440px;
  padding: 2rem;
}
</style>
