<template>
  <div class="space-y-6">
    <!-- Guild info form -->
    <WowCard>
      <h2 class="wow-heading text-base mb-4">{{ t('guild.settings.information') }}</h2>

      <div v-if="loading" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>

      <form v-else @submit.prevent="saveGuild" class="space-y-4 max-w-lg">
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('guild.settings.nameRequired') }}</label>
          <input v-model="form.name" required :disabled="isWarmaneSource" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none disabled:opacity-60 disabled:cursor-not-allowed" />
          <p v-if="isWarmaneSource" class="text-[10px] text-text-muted mt-1">{{ t('guild.settings.nameLocked') }}</p>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('guild.settings.realmRequired') }}</label>
          <select v-model="form.realm" required :disabled="isWarmaneSource" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none disabled:opacity-60 disabled:cursor-not-allowed">
            <option value="">{{ t('guild.settings.selectRealm') }}</option>
            <option v-for="r in warmaneRealms" :key="r" :value="r">{{ r }}</option>
          </select>
          <p v-if="isWarmaneSource" class="text-[10px] text-text-muted mt-1">{{ t('guild.settings.realmLocked') }}</p>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('guild.settings.description') }}</label>
          <textarea v-model="form.description" rows="3" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none resize-none" />
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('guild.settings.guildTimezone') }}</label>
          <select v-model="form.timezone" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option v-for="tz in timezoneOptions" :key="tz" :value="tz">{{ tz }}</option>
          </select>
          <p class="text-[10px] text-text-muted mt-1">{{ t('guild.settings.timezoneHelp') }}</p>
        </div>
        <div v-if="saveError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ saveError }}</div>
        <WowButton type="submit" :loading="saving">{{ t('guild.settings.saveChanges') }}</WowButton>
      </form>
    </WowCard>

    <!-- Warmane Guild Info (only for Warmane-sourced guilds) -->
    <WowCard v-if="isWarmaneSource">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div class="flex items-center gap-3">
          <img :src="getGuildIcon()" alt="Guild" class="w-8 h-8 rounded" />
          <h2 class="wow-heading text-lg">{{ t('guild.settings.warmaneInfo') }}</h2>
        </div>
        <div class="flex items-center gap-3 sm:gap-4">
          <span v-if="lastRefreshed" class="text-xs text-text-muted">
            {{ t('guild.settings.lastRefreshed') }} {{ lastRefreshed }}
          </span>
          <WowButton
            v-if="canManualRefresh"
            variant="secondary"
            class="text-sm py-1.5 px-4 flex-shrink-0"
            :loading="fetchingWarmane"
            @click="fetchWarmaneRoster"
          >{{ t('guild.settings.refresh') }}</WowButton>
        </div>
      </div>

      <div v-if="fetchingWarmane && !warmaneGuildData" class="h-56 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="warmaneError" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ warmaneError }}</div>

      <div v-else-if="warmaneGuildData" class="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8">
        <!-- Left column: Guild Info -->
        <div class="space-y-6">
          <h3 class="text-base font-semibold text-accent-gold uppercase tracking-wider">{{ t('guild.settings.guildDetails') }}</h3>

          <div class="bg-bg-secondary/50 rounded-lg border border-border-default p-5 space-y-4">
            <div class="flex items-center gap-3 sm:gap-4">
              <span class="text-sm text-text-muted w-20 sm:w-28 flex-shrink-0 font-medium">{{ t('guild.settings.guildName') }}</span>
              <span class="text-sm sm:text-base text-text-primary font-semibold">{{ warmaneGuildData.name }}</span>
            </div>
            <div class="border-t border-border-default/50" />
            <div class="flex items-center gap-3 sm:gap-4">
              <span class="text-sm text-text-muted w-20 sm:w-28 flex-shrink-0 font-medium">{{ t('guild.settings.realmRequired').replace(' *', '') }}</span>
              <span class="text-sm sm:text-base text-text-primary">{{ warmaneGuildData.realm }}</span>
            </div>
            <div class="border-t border-border-default/50" />
            <div class="flex items-center gap-3 sm:gap-4">
              <span class="text-sm text-text-muted w-20 sm:w-28 flex-shrink-0 font-medium">{{ t('guild.settings.faction') }}</span>
              <span v-if="warmaneGuildData.faction" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold"
                :class="warmaneGuildData.faction === 'Alliance' ? 'bg-blue-900/50 text-blue-300 border border-blue-600' : 'bg-red-900/50 text-red-300 border border-red-600'"
              >
                <img :src="getFactionIcon(warmaneGuildData.faction)" :alt="warmaneGuildData.faction" class="w-6 h-6 rounded" />
                {{ warmaneGuildData.faction }}
              </span>
              <span v-else class="text-sm sm:text-base text-text-muted">{{ t('common.labels.unknown') }}</span>
            </div>
            <div class="border-t border-border-default/50" />
            <div class="flex items-center gap-3 sm:gap-4">
              <span class="text-sm text-text-muted w-20 sm:w-28 flex-shrink-0 font-medium">{{ t('guild.settings.members') }}</span>
              <span class="text-sm sm:text-base text-text-primary font-semibold">{{ warmaneGuildData.member_count ?? warmaneGuildData.roster?.length ?? 0 }}</span>
            </div>
          </div>

          <!-- Class distribution -->
          <div v-if="classDistribution.length">
            <h4 class="text-sm font-semibold text-text-muted uppercase tracking-wider mb-3">{{ t('guild.settings.classDistribution') }}</h4>
            <div class="bg-bg-secondary/50 rounded-lg border border-border-default p-4">
              <div class="grid grid-cols-2 gap-3">
                <div v-for="cd in classDistribution" :key="cd.name" class="flex items-center gap-3 py-1">
                  <img :src="getClassIcon(cd.name)" :alt="cd.name" class="w-6 h-6 rounded flex-shrink-0" />
                  <span class="text-sm font-medium" :style="{ color: getClassColor(cd.name) }">{{ cd.name }}</span>
                  <span class="text-sm text-text-muted ml-auto font-medium">{{ cd.count }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right column: Member Roster -->
        <div>
          <h3 class="text-base font-semibold text-accent-gold uppercase tracking-wider mb-4">{{ t('guild.settings.memberRoster', { count: warmaneGuildData.roster?.length ?? 0 }) }}</h3>
          <div v-if="warmaneGuildData.roster?.length" class="overflow-x-auto max-h-[32rem] overflow-y-auto rounded-lg border border-border-default">
            <table class="w-full text-sm">
              <thead class="sticky top-0 z-10">
                <tr class="bg-bg-tertiary border-b border-border-default">
                  <th class="text-left px-4 py-3 text-xs text-text-muted uppercase font-semibold tracking-wider">{{ t('guild.settings.character') }}</th>
                  <th class="text-left px-4 py-3 text-xs text-text-muted uppercase font-semibold tracking-wider">{{ t('guild.settings.level') }}</th>
                  <th class="hidden sm:table-cell text-left px-4 py-3 text-xs text-text-muted uppercase font-semibold tracking-wider">{{ t('guild.settings.race') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-default/60">
                <tr v-for="ch in warmaneGuildData.roster" :key="ch.name" class="hover:bg-bg-tertiary/50 transition-colors">
                  <td class="px-4 py-2.5">
                    <div class="flex items-center gap-3">
                      <img :src="getClassIcon(ch.class_name)" :alt="ch.class_name" class="w-7 h-7 rounded flex-shrink-0" />
                      <span class="font-semibold text-sm" :style="{ color: getClassColor(ch.class_name) }">{{ ch.name }}</span>
                    </div>
                  </td>
                  <td class="px-4 py-2.5 text-text-muted font-medium">{{ ch.level }}</td>
                  <td class="hidden sm:table-cell px-4 py-2.5 text-text-muted">{{ ch.race }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="text-center py-12 text-text-muted text-sm bg-bg-secondary/30 rounded-lg border border-border-default">{{ t('guild.settings.noRosterData') }}</div>
        </div>
      </div>
    </WowCard>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import { useGuildStore } from '@/stores/guild'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useWowIcons } from '@/composables/useWowIcons'
import { usePermissions } from '@/composables/usePermissions'
import { WARMANE_REALMS } from '@/constants'
import * as guildsApi from '@/api/guilds'
import * as adminApi from '@/api/admin'
import { useTimezone } from '@/composables/useTimezone'

const { t } = useI18n()
const guildStore = useGuildStore()
const authStore = useAuthStore()
const uiStore = useUiStore()
const { getClassIcon, getClassColor, getFactionIcon, getGuildIcon } = useWowIcons()
const permissions = usePermissions()
const tzHelper = useTimezone()

const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const saveError = ref(null)
const form = reactive({ name: '', realm: '', description: '', timezone: 'Europe/Warsaw' })
const warmaneRealms = WARMANE_REALMS
const isWarmaneSource = ref(false)

const timezoneOptions = [
  'Europe/Warsaw', 'Europe/London', 'Europe/Paris', 'Europe/Berlin',
  'Europe/Madrid', 'Europe/Rome', 'Europe/Amsterdam', 'Europe/Brussels',
  'Europe/Vienna', 'Europe/Prague', 'Europe/Budapest', 'Europe/Bucharest',
  'Europe/Sofia', 'Europe/Athens', 'Europe/Helsinki', 'Europe/Stockholm',
  'Europe/Oslo', 'Europe/Copenhagen', 'Europe/Lisbon', 'Europe/Dublin',
  'Europe/Moscow', 'Europe/Kiev', 'Europe/Istanbul',
  'US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific',
  'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
  'America/Sao_Paulo', 'America/Argentina/Buenos_Aires',
  'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Seoul', 'Asia/Singapore',
  'Asia/Kolkata', 'Asia/Dubai',
  'Australia/Sydney', 'Australia/Melbourne', 'Pacific/Auckland',
  'UTC',
]

// Permission check: guild admin, guild creator, or global admin can manually refresh
const canManualRefresh = computed(() => {
  if (authStore.user?.is_admin) return true
  const guild = guildStore.currentGuild
  if (guild && guild.created_by === authStore.user?.id) return true
  return permissions.can('update_guild_settings')
})

async function loadGuildData() {
  loading.value = true
  error.value = null
  try {
    const g = guildStore.currentGuild
    if (g) {
      Object.assign(form, { name: g.name ?? '', realm: g.realm_name ?? '', description: g.description ?? '', timezone: g.timezone ?? 'Europe/Warsaw' })
      isWarmaneSource.value = !!g.warmane_source
    }
  } catch {
    error.value = 'Failed to load guild settings'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadGuildData()
  if (isWarmaneSource.value) {
    await fetchWarmaneRoster()
    await loadAutoRefreshInterval()
  }
})

watch(
  () => guildStore.currentGuild?.id,
  async (newId, oldId) => {
    if (newId && newId !== oldId) {
      stopAutoRefresh()
      await loadGuildData()
      warmaneGuildData.value = null
      warmaneError.value = null
      if (isWarmaneSource.value) {
        await fetchWarmaneRoster()
        await loadAutoRefreshInterval()
      }
    }
  }
)

async function saveGuild() {
  saveError.value = null
  saving.value = true
  try {
    const updated = await guildsApi.updateGuild(guildStore.currentGuild.id, {
      name: form.name,
      realm_name: form.realm,
      timezone: form.timezone,
    })
    guildStore.currentGuild = updated
    uiStore.showToast('Guild settings saved', 'success')
  } catch (err) {
    saveError.value = err?.response?.data?.message ?? 'Failed to save'
  } finally {
    saving.value = false
  }
}

// Warmane guild info
const fetchingWarmane = ref(false)
const warmaneError = ref(null)
const warmaneGuildData = ref(null)
const lastRefreshed = ref(null)
let autoRefreshTimer = null

async function fetchWarmaneRoster() {
  if (!guildStore.currentGuild?.id) return
  warmaneError.value = null
  fetchingWarmane.value = true
  const maxAttempts = 2
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      warmaneGuildData.value = await guildsApi.getWarmaneRoster(guildStore.currentGuild.id)
      lastRefreshed.value = tzHelper.formatGuildTime(new Date().toISOString(), { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
      warmaneError.value = null
      break
    } catch (err) {
      if (attempt < maxAttempts) {
        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, 2000))
        continue
      }
      warmaneError.value = err?.response?.data?.error ?? err?.response?.data?.message ?? 'Could not fetch roster from Warmane'
    }
  }
  fetchingWarmane.value = false
}

// Class distribution computed from roster
const classDistribution = computed(() => {
  const roster = warmaneGuildData.value?.roster
  if (!roster?.length) return []
  const counts = {}
  for (const ch of roster) {
    const cls = ch.class_name || 'Unknown'
    counts[cls] = (counts[cls] || 0) + 1
  }
  return Object.entries(counts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
})

// Auto-refresh using system settings interval
async function loadAutoRefreshInterval() {
  stopAutoRefresh()
  try {
    const settings = await adminApi.getSystemSettings()
    const enabled = settings.autosync_enabled === 'true'
    const intervalMin = parseInt(settings.autosync_interval_minutes) || 60
    if (enabled && intervalMin > 0) {
      autoRefreshTimer = setInterval(() => {
        if (isWarmaneSource.value) fetchWarmaneRoster()
      }, intervalMin * 60 * 1000)
    }
  } catch {
    // If we can't load system settings (non-admin), skip auto-refresh
  }
}

function stopAutoRefresh() {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
}

onUnmounted(() => {
  stopAutoRefresh()
})
</script>
