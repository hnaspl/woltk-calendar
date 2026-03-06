<template>
  <div class="min-h-screen bg-bg-primary flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <img
          :src="logoIcon"
          alt="Raid Calendar"
          class="w-16 h-16 sm:w-20 sm:h-20 rounded-xl border-2 border-border-gold mx-auto mb-4 shadow-gold"
        />
        <h1 class="wow-heading text-xl sm:text-2xl mb-1">{{ t('auth.appTitle') }}</h1>
        <p class="text-text-muted text-sm">{{ t('auth.createYourAccount') }}</p>
      </div>

      <WowCard :gold="true">
        <!-- Activation success message -->
        <div v-if="activationSuccess" class="text-center py-6">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-green-900/30 border border-green-600 flex items-center justify-center">
            <svg class="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
          </div>
          <h2 class="text-lg font-semibold text-text-primary mb-2">{{ t('auth.activationEmailSentTitle') }}</h2>
          <p class="text-text-muted text-sm mb-4">{{ t('auth.activationEmailSentDesc') }}</p>
          <RouterLink to="/login" class="text-accent-gold hover:text-yellow-400 transition-colors text-sm">
            {{ t('auth.signIn') }}
          </RouterLink>
        </div>

        <!-- Registration form -->
        <template v-else>
          <h2 class="text-lg font-semibold text-text-primary mb-6">{{ t('auth.register') }}</h2>

          <!-- Invite redirect banner -->
          <div v-if="isInviteRedirect" class="mb-4 p-3 rounded bg-accent-gold/10 border border-accent-gold/30 text-accent-gold text-sm">
            {{ t('auth.registerToAcceptInvite') }}
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

          <form @submit.prevent="handleRegister" class="space-y-4">
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.username') }}</label>
              <input
                v-model="username"
                type="text"
                autocomplete="username"
                required
                minlength="3"
                :placeholder="t('auth.placeholders.username')"
                class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50 transition-colors"
              />
            </div>

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
                autocomplete="new-password"
                required
                minlength="8"
                :placeholder="t('auth.placeholders.minChars')"
                class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50 transition-colors"
                @input="checkPasswordPolicy"
              />
              <!-- Password policy checklist -->
              <div v-if="passwordPolicy && password" class="mt-2 space-y-1">
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

            <!-- Create workspace checkbox -->
            <div class="border-t border-border-default pt-4">
              <label class="flex items-start gap-3 cursor-pointer">
                <input
                  v-model="createTenant"
                  type="checkbox"
                  class="mt-0.5 w-4 h-4 rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold accent-amber-500"
                />
                <div>
                  <span class="text-sm text-text-primary">{{ t('auth.createOwnWorkspace') }}</span>
                  <p class="text-[11px] text-text-muted mt-0.5">{{ t('auth.createWorkspaceHelp') }}</p>
                </div>
              </label>
            </div>

            <WowButton type="submit" :loading="loading" class="w-full mt-2">
              {{ t('auth.createAccount') }}
            </WowButton>
          </form>

          <p class="text-center text-sm text-text-muted mt-6">
            {{ t('auth.hasAccount') }}
            <RouterLink :to="loginLink" class="text-accent-gold hover:text-yellow-400 transition-colors">
              {{ t('auth.signIn') }}
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

const { register, authError } = useAuth()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const createTenant = ref(true)
const error = ref(null)
const loading = ref(false)
const discordEnabled = ref(false)
const discordLoading = ref(false)
const activationSuccess = ref(false)
const passwordPolicy = ref(null)

const isInviteRedirect = computed(() => {
  const redirect = route.query.redirect || ''
  return redirect.startsWith('/invite/')
})

const loginLink = computed(() => {
  const redirect = route.query.redirect
  return redirect ? { path: '/login', query: { redirect } } : '/login'
})

const policyRules = computed(() => {
  if (!passwordPolicy.value) return []
  const p = passwordPolicy.value
  const pwd = password.value
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

function checkPasswordPolicy() {
  // Policy already loaded, just triggers reactivity via policyRules
}

onMounted(async () => {
  try {
    const data = await authApi.getDiscordEnabled()
    discordEnabled.value = data.enabled
  } catch {
    // Discord not available – hide button
  }
  try {
    passwordPolicy.value = await authApi.getPasswordPolicy()
  } catch {
    // Defaults are fine
  }
})

async function handleRegister() {
  error.value = null
  if (password.value !== confirmPassword.value) {
    error.value = t('auth.passwordsDoNotMatch')
    return
  }
  loading.value = true
  try {
    const result = await register(username.value, email.value, password.value, createTenant.value)
    if (result?.activation_required) {
      activationSuccess.value = true
    }
  } catch (err) {
    error.value = err?.response?.data?.error ?? err?.response?.data?.message ?? authError.value ?? t('auth.registrationFailed')
  } finally {
    loading.value = false
  }
}

async function handleDiscordLogin() {
  // Direct navigation to backend endpoint which returns HTTP 302 to Discord
  window.location.href = '/api/v2/auth/discord/login'
}
</script>
