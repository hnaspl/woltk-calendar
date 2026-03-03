<template>
  <div class="space-y-6">
    <!-- Users table -->
    <WowCard>
      <div class="flex items-center justify-between mb-4">
        <h2 class="wow-heading text-base">{{ t('admin.users.title', { count: users.length }) }}</h2>
      </div>

      <div v-if="loading" class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-bg-tertiary border-b border-border-default">
              <th class="hidden sm:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.users.id') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.username') }}</th>
              <th class="hidden md:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.email') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.status') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.users.admin') }}</th>
              <th class="hidden lg:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.users.registered') }}</th>
              <th class="text-right px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.labels.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-default">
            <tr v-for="u in users" :key="u.id" class="hover:bg-bg-tertiary/50 transition-colors">
              <td class="hidden sm:table-cell px-4 py-2.5 text-text-muted">{{ u.id }}</td>
              <td class="px-4 py-2.5 text-text-primary font-medium">{{ u.username }}</td>
              <td class="hidden md:table-cell px-4 py-2.5 text-text-muted">{{ u.email }}</td>
              <td class="px-4 py-2.5">
                <span
                  class="inline-block px-2 py-0.5 text-xs rounded-full font-medium"
                  :class="u.is_active ? 'bg-green-900/50 text-green-300 border border-green-600' : 'bg-red-900/50 text-red-300 border border-red-600'"
                >
                  {{ u.is_active ? t('common.status.active') : t('admin.users.blocked') }}
                </span>
              </td>
              <td class="px-4 py-2.5">
                <span v-if="u.is_admin" class="text-accent-gold text-xs font-bold">{{ t('admin.users.admin') }}</span>
                <span v-else class="text-text-muted text-xs">—</span>
              </td>
              <td class="hidden lg:table-cell px-4 py-2.5 text-text-muted text-xs">{{ formatDate(u.created_at) }}</td>
              <td class="px-4 py-2.5 text-right">
                <div class="flex flex-wrap gap-1 justify-end">
                <template v-if="u.id !== authStore.user.id && u.id !== 1">
                  <WowButton
                    v-if="!u.is_admin"
                    variant="secondary"
                    class="text-xs py-1 px-2"
                    @click="toggleAdmin(u)"
                  >{{ t('admin.users.promoteAdmin') }}</WowButton>
                  <WowButton
                    v-else
                    variant="secondary"
                    class="text-xs py-1 px-2"
                    @click="toggleAdmin(u)"
                  >{{ t('admin.users.revokeAdmin') }}</WowButton>
                  <WowButton
                    v-if="u.is_active"
                    variant="secondary"
                    class="text-xs py-1 px-2"
                    @click="toggleBlock(u)"
                  >{{ t('admin.users.block') }}</WowButton>
                  <WowButton
                    v-else
                    variant="secondary"
                    class="text-xs py-1 px-2"
                    @click="toggleBlock(u)"
                  >{{ t('admin.users.unblock') }}</WowButton>
                  <WowButton variant="danger" class="text-xs py-1 px-2" @click="confirmDelete(u)">{{ t('common.buttons.delete') }}</WowButton>
                </template>
                <span v-else-if="u.id === authStore.user.id" class="text-text-muted text-xs italic">{{ t('common.labels.you') }}</span>
                <span v-else class="text-text-muted text-xs italic">{{ t('admin.users.primaryAdmin') }}</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WowCard>

    <!-- System Settings -->
    <WowCard>
      <h2 class="wow-heading text-base mb-4">{{ t('admin.system.title') }}</h2>

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
            <span class="text-sm text-text-primary">{{ t('admin.system.wowheadTooltips') }}</span>
            <p class="text-[10px] text-text-muted mt-0.5">{{ t('admin.system.wowheadHelp') }}</p>
          </div>
        </label>

        <!-- Auto-Sync -->
        <div class="border-t border-border-default pt-4">
          <h3 class="text-sm text-text-primary font-medium mb-3">{{ t('admin.system.warmaneSync') }}</h3>
          <p class="text-text-muted text-xs mb-3">{{ t('admin.system.warmaneSyncHelp') }}</p>

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
              <span class="text-sm text-text-primary">{{ t('admin.system.autoSyncEnabled') }}</span>
            </label>

            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('admin.system.syncInterval') }}</label>
              <select v-model.number="settingsForm.autosync_interval_minutes" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
                <option :value="15">{{ t('admin.system.every15min') }}</option>
                <option :value="30">{{ t('admin.system.every30min') }}</option>
                <option :value="60">{{ t('admin.system.everyHour') }}</option>
                <option :value="120">{{ t('admin.system.every2hours') }}</option>
                <option :value="360">{{ t('admin.system.every6hours') }}</option>
                <option :value="720">{{ t('admin.system.every12hours') }}</option>
                <option :value="1440">{{ t('admin.system.every24hours') }}</option>
              </select>
            </div>
          </div>
        </div>

        <div class="flex gap-3 pt-2">
          <WowButton :loading="sysSettingsSaving" @click="saveAllSettings">{{ t('admin.system.saveSettings') }}</WowButton>
          <WowButton variant="secondary" :loading="syncing" @click="triggerManualSync">{{ t('admin.system.syncNow') }}</WowButton>
        </div>
      </div>
    </WowCard>

    <!-- Discord OAuth Settings (Global Admin only) -->
    <WowCard v-if="authStore.user?.is_admin">
      <h2 class="wow-heading text-base mb-2">{{ t('admin.system.discord.title') }}</h2>
      <p class="text-text-muted text-xs mb-4">{{ t('admin.system.discord.help') }}</p>

      <div v-if="discordLoading" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" aria-label="Loading Discord settings" />
      <div v-else class="space-y-4 max-w-lg">
        <!-- Callback URL (auto-generated, read-only) -->
        <div v-if="discordCallbackUrl" class="p-3 rounded bg-bg-secondary border border-border-gold/50">
          <label class="block text-xs text-accent-gold font-semibold mb-1">{{ t('admin.system.discord.callbackUrlLabel') }}</label>
          <p class="text-text-muted text-xs mb-2">{{ t('admin.system.discord.callbackUrlHelp') }}</p>
          <div class="flex items-center gap-2">
            <code class="flex-1 text-xs text-text-primary bg-bg-tertiary border border-border-default rounded px-2 py-1.5 select-all break-all">{{ discordCallbackUrl }}</code>
            <button
              @click="copyCallbackUrl"
              class="shrink-0 text-xs bg-bg-tertiary border border-border-default hover:border-border-gold text-text-muted hover:text-text-primary rounded px-2 py-1.5 transition-colors"
              :title="t('common.buttons.copy')"
            >📋</button>
          </div>
        </div>

        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('admin.system.discord.clientId') }}</label>
          <input
            v-model="discordForm.discord_client_id"
            type="text"
            :placeholder="t('admin.system.discord.clientIdPlaceholder')"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
          />
        </div>

        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('admin.system.discord.clientSecret') }}</label>
          <input
            v-model="discordForm.discord_client_secret"
            type="password"
            :placeholder="t('admin.system.discord.clientSecretPlaceholder')"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
          />
        </div>

        <div class="pt-2">
          <WowButton :loading="discordSaving" @click="saveDiscordSettings">{{ t('admin.system.discord.saveSettings') }}</WowButton>
        </div>
      </div>
    </WowCard>

    <!-- Delete confirmation -->
    <WowModal v-model="showDeleteConfirm" :title="t('admin.users.deleteUser')" size="sm">
      <p class="text-text-muted">{{ t('admin.users.deleteConfirm', { name: deleteTarget?.username }) }}</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showDeleteConfirm = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="danger" :loading="deleting" @click="doDelete">{{ t('common.buttons.delete') }}</WowButton>
        </div>
      </template>
    </WowModal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import * as adminApi from '@/api/admin'
