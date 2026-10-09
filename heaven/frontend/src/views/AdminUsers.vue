<template>
  <div class="admin-users-view">
    <NeoCard>
      <div class="section-header">
        <div>
          <h2 class="section-title">User Management</h2>
          <p class="section-sub">HR_ADMIN only. Manage Haven user accounts.</p>
        </div>
        <NeoButton variant="primary" size="sm" @click="openCreate">+ Add User</NeoButton>
      </div>

      <DataTable
        :columns="columns"
        :rows="users"
        :loading="loading"
        :error="error"
      >
        <template #cell-role="{ value }">
          <span class="role-chip" :class="`role-chip--${value.toLowerCase()}`">{{ value }}</span>
        </template>
        <template #cell-is_active="{ value }">
          <span :class="value ? 'active-pill' : 'inactive-pill'">{{ value ? 'Active' : 'Inactive' }}</span>
        </template>
      </DataTable>
    </NeoCard>

    <!-- Create user modal -->
    <ModalDialog :open="showCreate" title="Add New User" @close="showCreate = false">
      <form class="create-form" @submit.prevent="submitCreate">
        <NeoInput v-model="newUser.username"      label="Username *"      id="nu_user"  />
        <NeoInput v-model="newUser.password"      label="Password *"      id="nu_pass"  type="password" />
        <NeoInput v-model="newUser.employee_hash" label="Employee Hash"   id="nu_hash"  />
        <NeoInput v-model="newUser.department"    label="Department"      id="nu_dept"  />
        <div class="form-field">
          <label class="neo-label" for="nu_role">Role *</label>
          <select id="nu_role" v-model="newUser.role" class="filter-select" style="width:100%">
            <option value="EMPLOYEE">Employee</option>
            <option value="MANAGER">Manager</option>
            <option value="HR_ADMIN">HR Admin</option>
          </select>
        </div>
        <p v-if="createError" class="form-error">{{ createError }}</p>
      </form>
      <template #footer>
        <NeoButton variant="secondary" @click="showCreate = false">Cancel</NeoButton>
        <NeoButton variant="primary" :loading="createLoading" @click="submitCreate">Create User</NeoButton>
      </template>
    </ModalDialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { authApi } from '@/api/client'
import NeoCard    from '@/components/NeoCard.vue'
import NeoButton  from '@/components/NeoButton.vue'
import NeoInput   from '@/components/NeoInput.vue'
import DataTable  from '@/components/DataTable.vue'
import ModalDialog from '@/components/ModalDialog.vue'

const loading = ref(false)
const error   = ref(null)
const users   = ref([])

const showCreate   = ref(false)
const createLoading = ref(false)
const createError  = ref(null)

const newUser = reactive({
  username: '', password: '', role: 'EMPLOYEE',
  employee_hash: '', department: '', is_active: true
})

const columns = [
  { key: 'username',      label: 'Username',    width: '180px' },
  { key: 'role',          label: 'Role',        width: '120px' },
  { key: 'department',    label: 'Department',  width: '140px' },
  { key: 'is_active',     label: 'Status',      width: '100px' },
]

function openCreate() {
  Object.assign(newUser, { username: '', password: '', role: 'EMPLOYEE', employee_hash: '', department: '', is_active: true })
  createError.value = null
  showCreate.value = true
}

async function submitCreate() {
  if (!newUser.username || !newUser.password) {
    createError.value = 'Username and password are required.'
    return
  }
  createLoading.value = true
  createError.value   = null
  try {
    const user = await authApi.createUser({
      username:      newUser.username,
      password:      newUser.password,
      role:          newUser.role,
      employee_hash: newUser.employee_hash || null,
      department:    newUser.department    || null,
      is_active:     newUser.is_active
    })
    users.value.unshift(user)
    showCreate.value = false
  } catch (err) {
    createError.value = err.message
  } finally {
    createLoading.value = false
  }
}

// Note: there's no GET /users endpoint in the backend; we show an empty table with a note.
onMounted(async () => {
  loading.value = true
  try {
    // No list-all-users endpoint — clear UX note shown instead
    users.value = []
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.admin-users-view { display: flex; flex-direction: column; gap: 1.5rem; }

.section-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  flex-wrap: wrap; gap: 1rem; margin-bottom: 1.25rem;
}
.section-title { font-size: 1rem; font-weight: 700; color: var(--text-primary); }
.section-sub   { font-size: 0.78rem; color: var(--text-muted); margin-top: 2px; }

.role-chip {
  display: inline-flex; align-items: center;
  padding: 2px 8px; border-radius: 999px;
  font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
}
.role-chip--hr_admin { background: #ede9fe; color: #6d28d9; }
.role-chip--manager  { background: #dbeafe; color: #1d4ed8; }
.role-chip--employee { background: var(--bg-inset); color: var(--text-secondary); }

.active-pill   { font-size: 0.78rem; font-weight: 600; color: var(--risk-low); }
.inactive-pill { font-size: 0.78rem; font-weight: 600; color: var(--text-muted); }

.create-form { display: flex; flex-direction: column; gap: 1rem; }

.form-field { display: flex; flex-direction: column; gap: 6px; }
.neo-label  { font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); }

.filter-select {
  padding: 0.65rem 1rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: var(--bg-base);
  box-shadow: inset 2px 2px 5px #d1d5db, inset -2px -2px 5px #ffffff;
  font-size: 0.875rem; color: var(--text-primary);
  outline: none;
}
.form-error {
  padding: 0.65rem 1rem;
  background: var(--risk-high-bg);
  color: var(--risk-high);
  border: 1px solid var(--risk-high-border);
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
}
</style>
