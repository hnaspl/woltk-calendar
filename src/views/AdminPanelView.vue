<template>
  <AppShell>
    <div class="p-4 md:p-6 space-y-6">
      <h1 class="wow-heading text-2xl">Admin Panel</h1>

      <div v-if="!authStore.user?.is_admin" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">
        You do not have admin privileges.
      </div>

      <template v-else>
        <!-- Users table -->
        <WowCard>
          <div class="flex items-center justify-between mb-4">
            <h2 class="wow-heading text-base">All Users ({{ users.length }})</h2>
          </div>

          <div v-if="loading" class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
          <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>

          <div v-else class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-bg-tertiary border-b border-border-default">
                  <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">ID</th>
                  <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Username</th>
                  <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Email</th>
                  <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Status</th>
                  <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Admin</th>
                  <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Registered</th>
                  <th class="text-right px-4 py-2.5 text-xs text-text-muted uppercase">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-default">
                <tr v-for="u in users" :key="u.id" class="hover:bg-bg-tertiary/50 transition-colors">
                  <td class="px-4 py-2.5 text-text-muted">{{ u.id }}</td>
                  <td class="px-4 py-2.5 text-text-primary font-medium">{{ u.username }}</td>
                  <td class="px-4 py-2.5 text-text-muted">{{ u.email }}</td>
                  <td class="px-4 py-2.5">
                    <span
                      class="inline-block px-2 py-0.5 text-xs rounded-full font-medium"
                      :class="u.is_active ? 'bg-green-900/50 text-green-300 border border-green-600' : 'bg-red-900/50 text-red-300 border border-red-600'"
                    >
                      {{ u.is_active ? 'Active' : 'Blocked' }}
                    </span>
                  </td>
                  <td class="px-4 py-2.5">
                    <span v-if="u.is_admin" class="text-accent-gold text-xs font-bold">Admin</span>
                    <span v-else class="text-text-muted text-xs">—</span>
                  </td>
                  <td class="px-4 py-2.5 text-text-muted text-xs">{{ formatDate(u.created_at) }}</td>
                  <td class="px-4 py-2.5 text-right space-x-2">
                    <template v-if="u.id !== authStore.user.id">
                      <WowButton
                        v-if="u.is_active"
                        variant="secondary"
                        class="text-xs py-1 px-2"
                        @click="toggleBlock(u)"
                      >Block</WowButton>
                      <WowButton
                        v-else
                        variant="secondary"
                        class="text-xs py-1 px-2"
                        @click="toggleBlock(u)"
                      >Unblock</WowButton>
                      <WowButton variant="danger" class="text-xs py-1 px-2" @click="confirmDelete(u)">Delete</WowButton>
                    </template>
                    <span v-else class="text-text-muted text-xs italic">You</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </WowCard>

        <!-- Auto-Sync Settings -->
        <WowCard>
          <h2 class="wow-heading text-base mb-4">Warmane Character Auto-Sync</h2>
          <p class="text-text-muted text-sm mb-4">Automatically sync all active characters from the Warmane armory at a scheduled interval.</p>

          <div v-if="autosyncLoading" class="h-24 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
          <div v-else class="space-y-4 max-w-lg">
            <div class="flex items-center gap-4">
              <label class="text-sm text-text-primary">Auto-Sync Enabled</label>
              <button
                type="button"
                class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
                :class="autosyncForm.enabled ? 'bg-accent-gold' : 'bg-bg-tertiary border border-border-default'"
                @click="autosyncForm.enabled = !autosyncForm.enabled"
              >
                <span
                  class="inline-block h-4 w-4 rounded-full bg-white transition-transform"
                  :class="autosyncForm.enabled ? 'translate-x-6' : 'translate-x-1'"
                />
              </button>
            </div>

            <div>
              <label class="block text-xs text-text-muted mb-1">Sync Interval (minutes)</label>
              <select v-model.number="autosyncForm.interval_minutes" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
                <option :value="15">Every 15 minutes</option>
                <option :value="30">Every 30 minutes</option>
                <option :value="60">Every hour</option>
                <option :value="120">Every 2 hours</option>
                <option :value="360">Every 6 hours</option>
                <option :value="720">Every 12 hours</option>
                <option :value="1440">Every 24 hours</option>
              </select>
            </div>

            <div class="flex gap-3">
              <WowButton :loading="autosyncSaving" @click="saveAutosync">Save Settings</WowButton>
              <WowButton variant="secondary" :loading="syncing" @click="triggerManualSync">Sync Now</WowButton>
            </div>
          </div>
        </WowCard>
      </template>
    </div>

    <!-- Delete confirmation -->
    <WowModal v-model="showDeleteConfirm" title="Delete User" size="sm">
      <p class="text-text-muted">Permanently delete <strong class="text-text-primary">{{ deleteTarget?.username }}</strong>? This cannot be undone.</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showDeleteConfirm = false">Cancel</WowButton>
          <WowButton variant="danger" :loading="deleting" @click="doDelete">Delete</WowButton>
        </div>
      </template>
    </WowModal>
  </AppShell>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import * as adminApi from '@/api/admin'

