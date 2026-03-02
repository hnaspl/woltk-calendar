<template>
  <div class="space-y-6">
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
                <template v-if="u.id !== authStore.user.id && u.id !== 1">
                  <WowButton
                    v-if="!u.is_admin"
                    variant="secondary"
                    class="text-xs py-1 px-2"
                    @click="toggleAdmin(u)"
                  >Promote Admin</WowButton>
                  <WowButton
                    v-else
                    variant="secondary"
                    class="text-xs py-1 px-2"
                    @click="toggleAdmin(u)"
                  >Revoke Admin</WowButton>
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
                <span v-else-if="u.id === authStore.user.id" class="text-text-muted text-xs italic">You</span>
                <span v-else class="text-text-muted text-xs italic">Primary Admin</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WowCard>

    <!-- System Settings -->
    <WowCard>
      <h2 class="wow-heading text-base mb-4">System Settings</h2>

      <div v-if="sysSettingsLoading" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else class="space-y-6 max-w-lg">
        <!-- Wowhead Tooltips -->
        <label class="flex items-center gap-3 cursor-pointer">
          <button
            type="button"
            class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0"
            :class="settingsForm.wowhead_tooltips ? 'bg-accent-gold' : 'bg-bg-tertiary border border-border-default'"
            @click="settingsForm.wowhead_tooltips = !settingsForm.wowhead_tooltips"
          >
            <span
              class="inline-block h-4 w-4 rounded-full bg-white transition-transform"
              :class="settingsForm.wowhead_tooltips ? 'translate-x-6' : 'translate-x-1'"
            />
          </button>
          <div>
            <span class="text-sm text-text-primary">Enable Wowhead Tooltips</span>
            <p class="text-[10px] text-text-muted mt-0.5">When enabled, hovering equipment items shows rich tooltips with full item statistics from Wowhead. When disabled, basic item info is shown inline.</p>
          </div>
        </label>

        <!-- Auto-Sync -->
        <div class="border-t border-border-default pt-4">
          <h3 class="text-sm text-text-primary font-medium mb-3">Warmane Character Auto-Sync</h3>
          <p class="text-text-muted text-xs mb-3">Automatically sync all active characters from the Warmane armory at a scheduled interval.</p>

          <div class="space-y-3">
            <label class="flex items-center gap-3 cursor-pointer">
              <button
                type="button"
                class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0"
                :class="settingsForm.autosync_enabled ? 'bg-accent-gold' : 'bg-bg-tertiary border border-border-default'"
                @click="settingsForm.autosync_enabled = !settingsForm.autosync_enabled"
              >
                <span
                  class="inline-block h-4 w-4 rounded-full bg-white transition-transform"
                  :class="settingsForm.autosync_enabled ? 'translate-x-6' : 'translate-x-1'"
                />
              </button>
              <span class="text-sm text-text-primary">Auto-Sync Enabled</span>
            </label>

            <div>
              <label class="block text-xs text-text-muted mb-1">Sync Interval</label>
              <select v-model.number="settingsForm.autosync_interval_minutes" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
                <option :value="15">Every 15 minutes</option>
                <option :value="30">Every 30 minutes</option>
                <option :value="60">Every hour</option>
                <option :value="120">Every 2 hours</option>
                <option :value="360">Every 6 hours</option>
                <option :value="720">Every 12 hours</option>
                <option :value="1440">Every 24 hours</option>
              </select>
            </div>
          </div>
        </div>

        <div class="flex gap-3 pt-2">
          <WowButton :loading="sysSettingsSaving" @click="saveAllSettings">Save Settings</WowButton>
          <WowButton variant="secondary" :loading="syncing" @click="triggerManualSync">Sync Now</WowButton>
        </div>
      </div>
    </WowCard>

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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import * as adminApi from '@/api/admin'
import { useTimezone } from '@/composables/useTimezone'

const authStore = useAuthStore()
const uiStore = useUiStore()
const tzHelper = useTimezone()

const users = ref([])
const loading = ref(true)
const error = ref(null)
const showDeleteConfirm = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)

// System settings state (unified)
const sysSettingsLoading = ref(true)
const sysSettingsSaving = ref(false)
const syncing = ref(false)
const settingsForm = ref({
  wowhead_tooltips: true,
  autosync_enabled: false,
  autosync_interval_minutes: 60,
})

onMounted(async () => {
  loading.value = true
  try {
    users.value = await adminApi.getUsers()
  } catch (err) {
    error.value = err?.response?.data?.message ?? 'Failed to load users'
  } finally {
    loading.value = false
  }

  // Load all system settings from unified endpoint
  sysSettingsLoading.value = true
  try {
    const settings = await adminApi.getSystemSettings()
    settingsForm.value = {
      wowhead_tooltips: settings.wowhead_tooltips !== 'false',
      autosync_enabled: settings.autosync_enabled === 'true',
      autosync_interval_minutes: parseInt(settings.autosync_interval_minutes) || 60,
    }
  } catch {
    // ignore – defaults are fine
  } finally {
    sysSettingsLoading.value = false
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

async function toggleAdmin(user) {
  try {
    const updated = await adminApi.updateUser(user.id, { is_admin: !user.is_admin })
    const idx = users.value.findIndex(u => u.id === user.id)
    if (idx !== -1) users.value[idx] = updated
    const msg = updated.is_admin
      ? `${updated.username} promoted to Global Admin`
      : `${updated.username} admin status revoked`
    uiStore.showToast(msg, 'success')
  } catch {
    uiStore.showToast('Failed to update admin status', 'error')
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

async function saveAllSettings() {
  sysSettingsSaving.value = true
  try {
    const updated = await adminApi.updateSystemSettings({
      wowhead_tooltips: settingsForm.value.wowhead_tooltips,
      autosync_enabled: settingsForm.value.autosync_enabled,
      autosync_interval_minutes: settingsForm.value.autosync_interval_minutes,
    })
    settingsForm.value = {
      wowhead_tooltips: updated.wowhead_tooltips !== 'false',
      autosync_enabled: updated.autosync_enabled === 'true',
      autosync_interval_minutes: parseInt(updated.autosync_interval_minutes) || 60,
    }
    uiStore.showToast('System settings saved', 'success')
  } catch {
    uiStore.showToast('Failed to save system settings', 'error')
  } finally {
    sysSettingsSaving.value = false
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
  return tzHelper.formatGuildDate(d, { day: '2-digit', month: 'short', year: 'numeric' })
}
</script>
