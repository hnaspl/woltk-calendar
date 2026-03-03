<template>
  <div class="space-y-6">
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

    <!-- Guild Limits -->
    <WowCard>
      <h2 class="wow-heading text-base mb-4">{{ t('admin.settings.guildLimits') }}</h2>

      <div v-if="sysSettingsLoading" class="h-20 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else class="space-y-4 max-w-lg">
        <div>
          <label class="block text-sm text-text-primary mb-1">{{ t('admin.settings.maxGuildsPerUser') }}</label>
          <p class="text-[10px] text-text-muted mb-2">{{ t('admin.settings.maxGuildsPerUserHelp') }}</p>
          <input
            v-model.number="settingsForm.max_guilds_per_user"
            type="number"
            min="1"
            class="w-32 bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
          />
        </div>
        <div class="pt-2">
          <WowButton :loading="sysSettingsSaving" @click="saveAllSettings">{{ t('admin.system.saveSettings') }}</WowButton>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import * as adminApi from '@/api/admin'

const { t } = useI18n()
const authStore = useAuthStore()
const uiStore = useUiStore()

// System settings state (unified)
const sysSettingsLoading = ref(true)
const sysSettingsSaving = ref(false)
const syncing = ref(false)
const settingsForm = ref({
  wowhead_tooltips: true,
  autosync_enabled: false,
  autosync_interval_minutes: 60,
  max_guilds_per_user: 5,
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
  // Load all system settings from unified endpoint
  sysSettingsLoading.value = true
  try {
    const settings = await adminApi.getSystemSettings()
    settingsForm.value = {
      wowhead_tooltips: settings.wowhead_tooltips !== 'false',
      autosync_enabled: settings.autosync_enabled === 'true',
      autosync_interval_minutes: parseInt(settings.autosync_interval_minutes) || 60,
      max_guilds_per_user: parseInt(settings.max_guilds_per_user) || 5,
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

async function saveAllSettings() {
  sysSettingsSaving.value = true
  try {
    const updated = await adminApi.updateSystemSettings({
      wowhead_tooltips: settingsForm.value.wowhead_tooltips,
      autosync_enabled: settingsForm.value.autosync_enabled,
      autosync_interval_minutes: settingsForm.value.autosync_interval_minutes,
      max_guilds_per_user: settingsForm.value.max_guilds_per_user,
    })
    settingsForm.value = {
      wowhead_tooltips: updated.wowhead_tooltips !== 'false',
      autosync_enabled: updated.autosync_enabled === 'true',
      autosync_interval_minutes: parseInt(updated.autosync_interval_minutes) || 60,
      max_guilds_per_user: parseInt(updated.max_guilds_per_user) || 5,
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
    // clipboard API may be blocked in non-HTTPS contexts; ignore silently
  }
}
</script>
