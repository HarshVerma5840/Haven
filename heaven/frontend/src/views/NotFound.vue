<template>
  <div class="not-found">
    <div class="not-found__code">404</div>
    <h1 class="not-found__title">Page not found</h1>
    <p class="not-found__sub">The page you're looking for doesn't exist or you don't have access.</p>
    <RouterLink to="/" class="not-found__link">← Go to Dashboard</RouterLink>
  </div>
</template>

<style scoped>
.not-found {
  min-height: 60vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  text-align: center;
  padding: 2rem;
}
.not-found__code {
  font-size: 5rem;
  font-weight: 800;
  color: var(--bg-inset);
  line-height: 1;
}
.not-found__title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
}
.not-found__sub {
  font-size: 0.875rem;
  color: var(--text-muted);
  max-width: 340px;
}
.not-found__link {
  margin-top: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--brand-accent);
}
.not-found__link:hover { text-decoration: underline; }
</style>
