<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-6 w-full max-w-3xl mx-auto">
      <!-- Header -->
      <div class="flex items-center gap-3">
        <RouterLink to="/dashboard" class="p-1.5 rounded-lg bg-bg-tertiary border border-border-default text-text-muted hover:text-accent-gold hover:border-border-gold transition-colors">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </RouterLink>
        <div class="flex-1">
          <h1 class="wow-heading text-xl sm:text-2xl">{{ t('guild.discoverTitle') }}</h1>
          <p class="text-xs text-text-muted mt-0.5">{{ t('guild.discoverSubtitle') }}</p>
        </div>
      </div>

      <div v-if="loading" class="py-8 text-center">
        <div class="w-6 h-6 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin mx-auto mb-2" />
        <p class="text-sm text-text-muted">{{ t('common.labels.loading') }}</p>
      </div>

      <div v-else-if="guilds.length === 0" class="py-12 text-center">
        <svg class="w-12 h-12 text-text-muted/30 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <p class="text-sm text-text-muted">{{ t('guild.noGuildsFound') }}</p>
      </div>

      <div v-else class="space-y-3">
        <WowCard v-for="g in guilds" :key="g.id">
          <div class="flex items-center justify-between gap-4">
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-10 h-10 rounded-lg bg-bg-secondary border border-border-default flex items-center justify-center text-sm text-accent-gold font-bold uppercase flex-shrink-0">
                {{ g.name[0] }}
              </div>
              <div class="min-w-0">
                <h3 class="text-sm font-semibold text-text-primary truncate">{{ g.name }}</h3>
                <div class="flex items-center gap-2 text-xs text-text-muted">
                  <span>{{ g.realm_name }}</span>
                  <span v-if="g.faction" class="px-1.5 py-0.5 rounded text-[10px] font-medium uppercase"
                    :class="g.faction === 'Alliance' ? 'bg-blue-900/30 text-blue-300 border border-blue-700/50' : 'bg-red-900/30 text-red-300 border border-red-700/50'">
                    {{ g.faction }}
                  </span>
                </div>
              </div>
            </div>
            <div class="flex-shrink-0">
              <span v-if="g.is_member" class="text-xs text-green-400 font-medium">{{ t('guild.alreadyMember') }}</span>
              <span v-else-if="g.has_pending_application" class="text-xs text-yellow-400 font-medium">{{ t('guild.applicationPending') }}</span>
              <WowButton v-else @click="doApply(g)" :loading="applyingId === g.id" class="text-xs">
                {{ t('guild.applyToJoin') }}
              </WowButton>
            </div>
          </div>
        </WowCard>
      </div>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import { useUiStore } from '@/stores/ui'
import * as guildsApi from '@/api/guilds'

const { t } = useI18n()
const uiStore = useUiStore()

const loading = ref(true)
const guilds = ref([])
const applyingId = ref(null)

onMounted(async () => {
  try {
    const { data } = await guildsApi.discoverGuilds()
    guilds.value = data
  } catch { /* ignore */ }
  loading.value = false
})

async function doApply(guild) {
  applyingId.value = guild.id
  try {
    await guildsApi.applyToGuild(guild.id)
    guild.has_pending_application = true
    uiStore.showToast(t('guild.applicationSent'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || 'Error', 'error')
  }
  applyingId.value = null
}
</script>
