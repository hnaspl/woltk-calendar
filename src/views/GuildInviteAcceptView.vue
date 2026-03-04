<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 flex items-center justify-center min-h-[60vh]">
      <WowCard class="w-full max-w-md text-center">
        <!-- Loading -->
        <div v-if="status === 'loading'" class="py-8">
          <div class="w-8 h-8 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin mx-auto mb-4" />
          <p class="text-sm text-text-muted">{{ t('guild.inviteAccepting') }}</p>
        </div>
        <!-- Accepted -->
        <div v-else-if="status === 'accepted'" class="py-8">
          <svg class="w-12 h-12 text-green-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h2 class="text-lg font-semibold text-text-primary mb-1">{{ t('guild.inviteAccepted') }}</h2>
          <p v-if="guildName" class="text-sm text-text-muted mb-4">{{ guildName }}</p>
          <WowButton @click="goToDashboard">{{ t('common.buttons.continue') }}</WowButton>
        </div>
        <!-- Error -->
        <div v-else-if="status === 'error'" class="py-8">
          <svg class="w-12 h-12 text-red-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h2 class="text-lg font-semibold text-text-primary mb-1">{{ t('guild.inviteError') }}</h2>
          <p class="text-sm text-red-400 mb-4">{{ errorMsg }}</p>
          <WowButton @click="goToDashboard">{{ t('common.buttons.continue') }}</WowButton>
        </div>
        <!-- Pending — show accept button -->
        <div v-else class="py-8">
          <svg class="w-12 h-12 text-accent-gold mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <h2 class="text-lg font-semibold text-text-primary mb-1">{{ t('guild.invitePending') }}</h2>
          <p v-if="guildName" class="text-sm text-text-muted mb-4">{{ guildName }}</p>
          <WowButton @click="doAccept" :loading="accepting">{{ t('guild.acceptInvite') }}</WowButton>
        </div>
      </WowCard>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import * as guildsApi from '@/api/guilds'
import { useGuildStore } from '@/stores/guild'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const guildStore = useGuildStore()

const status = ref('pending')
const accepting = ref(false)
const errorMsg = ref('')
const guildName = ref('')

onMounted(async () => {
  // Auto-accept on mount
  await doAccept()
})

async function doAccept() {
  const token = route.params.token
  if (!token) {
    status.value = 'error'
    errorMsg.value = 'No token provided'
    return
  }
  accepting.value = true
  status.value = 'loading'
  try {
    const { data } = await guildsApi.acceptGuildInvite(token)
    guildName.value = data.guild_name || ''
    status.value = 'accepted'
    await guildStore.fetchGuilds()
  } catch (err) {
    status.value = 'error'
    errorMsg.value = err?.response?.data?.error || t('guild.inviteError')
  }
  accepting.value = false
}

function goToDashboard() {
  router.push('/dashboard')
}
</script>