const authStore = useAuthStore()
const uiStore = useUiStore()

const users = ref([])
const loading = ref(true)
const error = ref(null)
const showDeleteConfirm = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)

// Auto-sync state
const autosyncLoading = ref(true)
const autosyncSaving = ref(false)
const syncing = ref(false)
const autosyncForm = ref({ enabled: false, interval_minutes: 60 })

onMounted(async () => {
  if (!authStore.user?.is_admin) return
  loading.value = true
  try {
    users.value = await adminApi.getUsers()
  } catch (err) {
    error.value = err?.response?.data?.message ?? 'Failed to load users'
  } finally {
    loading.value = false
  }

  // Load auto-sync settings
  autosyncLoading.value = true
  try {
    const config = await adminApi.getAutosyncSettings()
    autosyncForm.value = { enabled: config.enabled ?? false, interval_minutes: config.interval_minutes ?? 60 }
  } catch {
    // ignore – defaults are fine
  } finally {
    autosyncLoading.value = false
  }
})

async function toggleBlock(user) {
  try {
    const updated = await adminApi.updateUser(user.id, { is_active: !user.is_active })
    const idx = users.value.findIndex(u => u.id === user.id)
    if (idx !== -1) users.value[idx] = updated
    uiStore.showToast(updated.is_active ? 'User unblocked' : 'User blocked', 'success')
  } catch {
    uiStore.showToast('Failed to update user', 'error')
  }
}

function confirmDelete(user) {
  deleteTarget.value = user
  showDeleteConfirm.value = true
}

async function doDelete() {
  deleting.value = true
  try {
    await adminApi.deleteUser(deleteTarget.value.id)
    users.value = users.value.filter(u => u.id !== deleteTarget.value.id)
    showDeleteConfirm.value = false
    uiStore.showToast('User deleted', 'success')
  } catch {
    uiStore.showToast('Failed to delete user', 'error')
  } finally {
    deleting.value = false
  }
}

async function saveAutosync() {
  autosyncSaving.value = true
  try {
    const config = await adminApi.updateAutosyncSettings(autosyncForm.value)
    autosyncForm.value = { enabled: config.enabled, interval_minutes: config.interval_minutes }
    uiStore.showToast('Auto-sync settings saved', 'success')
  } catch {
    uiStore.showToast('Failed to save auto-sync settings', 'error')
  } finally {
    autosyncSaving.value = false
  }
}

async function triggerManualSync() {
  syncing.value = true
  try {
    await adminApi.triggerSync()
    uiStore.showToast('Character sync completed', 'success')
  } catch {
    uiStore.showToast('Sync failed', 'error')
  } finally {
    syncing.value = false
  }
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}
</script>
