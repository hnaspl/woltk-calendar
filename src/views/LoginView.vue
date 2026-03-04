<template>
  <div class="min-h-screen bg-bg-primary flex items-center justify-center p-4">
    <div class="w-full max-w-sm">
      <!-- Logo / Branding -->
      <div class="text-center mb-8">
        <img
          :src="logoIcon"
          alt="Raid Calendar"
          class="w-16 h-16 sm:w-20 sm:h-20 rounded-xl border-2 border-border-gold mx-auto mb-4 shadow-gold"
        />
        <h1 class="wow-heading text-xl sm:text-2xl mb-1">{{ t('auth.appTitle') }}</h1>
        <p class="text-text-muted text-sm">{{ t('auth.appSubtitle') }}</p>
      </div>

      <WowCard :gold="true">
        <h2 class="text-lg font-semibold text-text-primary mb-6">{{ t('auth.signIn') }}</h2>

        <!-- Invite redirect banner -->
        <div v-if="isInviteRedirect" class="mb-4 p-3 rounded bg-accent-gold/10 border border-accent-gold/30 text-accent-gold text-sm">
          {{ t('auth.loginToAcceptInvite') }}
        </div>

        <div v-if="error" class="mb-4 p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">
          {{ error }}
        </div>

        <!-- Discord Login Button -->
        <button
          v-if="discordEnabled"
          @click="handleDiscordLogin"
          :disabled="discordLoading"
          class="w-full flex items-center justify-center gap-2 bg-[#5865F2] hover:bg-[#4752C4] text-white font-medium py-2.5 px-4 rounded transition-colors mb-4 disabled:opacity-50"
        >
          <img :src="discordIcon" alt="Discord" class="w-5 h-5" />
          {{ t('auth.signInWithDiscord') }}
        </button>

        <div v-if="discordEnabled" class="flex items-center gap-3 mb-4">
          <div class="flex-1 border-t border-border-default"></div>
          <span class="text-text-muted text-xs uppercase">{{ t('auth.orSeparator') }}</span>
          <div class="flex-1 border-t border-border-default"></div>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-4">
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

          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('auth.password') }}</label>
            <input
              v-model="password"
              type="password"
              autocomplete="current-password"
              required
              :placeholder="t('auth.placeholders.password')"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50 transition-colors"
            />
          </div>

          <WowButton type="submit" :loading="loading" class="w-full mt-2">
            {{ t('auth.signIn') }}
          </WowButton>
        </form>

        <p class="text-center text-sm text-text-muted mt-6">
          {{ t('auth.noAccount') }}
          <RouterLink :to="registerLink" class="text-accent-gold hover:text-yellow-400 transition-colors">
            {{ t('auth.register') }}
          </RouterLink>
        </p>
      </WowCard>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuth } from '@/composables/useAuth'
import { useWowIcons } from '@/composables/useWowIcons'
import * as authApi from '@/api/auth'
import discordIcon from '@/assets/icons/discord/discord-mark-white.svg'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'

const { t } = useI18n()
const { getRaidIcon } = useWowIcons()
const logoIcon = getRaidIcon('icc')
const route = useRoute()

const { login, isLoading, authError } = useAuth()

const email = ref('')
const password = ref('')
const error = ref(null)
const loading = ref(false)
const discordEnabled = ref(false)
const discordLoading = ref(false)

const isInviteRedirect = computed(() => {
  const redirect = route.query.redirect || ''
  return redirect.startsWith('/invite/')
})

const registerLink = computed(() => {
  const redirect = route.query.redirect
  return redirect ? { path: '/register', query: { redirect } } : '/register'
})

onMounted(async () => {
  // Check URL params for Discord error
  const params = new URLSearchParams(window.location.search)
  if (params.get('error') === 'discord_failed') {
    error.value = t('auth.errors.discordLoginFailed')
  } else if (params.get('error') === 'account_disabled') {
    error.value = t('auth.errors.accountDisabled')
  } else if (params.get('error') === 'discord_not_configured') {
    error.value = t('auth.errors.discordNotConfigured')
  }

  try {
    const data = await authApi.getDiscordEnabled()
    discordEnabled.value = data.enabled
  } catch {
    // Discord not available – hide button
  }
})

async function handleLogin() {
  error.value = null
  loading.value = true
  try {
    await login(email.value, password.value)
  } catch (err) {
    error.value = err?.response?.data?.message ?? authError.value ?? t('auth.loginFailed')
  } finally {
    loading.value = false
  }
}

async function handleDiscordLogin() {
  // Direct navigation to backend endpoint which returns HTTP 302 to Discord
  window.location.href = '/api/v2/auth/discord/login'
}
</script>