import { useFormatting } from '@/composables/useFormatting'

const { t } = useI18n()
const authStore = useAuthStore()
const uiStore = useUiStore()
const { formatDate } = useFormatting()

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

// Discord OAuth settings state
const discordLoading = ref(true)
const discordSaving = ref(false)
const discordCallbackUrl = ref('')
const discordForm = ref({
  discord_client_id: '',
  discord_client_secret: '',
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

  // Load Discord OAuth settings (global admin only)
  if (authStore.user?.is_admin) {
    discordLoading.value = true
    try {
      const discord = await adminApi.getDiscordSettings()
      discordCallbackUrl.value = discord.callback_url || ''
      discordForm.value = {
        discord_client_id: discord.discord_client_id || '',
        discord_client_secret: discord.discord_client_secret || '',
      }
    } catch {
      // ignore – defaults are fine
    } finally {
      discordLoading.value = false
    }
  } else {
    discordLoading.value = false
  }
})

async function toggleBlock(user) {
  try {
    const updated = await adminApi.updateUser(user.id, { is_active: !user.is_active })
    const idx = users.value.findIndex(u => u.id === user.id)
    if (idx !== -1) users.value[idx] = updated
    uiStore.showToast(t(updated.is_active ? 'admin.system.toasts.userUnblocked' : 'admin.system.toasts.userBlocked'), 'success')
  } catch {
    uiStore.showToast(t('admin.system.toasts.failedToUpdateUser'), 'error')
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
    uiStore.showToast(t('admin.system.toasts.failedToUpdateAdmin'), 'error')
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
    uiStore.showToast(t('admin.system.toasts.userDeleted'), 'success')
  } catch {
    uiStore.showToast(t('admin.system.toasts.failedToDeleteUser'), 'error')
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
    uiStore.showToast(t('admin.system.toasts.settingsSaved'), 'success')
  } catch {
    uiStore.showToast(t('admin.system.toasts.failedToSaveSettings'), 'error')
  } finally {
    sysSettingsSaving.value = false
  }
}

async function triggerManualSync() {
  syncing.value = true
  try {
    await adminApi.triggerSync()
    uiStore.showToast(t('admin.system.toasts.syncCompleted'), 'success')
  } catch {
    uiStore.showToast(t('admin.system.toasts.syncFailed'), 'error')
  } finally {
    syncing.value = false
  }
}

async function saveDiscordSettings() {
  discordSaving.value = true
  try {
    await adminApi.updateDiscordSettings(discordForm.value)
    uiStore.showToast(t('admin.system.toasts.discordSettingsSaved'), 'success')
  } catch {
    uiStore.showToast(t('admin.system.toasts.failedToSaveDiscord'), 'error')
  } finally {
    discordSaving.value = false
  }
}

async function copyCallbackUrl() {
  try {
    await navigator.clipboard.writeText(discordCallbackUrl.value)
    uiStore.showToast(t('admin.system.discord.callbackUrlCopied'), 'success')
  } catch {
    // Fallback: select the text
  }
}
</script>
