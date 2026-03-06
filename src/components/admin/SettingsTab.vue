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
          <h3 class="text-sm text-text-primary font-medium mb-3">{{ t('admin.system.armorySync') }}</h3>
          <p class="text-text-muted text-xs mb-3">{{ t('admin.system.armorySyncHelp') }}</p>

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

    <!-- SMTP / Email Settings -->
    <WowCard>
      <h2 class="wow-heading text-base mb-2">{{ t('admin.smtp.title') }}</h2>
      <p class="text-text-muted text-xs mb-4">{{ t('admin.smtp.help') }}</p>

      <div class="space-y-4 max-w-lg">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('admin.smtp.host') }}</label>
            <input
              v-model="settingsForm.smtp_host"
              type="text"
              placeholder="smtp.gmail.com"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
            />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('admin.smtp.port') }}</label>
            <input
              v-model.number="settingsForm.smtp_port"
              type="number"
              min="1"
              max="65535"
              placeholder="587"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
            />
          </div>
        </div>

        <label class="flex items-center gap-3 cursor-pointer">
          <button
            type="button"
            class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0"
            :class="settingsForm.smtp_tls ? 'bg-accent-gold' : 'bg-bg-tertiary border border-border-default'"
            @click="settingsForm.smtp_tls = !settingsForm.smtp_tls"
          >
            <span
              class="inline-block h-4 w-4 rounded-full bg-white transition-transform"
              :class="settingsForm.smtp_tls ? 'translate-x-6' : 'translate-x-1'"
            />
          </button>
          <span class="text-sm text-text-primary">{{ t('admin.smtp.useTls') }}</span>
        </label>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('admin.smtp.username') }}</label>
            <input
              v-model="settingsForm.smtp_username"
              type="text"
              :placeholder="t('admin.smtp.usernamePlaceholder')"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
            />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('admin.smtp.password') }}</label>
            <input
              v-model="settingsForm.smtp_password"
              type="password"
              :placeholder="t('admin.smtp.passwordPlaceholder')"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
            />
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('admin.smtp.fromEmail') }}</label>
            <input
              v-model="settingsForm.smtp_from_email"
              type="email"
              placeholder="noreply@example.com"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
            />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('admin.smtp.fromName') }}</label>
            <input
              v-model="settingsForm.smtp_from_name"
              type="text"
              placeholder="Raid Calendar"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
            />
          </div>
        </div>

        <!-- Email activation toggle -->
        <div class="border-t border-border-default pt-4">
          <label class="flex items-center gap-3 cursor-pointer">
            <button
              type="button"
              class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0"
              :class="settingsForm.email_activation_required ? 'bg-accent-gold' : 'bg-bg-tertiary border border-border-default'"
              @click="settingsForm.email_activation_required = !settingsForm.email_activation_required"
            >
              <span
                class="inline-block h-4 w-4 rounded-full bg-white transition-transform"
                :class="settingsForm.email_activation_required ? 'translate-x-6' : 'translate-x-1'"
              />
            </button>
            <div>
              <span class="text-sm text-text-primary">{{ t('admin.smtp.requireActivation') }}</span>
              <p class="text-[10px] text-text-muted mt-0.5">{{ t('admin.smtp.requireActivationHelp') }}</p>
            </div>
          </label>
        </div>

        <div class="pt-2">
          <WowButton :loading="sysSettingsSaving" @click="saveAllSettings">{{ t('admin.system.saveSettings') }}</WowButton>
        </div>
      </div>
    </WowCard>

    <!-- Password Policy -->
    <WowCard>
      <h2 class="wow-heading text-base mb-2">{{ t('admin.passwordPolicy.title') }}</h2>
      <p class="text-text-muted text-xs mb-4">{{ t('admin.passwordPolicy.help') }}</p>

      <div class="space-y-4 max-w-lg">
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('admin.passwordPolicy.minLength') }}</label>
          <input
            v-model.number="settingsForm.password_min_length"
            type="number"
            min="4"
            max="128"
            class="w-32 bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
          />
        </div>

        <div class="space-y-3">
          <label class="flex items-center gap-3 cursor-pointer" v-for="toggle in passwordToggles" :key="toggle.key">
            <button
              type="button"
              class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0"
              :class="settingsForm[toggle.key] ? 'bg-accent-gold' : 'bg-bg-tertiary border border-border-default'"
              @click="settingsForm[toggle.key] = !settingsForm[toggle.key]"
            >
              <span
                class="inline-block h-4 w-4 rounded-full bg-white transition-transform"
                :class="settingsForm[toggle.key] ? 'translate-x-6' : 'translate-x-1'"
              />
            </button>
            <span class="text-sm text-text-primary">{{ toggle.label }}</span>
          </label>
        </div>

        <div class="pt-2">
          <WowButton :loading="sysSettingsSaving" @click="saveAllSettings">{{ t('admin.system.saveSettings') }}</WowButton>
        </div>
      </div>
    </WowCard>

    <!-- Discord OAuth Settings (Global Admin only) -->
    <WowCard>
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
            >
              {{ t('common.buttons.copy') }}
            </button>
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
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import * as adminApi from '@/api/admin'

