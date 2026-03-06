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
        <!-- Success message -->
        <div v-if="success" class="text-center py-6">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-green-900/30 border border-green-600 flex items-center justify-center">
            <svg class="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
          </div>
          <h2 class="text-lg font-semibold text-text-primary mb-2">{{ t('auth.resetEmailSentTitle') }}</h2>
          <p class="text-text-muted text-sm mb-4">{{ t('auth.resetEmailSentDesc') }}</p>
          <RouterLink to="/login" class="text-accent-gold hover:text-yellow-400 transition-colors text-sm">
            {{ t('auth.backToLogin') }}
          </RouterLink>
        </div>

        <!-- Form -->
        <template v-else>
          <h2 class="text-lg font-semibold text-text-primary mb-2">{{ t('auth.forgotPassword') }}</h2>
          <p class="text-text-muted text-sm mb-6">{{ t('auth.forgotPasswordDesc') }}</p>

          <div v-if="error" class="mb-4 p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">
            {{ error }}
          </div>

          <form @submit.prevent="handleSubmit" class="space-y-4">
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.email') }}</label>
              <input
                v-model="email"
                type="email"
                autocomplete="email"
                required
                :placeholder="t('auth.placeholders.email')"
                class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50 transition-colors"
              />
            </div>

            <WowButton type="submit" :loading="loading" class="w-full">
              {{ t('auth.sendResetLink') }}
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
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useWowIcons } from '@/composables/useWowIcons'
import * as authApi from '@/api/auth'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'

const { t } = useI18n()
const { getRaidIcon } = useWowIcons()
const logoIcon = getRaidIcon('icc')

const email = ref('')
const loading = ref(false)
const error = ref(null)
const success = ref(false)

async function handleSubmit() {
  error.value = null
  loading.value = true
  try {
    await authApi.forgotPassword(email.value)
    success.value = true
  } catch (err) {
    error.value = err?.response?.data?.error || t('auth.errors.resetFailed')
  } finally {
    loading.value = false
  }
}
</script>
