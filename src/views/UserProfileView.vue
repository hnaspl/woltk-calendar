<template>
  <AppShell>
    <div class="p-4 md:p-6 space-y-6">
      <h1 class="wow-heading text-2xl">User Profile</h1>

      <!-- Profile form -->
      <WowCard>
        <h2 class="wow-heading text-base mb-4">Profile Settings</h2>
        <form @submit.prevent="saveProfile" class="space-y-4 max-w-lg">
          <div>
            <label class="block text-xs text-text-muted mb-1">Username</label>
            <input :value="authStore.user?.username" disabled class="w-full bg-bg-tertiary border border-border-default text-text-muted rounded px-3 py-2 text-sm opacity-60 cursor-not-allowed" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Email</label>
            <input :value="authStore.user?.email" disabled class="w-full bg-bg-tertiary border border-border-default text-text-muted rounded px-3 py-2 text-sm opacity-60 cursor-not-allowed" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Display Name</label>
            <input v-model="profileForm.display_name" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Timezone</label>
            <select v-model="profileForm.timezone" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option v-for="tz in timezones" :key="tz" :value="tz">{{ tz }}</option>
            </select>
          </div>
          <div v-if="profileError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ profileError }}</div>
          <div v-if="profileSuccess" class="p-3 rounded bg-green-900/30 border border-green-600 text-green-300 text-sm">{{ profileSuccess }}</div>
          <WowButton type="submit" :loading="savingProfile">Save Profile</WowButton>
        </form>
      </WowCard>

      <!-- Change password -->
      <WowCard>
        <h2 class="wow-heading text-base mb-4">Change Password</h2>
        <form @submit.prevent="changePassword" class="space-y-4 max-w-lg">
          <div>
            <label class="block text-xs text-text-muted mb-1">Current Password *</label>
            <input v-model="pwForm.current_password" type="password" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">New Password *</label>
            <input v-model="pwForm.new_password" type="password" required minlength="4" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Confirm New Password *</label>
            <input v-model="pwForm.confirm_password" type="password" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div v-if="pwError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ pwError }}</div>
          <div v-if="pwSuccess" class="p-3 rounded bg-green-900/30 border border-green-600 text-green-300 text-sm">{{ pwSuccess }}</div>
          <WowButton type="submit" :loading="changingPw">Change Password</WowButton>
        </form>
      </WowCard>
    </div>
  </AppShell>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import { useAuthStore } from '@/stores/auth'
import * as authApi from '@/api/auth'

const authStore = useAuthStore()

const profileForm = reactive({ display_name: '', timezone: 'UTC' })
const pwForm = reactive({ current_password: '', new_password: '', confirm_password: '' })

const savingProfile = ref(false)
const profileError = ref(null)
const profileSuccess = ref(null)
const changingPw = ref(false)
const pwError = ref(null)
const pwSuccess = ref(null)

const timezones = [
  'UTC', 'Europe/London', 'Europe/Berlin', 'Europe/Paris', 'Europe/Warsaw',
  'Europe/Moscow', 'Europe/Athens', 'US/Eastern', 'US/Central', 'US/Pacific',
  'Asia/Tokyo', 'Australia/Sydney',
]

onMounted(() => {
  if (authStore.user) {
    profileForm.display_name = authStore.user.display_name || ''
    profileForm.timezone = authStore.user.timezone || 'UTC'
  }
})

async function saveProfile() {
  profileError.value = null
  profileSuccess.value = null
  savingProfile.value = true
  try {
    const updated = await authApi.updateProfile(profileForm)
    authStore.user = updated
    profileSuccess.value = 'Profile saved'
  } catch (err) {
    profileError.value = err?.response?.data?.message ?? 'Failed to save profile'
  } finally {
    savingProfile.value = false
  }
}

async function changePassword() {
  pwError.value = null
  pwSuccess.value = null

  if (pwForm.new_password !== pwForm.confirm_password) {
    pwError.value = 'New passwords do not match'
    return
  }

  changingPw.value = true
  try {
    await authApi.changePassword({
      current_password: pwForm.current_password,
      new_password: pwForm.new_password,
    })
    pwSuccess.value = 'Password changed successfully'
    pwForm.current_password = ''
    pwForm.new_password = ''
    pwForm.confirm_password = ''
  } catch (err) {
    pwError.value = err?.response?.data?.message ?? 'Failed to change password'
  } finally {
    changingPw.value = false
  }
}
</script>