const { t } = useI18n()
const authStore = useAuthStore()
const toast = useToast()

// System settings state (unified)
const sysSettingsLoading = ref(true)
const sysSettingsSaving = ref(false)
const syncing = ref(false)
const settingsForm = ref({
  wowhead_tooltips: true,
  autosync_enabled: true,
  autosync_interval_minutes: 60,
  // SMTP
  smtp_host: '',
  smtp_port: 587,
  smtp_tls: true,
  smtp_username: '',
  smtp_password: '',
  smtp_from_email: '',
  smtp_from_name: 'Raid Calendar',
  email_activation_required: true,
  // Password policy
  password_min_length: 8,
  password_require_uppercase: true,
  password_require_lowercase: true,
  password_require_digit: true,
  password_require_special: true,
})

const passwordToggles = computed(() => [
  { key: 'password_require_uppercase', label: t('admin.passwordPolicy.requireUppercase') },
  { key: 'password_require_lowercase', label: t('admin.passwordPolicy.requireLowercase') },
  { key: 'password_require_digit', label: t('admin.passwordPolicy.requireDigit') },
  { key: 'password_require_special', label: t('admin.passwordPolicy.requireSpecial') },
])

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
      autosync_interval_minutes: parseInt(settings.autosync_interval_minutes, 10) || 60,
      // SMTP
      smtp_host: settings.smtp_host || '',
      smtp_port: parseInt(settings.smtp_port, 10) || 587,
      smtp_tls: (settings.smtp_tls || 'true') !== 'false',
      smtp_username: settings.smtp_username || '',
      smtp_password: settings.smtp_password || '',
      smtp_from_email: settings.smtp_from_email || '',
      smtp_from_name: settings.smtp_from_name || 'Raid Calendar',
      email_activation_required: settings.email_activation_required === 'true',
      // Password policy
      password_min_length: parseInt(settings.password_min_length, 10) || 8,
      password_require_uppercase: settings.password_require_uppercase === 'true',
      password_require_lowercase: settings.password_require_lowercase === 'true',
      password_require_digit: settings.password_require_digit === 'true',
      password_require_special: settings.password_require_special === 'true',
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
    const updated = await adminApi.updateSystemSettings(settingsForm.value)
    settingsForm.value = {
      wowhead_tooltips: updated.wowhead_tooltips !== 'false',
      autosync_enabled: updated.autosync_enabled === 'true',
      autosync_interval_minutes: parseInt(updated.autosync_interval_minutes, 10) || 60,
      smtp_host: updated.smtp_host || '',
      smtp_port: parseInt(updated.smtp_port, 10) || 587,
      smtp_tls: (updated.smtp_tls || 'true') !== 'false',
      smtp_username: updated.smtp_username || '',
      smtp_password: updated.smtp_password || '',
      smtp_from_email: updated.smtp_from_email || '',
      smtp_from_name: updated.smtp_from_name || 'Raid Calendar',
      email_activation_required: updated.email_activation_required === 'true',
      password_min_length: parseInt(updated.password_min_length, 10) || 8,
      password_require_uppercase: updated.password_require_uppercase === 'true',
      password_require_lowercase: updated.password_require_lowercase === 'true',
      password_require_digit: updated.password_require_digit === 'true',
      password_require_special: updated.password_require_special === 'true',
    }
    toast.success(t('admin.system.toasts.settingsSaved'))
  } catch {
    toast.error(t('admin.system.toasts.failedToSaveSettings'))
  } finally {
    sysSettingsSaving.value = false
  }
}

async function triggerManualSync() {
  syncing.value = true
  try {
    await adminApi.triggerSync()
    toast.success(t('admin.system.toasts.syncCompleted'))
  } catch {
    toast.error(t('admin.system.toasts.syncFailed'))
  } finally {
    syncing.value = false
  }
}

async function saveDiscordSettings() {
  discordSaving.value = true
  try {
    await adminApi.updateDiscordSettings(discordForm.value)
    toast.success(t('admin.system.toasts.discordSettingsSaved'))
  } catch {
    toast.error(t('admin.system.toasts.failedToSaveDiscord'))
  } finally {
    discordSaving.value = false
  }
}

async function copyCallbackUrl() {
  try {
    await navigator.clipboard.writeText(discordCallbackUrl.value)
    toast.success(t('admin.system.discord.callbackUrlCopied'))
  } catch {
    // clipboard API may be blocked in non-HTTPS contexts; ignore silently
  }
}
</script>
