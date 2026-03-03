<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6">
      <h1 class="wow-heading text-xl sm:text-2xl">{{ t('profile.title') }}</h1>

      <!-- Profile form -->
      <WowCard>
        <h2 class="wow-heading text-base mb-4">{{ t('profile.profileSettings') }}</h2>
        <form @submit.prevent="saveProfile" class="space-y-4 max-w-lg">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.username') }}</label>
            <input :value="authStore.user?.username" disabled class="w-full bg-bg-tertiary border border-border-default text-text-muted rounded px-3 py-2 text-sm opacity-60 cursor-not-allowed" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.email') }}</label>
            <input :value="authStore.user?.email" disabled class="w-full bg-bg-tertiary border border-border-default text-text-muted rounded px-3 py-2 text-sm opacity-60 cursor-not-allowed" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('profile.displayName') }}</label>
            <input v-model="profileForm.display_name" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.timezone') }}</label>
            <select v-model="profileForm.timezone" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option v-for="tz in timezones" :key="tz" :value="tz">{{ tzLabel(tz) }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('profile.language') }}</label>
            <select v-model="profileForm.language" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="en">{{ t('language.en') }}</option>
              <option value="pl">{{ t('language.pl') }}</option>
            </select>
          </div>
          <div v-if="profileError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ profileError }}</div>
          <div v-if="profileSuccess" class="p-3 rounded bg-green-900/30 border border-green-600 text-green-300 text-sm">{{ profileSuccess }}</div>
          <WowButton type="submit" :loading="savingProfile">{{ t('profile.saveProfile') }}</WowButton>
        </form>
      </WowCard>

      <!-- Change password (local accounts only – Discord users have no password) -->
      <WowCard v-if="authStore.user?.auth_provider === 'local'">
        <h2 class="wow-heading text-base mb-4">{{ t('profile.changePassword') }}</h2>
        <form @submit.prevent="changePassword" class="space-y-4 max-w-lg">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('auth.currentPassword') }} *</label>
            <input v-model="pwForm.current_password" type="password" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('auth.newPassword') }} *</label>
            <input v-model="pwForm.new_password" type="password" required minlength="4" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('auth.confirmNewPassword') }} *</label>
            <input v-model="pwForm.confirm_password" type="password" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div v-if="pwError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ pwError }}</div>
          <div v-if="pwSuccess" class="p-3 rounded bg-green-900/30 border border-green-600 text-green-300 text-sm">{{ pwSuccess }}</div>
          <WowButton type="submit" :loading="changingPw">{{ t('profile.changePassword') }}</WowButton>
        </form>
      </WowCard>
    </div>
  </AppShell>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import { useAuthStore } from '@/stores/auth'
import * as authApi from '@/api/auth'

const authStore = useAuthStore()
const { t, locale } = useI18n()

const profileForm = reactive({ display_name: '', timezone: 'Europe/Warsaw', language: 'en' })
const pwForm = reactive({ current_password: '', new_password: '', confirm_password: '' })

const savingProfile = ref(false)
const profileError = ref(null)
const profileSuccess = ref(null)
const changingPw = ref(false)
const pwError = ref(null)
const pwSuccess = ref(null)

const timezones = [
  'Europe/Warsaw', 'Europe/London', 'Europe/Paris', 'Europe/Berlin',
  'Europe/Madrid', 'Europe/Rome', 'Europe/Amsterdam', 'Europe/Brussels',
  'Europe/Vienna', 'Europe/Prague', 'Europe/Budapest', 'Europe/Bucharest',
  'Europe/Sofia', 'Europe/Athens', 'Europe/Helsinki', 'Europe/Stockholm',
  'Europe/Oslo', 'Europe/Copenhagen', 'Europe/Lisbon', 'Europe/Dublin',
  'Europe/Moscow', 'Europe/Kiev', 'Europe/Istanbul',
  'US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific',
  'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
  'America/Sao_Paulo', 'America/Argentina/Buenos_Aires',
  'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Seoul', 'Asia/Singapore',
  'Asia/Kolkata', 'Asia/Dubai',
  'Australia/Sydney', 'Australia/Melbourne', 'Pacific/Auckland',
  'UTC',
]

function tzLabel(tz) {
  const key = 'timezones.' + tz.replace(/\//g, '_').replace(/-/g, '_')
  const label = t(key)
  return label !== key ? label : tz
}

onMounted(() => {
  if (authStore.user) {
    profileForm.display_name = authStore.user.display_name || ''
    profileForm.timezone = authStore.user.timezone || 'Europe/Warsaw'
    profileForm.language = authStore.user.language || 'en'
  }
})

async function saveProfile() {
  profileError.value = null
  profileSuccess.value = null
  savingProfile.value = true
  try {
    const updated = await authApi.updateProfile(profileForm)
    authStore.user = updated
    locale.value = updated.language || 'en'
    profileSuccess.value = t('profile.profileSaved')
  } catch (err) {
    profileError.value = err?.response?.data?.message ?? t('profile.failedToSave')
  } finally {
    savingProfile.value = false
  }
}

async function changePassword() {
  pwError.value = null
  pwSuccess.value = null

  if (pwForm.new_password !== pwForm.confirm_password) {
    pwError.value = t('auth.newPasswordsDoNotMatch')
    return
  }

  changingPw.value = true
  try {
    await authApi.changePassword({
      current_password: pwForm.current_password,
      new_password: pwForm.new_password,
    })
    pwSuccess.value = t('profile.passwordChangedSuccess')
    pwForm.current_password = ''
    pwForm.new_password = ''
    pwForm.confirm_password = ''
  } catch (err) {
    pwError.value = err?.response?.data?.message ?? t('profile.failedToChangePassword')
  } finally {
    changingPw.value = false
  }
}
</script>
