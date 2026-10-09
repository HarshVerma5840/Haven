<template>
  <div class="login-page">
    <!-- Brand header -->
    <div class="login-brand">
      <span class="login-brand__icon">🛡</span>
      <span class="login-brand__name">Haven</span>
    </div>
    <p class="login-tagline">AI-powered Employee Wellbeing Suite</p>

    <NeoCard class="login-card">
      <h2 class="login-card__title">Sign in</h2>

      <form class="login-form" @submit.prevent="handleLogin">
        <NeoInput
          id="username"
          v-model="form.username"
          label="Username"
          type="text"
          autocomplete="username"
          placeholder="your_username"
          :error="errors.username"
        />
        <NeoInput
          id="password"
          v-model="form.password"
          label="Password"
          type="password"
          autocomplete="current-password"
          placeholder="••••••••"
          :error="errors.password"
        />

        <p v-if="loginError" class="login-error">{{ loginError }}</p>

        <NeoButton type="submit" variant="primary" size="lg" :loading="loading" style="width:100%">
          Sign in
        </NeoButton>
      </form>
    </NeoCard>

    <p class="login-footer">
      Haven stores your session token in browser memory only.<br>
      No credentials are stored in source code.
    </p>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import NeoCard   from '@/components/NeoCard.vue'
import NeoInput  from '@/components/NeoInput.vue'
import NeoButton from '@/components/NeoButton.vue'

const auth   = useAuthStore()
const router = useRouter()
const route  = useRoute()

const loading    = ref(false)
const loginError = ref(null)

const form = reactive({ username: '', password: '' })
const errors = reactive({ username: null, password: null })

onMounted(() => {
  if (auth.isAuthenticated) {
    const redirect = route.query.redirect ?? '/dashboard'
    router.replace(redirect)
  }
})

function validate() {
  errors.username = form.username.trim() ? null : 'Username is required'
  errors.password = form.password        ? null : 'Password is required'
  return !errors.username && !errors.password
}

async function handleLogin() {
  loginError.value = null
  if (!validate()) return

  loading.value = true
  try {
    await auth.login(form.username.trim(), form.password)
    const redirect = route.query.redirect ?? '/dashboard'
    await router.push(redirect)
  } catch (err) {
    loginError.value = err.message ?? 'Login failed. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.login-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 0.25rem;
}
.login-brand__icon { font-size: 2rem; }
.login-brand__name {
  font-size: 2rem;
  font-weight: 800;
  color: var(--brand-navy);
  letter-spacing: -0.03em;
}

.login-tagline {
  font-size: 0.875rem;
  color: var(--text-muted);
  text-align: center;
}

.login-card { width: 100%; }
.login-card__title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 1.5rem;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.login-error {
  padding: 0.65rem 1rem;
  background: var(--risk-high-bg);
  color: var(--risk-high);
  border: 1px solid var(--risk-high-border);
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
}

.login-footer {
  text-align: center;
  font-size: 0.72rem;
  color: var(--text-muted);
  line-height: 1.8;
}
</style>
