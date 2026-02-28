<template>
  <div class="min-h-screen bg-bg-primary flex items-center justify-center p-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <img
          :src="logoIcon"
          alt="Raid Calendar"
          class="w-20 h-20 rounded-xl border-2 border-border-gold mx-auto mb-4 shadow-gold"
        />
        <h1 class="wow-heading text-2xl mb-1">Raid Calendar</h1>
        <p class="text-text-muted text-sm">Create your account</p>
      </div>

      <WowCard :gold="true">
        <h2 class="text-lg font-semibold text-text-primary mb-6">Register</h2>

        <div v-if="error" class="mb-4 p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">
          {{ error }}
        </div>

        <form @submit.prevent="handleRegister" class="space-y-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">Username</label>
            <input
              v-model="username"
              type="text"
              autocomplete="username"
              required
              minlength="3"
              placeholder="YourUsername"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50 transition-colors"
            />
          </div>

          <div>
            <label class="block text-xs text-text-muted mb-1">Email</label>
            <input
              v-model="email"
              type="email"
              autocomplete="email"
              required
              placeholder="you@example.com"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50 transition-colors"
            />
          </div>

          <div>
            <label class="block text-xs text-text-muted mb-1">Password</label>
            <input
              v-model="password"
              type="password"
              autocomplete="new-password"
              required
              minlength="8"
              placeholder="Min. 8 characters"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50 transition-colors"
            />
          </div>

          <div>
            <label class="block text-xs text-text-muted mb-1">Confirm Password</label>
            <input
              v-model="confirmPassword"
              type="password"
              autocomplete="new-password"
              required
              placeholder="Repeat password"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50 transition-colors"
            />
          </div>

          <WowButton type="submit" :loading="loading" class="w-full mt-2">
            Create Account
          </WowButton>
        </form>

        <p class="text-center text-sm text-text-muted mt-6">
          Already have an account?
          <RouterLink to="/login" class="text-accent-gold hover:text-yellow-400 transition-colors">
            Sign In
          </RouterLink>
        </p>
      </WowCard>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { useWowIcons } from '@/composables/useWowIcons'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'

const { getRaidIcon } = useWowIcons()
const logoIcon = getRaidIcon('icc')

const { register, authError } = useAuth()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref(null)
const loading = ref(false)

async function handleRegister() {
  error.value = null
  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match'
    return
  }
  loading.value = true
  try {
    await register(username.value, email.value, password.value)
  } catch (err) {
    error.value = err?.response?.data?.message ?? authError.value ?? 'Registration failed.'
  } finally {
    loading.value = false
  }
}
</script>
