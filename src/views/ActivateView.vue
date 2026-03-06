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
        <!-- Loading state -->
        <div v-if="loading" class="text-center py-8">
          <div class="w-8 h-8 border-2 border-accent-gold border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p class="text-text-muted text-sm">{{ t('auth.activatingAccount') }}</p>
        </div>

        <!-- Success -->
        <div v-else-if="success" class="text-center py-6">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-green-900/30 border border-green-600 flex items-center justify-center">
            <svg class="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
          </div>
          <h2 class="text-lg font-semibold text-text-primary mb-2">{{ t('auth.accountActivated') }}</h2>
          <p class="text-text-muted text-sm mb-4">{{ t('auth.accountActivatedDesc') }}</p>
          <RouterLink to="/dashboard">
            <WowButton class="w-full">{{ t('auth.goToDashboard') }}</WowButton>
          </RouterLink>
        </div>

        <!-- Error -->
        <div v-else class="text-center py-6">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-red-900/30 border border-red-600 flex items-center justify-center">
            <svg class="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </div>
          <h2 class="text-lg font-semibold text-text-primary mb-2">{{ t('auth.activationFailed') }}</h2>
          <p class="text-text-muted text-sm mb-4">{{ error || t('auth.activationFailedDesc') }}</p>
          <RouterLink to="/register">
            <WowButton variant="secondary" class="w-full">{{ t('auth.register') }}</WowButton>
          </RouterLink>
        </div>
      </WowCard>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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

const loading = ref(true)
const success = ref(false)
const error = ref(null)

onMounted(async () => {
  const token = route.query.token
  if (!token) {
    loading.value = false
    error.value = t('auth.errors.invalidActivationToken')
    return
  }

  try {
    await authApi.activateAccount(token)
    success.value = true
  } catch (err) {
    error.value = err?.response?.data?.error || t('auth.activationFailedDesc')
  } finally {
    loading.value = false
  }
})
</script>
