<template>
  <div class="space-y-6">
    <WowCard>
      <div class="flex items-center gap-2 mb-4">
        <svg class="w-5 h-5 text-accent-gold flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        <div>
          <h2 class="text-sm font-semibold text-text-primary">{{ t('guild.expansions.title') }}</h2>
          <p class="text-xs text-text-muted mt-0.5">{{ t('guild.expansions.description') }}</p>
        </div>
      </div>

      <div v-if="loading" class="py-4 text-center">
        <div class="w-5 h-5 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin mx-auto" />
      </div>

      <div v-else-if="allExpansions.length === 0" class="py-6 text-center">
        <p class="text-sm text-text-muted">{{ t('guild.expansions.noExpansions') }}</p>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="exp in allExpansions"
          :key="exp.id"
          class="p-3 rounded-lg border transition-colors"
          :class="isEnabled(exp.id)
            ? 'bg-accent-gold/5 border-accent-gold/30'
            : 'bg-bg-tertiary border-border-default'"
        >
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-text-primary">{{ exp.name }}</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded border"
                :class="isEnabled(exp.id)
                  ? 'bg-green-600/15 text-green-400 border-green-600/40'
                  : 'bg-bg-secondary text-text-muted border-border-default'"
              >
                {{ isEnabled(exp.id) ? t('guild.expansions.enabled') : t('guild.expansions.disabled') }}
              </span>
              <span v-if="wouldAutoEnable(exp.id)" class="text-[10px] px-1.5 py-0.5 rounded bg-blue-600/15 text-blue-400 border border-blue-600/40">
                {{ t('guild.expansions.autoEnables') }}
              </span>
            </div>
            <div class="flex items-center gap-2">
              <WowButton
                v-if="!isEnabled(exp.id)"
                class="text-xs py-1 px-3"
                :loading="togglingId === exp.id"
                @click="doEnable(exp)"
              >{{ t('guild.expansions.enable') }}</WowButton>
              <WowButton
                v-else
                variant="danger"
                class="text-xs py-1 px-3"
                :loading="togglingId === exp.id"
                @click="doDisable(exp)"
              >{{ t('guild.expansions.disable') }}</WowButton>
            </div>
          </div>
          <div class="flex items-center gap-3 mt-1 text-xs text-text-muted">
            <span>{{ exp.slug }}</span>
            <span>{{ t('guild.expansions.order') }}: {{ exp.sort_order ?? 0 }}</span>
          </div>
        </div>
      </div>
    </WowCard>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import { useGuildStore } from '@/stores/guild'
import { useExpansionStore } from '@/stores/expansion'
import { useUiStore } from '@/stores/ui'
import * as guildExpansionsApi from '@/api/guild_expansions'

const guildStore = useGuildStore()
const expansionStore = useExpansionStore()
const uiStore = useUiStore()
const { t } = useI18n()

const loading = ref(false)
const enabledIds = ref(new Set())
const togglingId = ref(null)

const allExpansions = computed(() =>
  [...expansionStore.expansions].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
)

function isEnabled(id) {
  return enabledIds.value.has(id)
}

function wouldAutoEnable(id) {
  if (isEnabled(id)) return false
  const exp = allExpansions.value.find(e => e.id === id)
  if (!exp) return false
  return allExpansions.value.some(
    e => e.sort_order < exp.sort_order && !isEnabled(e.id)
  )
}

async function loadData() {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  loading.value = true
  try {
    if (expansionStore.expansions.length === 0) {
      await expansionStore.fetchExpansions(true)
    }
    const data = await guildExpansionsApi.getGuildExpansions(guildId)
    enabledIds.value = new Set((data.expansions || []).map(e => e.expansion_id))
  } catch {
    uiStore.showToast(t('guild.expansions.failedToLoad'), 'error')
  }
  loading.value = false
}

async function doEnable(exp) {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  togglingId.value = exp.id
  try {
    const data = await guildExpansionsApi.enableExpansion(guildId, exp.id)
    enabledIds.value = new Set((data.expansions || []).map(e => e.expansion_id))
    uiStore.showToast(t('guild.expansions.enabledToast', { name: exp.name }), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || t('guild.expansions.failedToEnable'), 'error')
  }
  togglingId.value = null
}

async function doDisable(exp) {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  togglingId.value = exp.id
  try {
    const data = await guildExpansionsApi.disableExpansion(guildId, exp.id)
    enabledIds.value = new Set((data.expansions || []).map(e => e.expansion_id))
    uiStore.showToast(t('guild.expansions.disabledToast', { name: exp.name }), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || t('guild.expansions.failedToDisable'), 'error')
  }
  togglingId.value = null
}

onMounted(loadData)
</script>
