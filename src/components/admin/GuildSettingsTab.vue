<template>
  <div class="space-y-6">
    <!-- Guild info form -->
    <WowCard>
      <h2 class="wow-heading text-base mb-4">Guild Information</h2>

      <div v-if="loading" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>

      <form v-else @submit.prevent="saveGuild" class="space-y-4 max-w-lg">
        <div>
          <label class="block text-xs text-text-muted mb-1">Guild Name *</label>
          <input v-model="form.name" required :disabled="isWarmaneSource" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none disabled:opacity-60 disabled:cursor-not-allowed" />
          <p v-if="isWarmaneSource" class="text-[10px] text-text-muted mt-1">Name is locked for Warmane-sourced guilds.</p>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Realm *</label>
          <select v-model="form.realm" required :disabled="isWarmaneSource" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none disabled:opacity-60 disabled:cursor-not-allowed">
            <option value="">Select realm…</option>
            <option v-for="r in warmaneRealms" :key="r" :value="r">{{ r }}</option>
          </select>
          <p v-if="isWarmaneSource" class="text-[10px] text-text-muted mt-1">Realm is locked for Warmane-sourced guilds.</p>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Description</label>
          <textarea v-model="form.description" rows="3" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none resize-none" />
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Guild Timezone</label>
          <select v-model="form.timezone" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option v-for="tz in timezoneOptions" :key="tz" :value="tz">{{ tz }}</option>
          </select>
          <p class="text-[10px] text-text-muted mt-1">All raid times will be displayed in this timezone by default.</p>
        </div>
        <div v-if="saveError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ saveError }}</div>
        <WowButton type="submit" :loading="saving">Save Changes</WowButton>
      </form>
    </WowCard>

    <!-- Warmane Guild Info (only for Warmane-sourced guilds) -->
    <WowCard v-if="isWarmaneSource">
      <div class="flex items-center justify-between mb-4">
        <h2 class="wow-heading text-base">Warmane Guild Info</h2>
        <div class="flex items-center gap-3">
          <span v-if="lastRefreshed" class="text-[10px] text-text-muted">
            Last refreshed: {{ lastRefreshed }}
          </span>
          <WowButton
            v-if="canManualRefresh"
            variant="secondary"
            class="text-xs py-1 px-3"
            :loading="fetchingWarmane"
            @click="fetchWarmaneRoster"
          >🔄 Refresh</WowButton>
        </div>
      </div>

      <div v-if="fetchingWarmane && !warmaneGuildData" class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="warmaneError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ warmaneError }}</div>

      <div v-else-if="warmaneGuildData" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Left column: Guild Info -->
        <div class="space-y-4">
          <h3 class="text-sm font-semibold text-accent-gold uppercase tracking-wider">Guild Details</h3>
          <div class="space-y-3">
            <div class="flex items-center gap-3">
              <span class="text-xs text-text-muted w-24 flex-shrink-0">Guild Name</span>
              <span class="text-sm text-text-primary font-medium">{{ warmaneGuildData.name }}</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-xs text-text-muted w-24 flex-shrink-0">Realm</span>
              <span class="text-sm text-text-primary">{{ warmaneGuildData.realm }}</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-xs text-text-muted w-24 flex-shrink-0">Faction</span>
              <span v-if="warmaneGuildData.faction" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold"
                :class="warmaneGuildData.faction === 'Alliance' ? 'bg-blue-900/50 text-blue-300 border border-blue-600' : 'bg-red-900/50 text-red-300 border border-red-600'"
              >
                <span>{{ warmaneGuildData.faction === 'Alliance' ? '🛡️' : '⚔️' }}</span>
                {{ warmaneGuildData.faction }}
              </span>
              <span v-else class="text-sm text-text-muted">Unknown</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-xs text-text-muted w-24 flex-shrink-0">Members</span>
              <span class="text-sm text-text-primary font-medium">{{ warmaneGuildData.member_count ?? warmaneGuildData.roster?.length ?? 0 }}</span>
            </div>
          </div>

          <!-- Class distribution -->
          <div v-if="classDistribution.length" class="mt-4">
            <h4 class="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Class Distribution</h4>
            <div class="grid grid-cols-2 gap-1.5">
              <div v-for="cd in classDistribution" :key="cd.name" class="flex items-center gap-2 text-xs">
                <img :src="getClassIcon(cd.name)" :alt="cd.name" class="w-4 h-4 rounded-sm" />
                <span :style="{ color: getClassColor(cd.name) }">{{ cd.name }}</span>
                <span class="text-text-muted ml-auto">{{ cd.count }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Right column: Member Roster -->
        <div>
          <h3 class="text-sm font-semibold text-accent-gold uppercase tracking-wider mb-3">Member Roster ({{ warmaneGuildData.roster?.length ?? 0 }})</h3>
          <div v-if="warmaneGuildData.roster?.length" class="overflow-x-auto max-h-96 overflow-y-auto rounded border border-border-default">
            <table class="w-full text-xs">
              <thead class="sticky top-0 z-10">
                <tr class="bg-bg-tertiary border-b border-border-default">
                  <th class="text-left px-3 py-2 text-text-muted uppercase">Character</th>
                  <th class="text-left px-3 py-2 text-text-muted uppercase">Level</th>
                  <th class="text-left px-3 py-2 text-text-muted uppercase">Race</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-default">
                <tr v-for="ch in warmaneGuildData.roster" :key="ch.name" class="hover:bg-bg-tertiary/50 transition-colors">
                  <td class="px-3 py-1.5">
                    <div class="flex items-center gap-2">
                      <img :src="getClassIcon(ch.class_name)" :alt="ch.class_name" class="w-5 h-5 rounded-sm flex-shrink-0" />
                      <span class="font-medium" :style="{ color: getClassColor(ch.class_name) }">{{ ch.name }}</span>
                    </div>
                  </td>
                  <td class="px-3 py-1.5 text-text-muted">{{ ch.level }}</td>
                  <td class="px-3 py-1.5 text-text-muted">{{ ch.race }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="text-center py-8 text-text-muted text-sm">No roster data available.</div>
        </div>
      </div>
    </WowCard>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
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

const guildStore = useGuildStore()
const authStore = useAuthStore()
const uiStore = useUiStore()
const { getClassIcon, getClassColor } = useWowIcons()
const permissions = usePermissions()

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
  try {
    warmaneGuildData.value = await guildsApi.getWarmaneRoster(guildStore.currentGuild.id)
    lastRefreshed.value = new Date().toLocaleTimeString()
  } catch (err) {
    warmaneError.value = err?.response?.data?.error ?? err?.response?.data?.message ?? 'Could not fetch roster from Warmane'
  } finally {
    fetchingWarmane.value = false
  }
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
