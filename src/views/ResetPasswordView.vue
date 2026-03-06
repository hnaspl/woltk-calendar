<template>
  <div class="min-h-screen bg-bg-primary flex items-center justify-center p-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <img
          :src="logoIcon"
          alt="Raid Calendar"
          class="w-16 h-16 sm:w-20 sm:h-20 rounded-xl border-2 border-border-gold mx-auto mb-4 shadow-gold"
        />
        <h1 class="wow-heading text-xl sm:text-2xl mb-1">{{ t('auth.appTitle') }}</h1>
      </div>

      <WowCard :gold="true">
        <!-- Success -->
        <div v-if="success" class="text-center py-6">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-green-900/30 border border-green-600 flex items-center justify-center">
            <svg class="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
          </div>
          <h2 class="text-lg font-semibold text-text-primary mb-2">{{ t('auth.passwordResetSuccess') }}</h2>
          <p class="text-text-muted text-sm mb-4">{{ t('auth.passwordResetSuccessDesc') }}</p>
          <RouterLink to="/login">
            <WowButton class="w-full">{{ t('auth.signIn') }}</WowButton>
          </RouterLink>
        </div>

        <!-- Form -->
        <template v-else>
          <h2 class="text-lg font-semibold text-text-primary mb-2">{{ t('auth.resetPassword') }}</h2>
          <p class="text-text-muted text-sm mb-6">{{ t('auth.resetPasswordDesc') }}</p>

          <div v-if="error" class="mb-4 p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">
            {{ error }}
          </div>

          <form @submit.prevent="handleSubmit" class="space-y-4">
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('auth.newPassword') }}</label>
              <input
                v-model="newPassword"
                type="password"
                autocomplete="new-password"
                required
                minlength="8"
                :placeholder="t('auth.placeholders.minChars')"
                class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50 transition-colors"
                @input="checkPolicy"
              />
              <!-- Password policy checklist -->
              <div v-if="passwordPolicy && newPassword" class="mt-2 space-y-1">
                <div v-for="rule in policyRules" :key="rule.key" class="flex items-center gap-1.5 text-xs" :class="rule.met ? 'text-green-400' : 'text-text-muted'">
                  <svg v-if="rule.met" class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                  <svg v-else class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke-width="2"/></svg>
                  {{ rule.label }}
                </div>
              </div>
            </div>

            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('auth.confirmPassword') }}</label>
              <input
                v-model="confirmPassword"
                type="password"
                autocomplete="new-password"
                required
                :placeholder="t('auth.placeholders.repeatPassword')"
                class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50 transition-colors"
              />
            </div>

            <WowButton type="submit" :loading="loading" class="w-full">
              {{ t('auth.resetPassword') }}
            </WowButton>
          </form>

          <p class="text-center text-sm text-text-muted mt-6">
            <RouterLink to="/login" class="text-accent-gold hover:text-yellow-400 transition-colors">
              {{ t('auth.backToLogin') }}
            </RouterLink>
          </p>
        </template>
      </WowCard>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useWowIcons } from '@/composables/useWowIcons'
import * as authApi from '@/api/auth'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'

const { t } = useI18n()
const { getRaidIcon } = useWowIcons()
const logoIcon = getRaidIcon('icc')
const route = useRoute()

const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref(null)
const success = ref(false)
const passwordPolicy = ref(null)

const policyRules = computed(() => {
  if (!passwordPolicy.value) return []
  const p = passwordPolicy.value
  const pwd = newPassword.value
  const rules = []
  rules.push({
    key: 'length',
    label: t('auth.policy.minLength', { n: p.min_length }),
    met: pwd.length >= p.min_length,
  })
  if (p.require_uppercase) {
    rules.push({ key: 'upper', label: t('auth.policy.uppercase'), met: /[A-Z]/.test(pwd) })
  }
  if (p.require_lowercase) {
    rules.push({ key: 'lower', label: t('auth.policy.lowercase'), met: /[a-z]/.test(pwd) })
  }
  if (p.require_digit) {
    rules.push({ key: 'digit', label: t('auth.policy.digit'), met: /\d/.test(pwd) })
  }
  if (p.require_special) {
    rules.push({ key: 'special', label: t('auth.policy.special'), met: /[^a-zA-Z0-9]/.test(pwd) })
  }
  return rules
})

function checkPolicy() {
  // triggers reactivity via policyRules
}

onMounted(async () => {
  if (!route.query.token) {
    error.value = t('auth.errors.invalidResetToken')
  }
  try {
    passwordPolicy.value = await authApi.getPasswordPolicy()
  } catch {
    // defaults
  }
})

async function handleSubmit() {
  error.value = null
  if (newPassword.value !== confirmPassword.value) {
    error.value = t('auth.passwordsDoNotMatch')
    return
  }
  loading.value = true
  try {
    await authApi.resetPassword({
      token: route.query.token,
      new_password: newPassword.value,
    })
    success.value = true
  } catch (err) {
    error.value = err?.response?.data?.error || t('auth.errors.resetFailed')
  } finally {
    loading.value = false
  }
}
</script>
