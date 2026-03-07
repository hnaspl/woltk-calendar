<template>
  <div class="space-y-6">
    <!-- No guild message -->
    <div v-if="noGuild" class="p-4 rounded-lg bg-blue-900/30 border border-blue-600 text-blue-300">
      {{ t('guild.settings.noGuild') }}
    </div>
    <template v-else>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Left column: Settings -->
      <div class="space-y-6">
        <!-- Guild info form -->
        <WowCard>
          <h2 class="wow-heading text-base mb-4">{{ t('guild.settings.information') }}</h2>

          <div v-if="loading" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
          <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>

          <form v-else @submit.prevent="saveGuild" class="space-y-4">
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.guildName') }}</label>
              <input v-model="form.name" required :disabled="isArmorySource" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none disabled:opacity-60 disabled:cursor-not-allowed" />
              <p v-if="isArmorySource" class="text-[10px] text-text-muted mt-1">{{ t('guild.settings.nameLocked') }}</p>
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.realmRequired') }}</label>
              <select v-model="form.realm" required :disabled="isArmorySource" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none disabled:opacity-60 disabled:cursor-not-allowed">
                <option value="">{{ t('common.fields.selectRealm') }}</option>
                <option v-for="r in guildRealmNames" :key="r" :value="r">{{ r }}</option>
              </select>
              <p v-if="isArmorySource" class="text-[10px] text-text-muted mt-1">{{ t('guild.settings.realmLocked') }}</p>
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('common.labels.description') }}</label>
              <textarea v-model="form.description" rows="3" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none resize-none" />
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('guild.settings.guildTimezone') }}</label>
              <select v-model="form.timezone" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
                <option v-for="tz in timezoneOptions" :key="tz" :value="tz">{{ tzLabel(tz) }}</option>
              </select>
              <p class="text-[10px] text-text-muted mt-1">{{ t('guild.settings.timezoneHelp') }}</p>
            </div>
            <div v-if="saveError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ saveError }}</div>
            <WowButton type="submit" :loading="saving">{{ t('common.fields.saveChanges') }}</WowButton>
          </form>
        </WowCard>

        <!-- Discord Integration -->
        <WowCard>
          <div class="flex items-center gap-2 mb-4">
            <img :src="discordIcon" class="w-5 h-5" alt="Discord" />
            <h2 class="wow-heading text-base">{{ t('guild.settings.discordIntegration') }}</h2>
          </div>
          <form @submit.prevent="saveDiscordWebhook" class="space-y-4">
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('guild.settings.webhookUrl') }}</label>
              <input
                v-model="discordWebhookUrl"
                type="url"
                placeholder="https://discord.com/api/webhooks/..."
                class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
              />
              <p class="text-[10px] text-text-muted mt-1">
                {{ t('guild.settings.webhookHelp') }}
              </p>
            </div>
            <div v-if="discordSaveError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ discordSaveError }}</div>
            <div v-if="discordSaveSuccess" class="p-3 rounded bg-green-900/30 border border-green-600 text-green-300 text-sm">{{ t('guild.settings.webhookSaved') }}</div>
            <WowButton type="submit" :loading="discordSaving">{{ t('common.fields.saveChanges') }}</WowButton>
          </form>
        </WowCard>

        <!-- Bench / Queue Settings -->
        <WowCard>
          <h2 class="wow-heading text-base mb-2">{{ t('guild.settings.benchSettings') }}</h2>
          <p class="text-text-muted text-xs mb-4">{{ t('guild.settings.benchSettingsHelp') }}</p>

          <form @submit.prevent="saveBenchSettings" class="space-y-4">
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('guild.settings.benchDisplayLimit') }}</label>
              <input
                v-model.number="benchDisplayLimit"
                type="number"
                min="1"
                max="100"
                class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
              />
              <p class="text-[10px] text-text-muted mt-1">{{ t('guild.settings.benchDisplayLimitHelp') }}</p>
            </div>
            <WowButton type="submit" :loading="benchSaving">{{ t('common.fields.saveChanges') }}</WowButton>
          </form>
        </WowCard>
      </div>

      <!-- Right column: Armory Guild Info -->
      <div v-if="isArmorySource" class="space-y-6">
        <WowCard>
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
            <div class="flex items-center gap-3">
              <img :src="getGuildIcon()" alt="Guild" class="w-8 h-8 rounded" />
              <h2 class="wow-heading text-lg">{{ t('guild.settings.armoryInfo') }}</h2>
            </div>
            <div class="flex items-center gap-3 sm:gap-4">
              <span v-if="lastRefreshed" class="text-xs text-text-muted">
                {{ t('guild.settings.lastRefreshed') }} {{ lastRefreshed }}
              </span>
              <WowButton
                v-if="canManualRefresh"
                variant="secondary"
                class="text-sm py-1.5 px-4 flex-shrink-0"
                :loading="fetchingArmory"
                @click="fetchArmoryRoster"
              >{{ t('guild.settings.refresh') }}</WowButton>
            </div>
          </div>

          <div v-if="fetchingArmory && !armoryGuildData" class="h-56 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
          <div v-else-if="armoryError" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ armoryError }}</div>

          <template v-else-if="armoryGuildData">
            <!-- Guild details -->
            <div class="space-y-6 mb-6">
              <h3 class="text-base font-semibold text-accent-gold uppercase tracking-wider">{{ t('guild.settings.guildDetails') }}</h3>

              <div class="bg-bg-secondary/50 rounded-lg border border-border-default p-5 space-y-4">
                <div class="flex items-center gap-3 sm:gap-4">
                  <span class="text-sm text-text-muted w-20 sm:w-28 flex-shrink-0 font-medium">{{ t('guild.settings.guildName') }}</span>
                  <span class="text-sm sm:text-base text-text-primary font-semibold">{{ armoryGuildData.name }}</span>
                </div>
                <div class="border-t border-border-default/50" />
                <div class="flex items-center gap-3 sm:gap-4">
                  <span class="text-sm text-text-muted w-20 sm:w-28 flex-shrink-0 font-medium">{{ t('common.fields.realmRequired').replace(' *', '') }}</span>
                  <span class="text-sm sm:text-base text-text-primary">{{ armoryGuildData.realm }}</span>
                </div>
                <div class="border-t border-border-default/50" />
                <div class="flex items-center gap-3 sm:gap-4">
                  <span class="text-sm text-text-muted w-20 sm:w-28 flex-shrink-0 font-medium">{{ t('common.fields.faction') }}</span>
                  <span v-if="armoryGuildData.faction" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold"
                    :class="armoryGuildData.faction === 'Alliance' ? 'bg-blue-900/50 text-blue-300 border border-blue-600' : 'bg-red-900/50 text-red-300 border border-red-600'"
                  >
                    <img :src="getFactionIcon(armoryGuildData.faction)" :alt="armoryGuildData.faction" class="w-6 h-6 rounded" />
                    {{ armoryGuildData.faction }}
                  </span>
                  <span v-else class="text-sm sm:text-base text-text-muted">{{ t('common.labels.unknown') }}</span>
                </div>
                <div class="border-t border-border-default/50" />
                <div class="flex items-center gap-3 sm:gap-4">
                  <span class="text-sm text-text-muted w-20 sm:w-28 flex-shrink-0 font-medium">{{ t('common.labels.members') }}</span>
                  <span class="text-sm sm:text-base text-text-primary font-semibold">{{ armoryGuildData.member_count ?? armoryGuildData.roster?.length ?? 0 }}</span>
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

            <!-- Member Roster -->
            <div>
              <h3 class="text-base font-semibold text-accent-gold uppercase tracking-wider mb-4">{{ t('guild.settings.memberRoster', { count: armoryGuildData.roster?.length ?? 0 }) }}</h3>
              <div v-if="armoryGuildData.roster?.length" class="overflow-x-auto max-h-[32rem] overflow-y-auto rounded-lg border border-border-default">
                <table class="w-full text-sm">
                  <thead class="sticky top-0 z-10">
                    <tr class="bg-bg-tertiary border-b border-border-default">
                      <th class="text-left px-4 py-3 text-xs text-text-muted uppercase font-semibold tracking-wider">{{ t('common.fields.character') }}</th>
                      <th class="text-left px-4 py-3 text-xs text-text-muted uppercase font-semibold tracking-wider">{{ t('common.fields.level') }}</th>
                      <th class="hidden sm:table-cell text-left px-4 py-3 text-xs text-text-muted uppercase font-semibold tracking-wider">{{ t('guild.settings.race') }}</th>
                      <th class="text-center px-4 py-3 text-xs text-text-muted uppercase font-semibold tracking-wider w-20"></th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-border-default/60">
                    <tr v-for="ch in armoryGuildData.roster" :key="ch.name" class="hover:bg-bg-tertiary/50 transition-colors">
                      <td class="px-4 py-2.5">
                        <div class="flex items-center gap-3">
                          <img :src="getClassIcon(ch.class_name)" :alt="ch.class_name" class="w-7 h-7 rounded flex-shrink-0" />
                          <span class="font-semibold text-sm" :style="{ color: getClassColor(ch.class_name) }">{{ ch.name }}</span>
                        </div>
                      </td>
                      <td class="px-4 py-2.5 text-text-muted font-medium">{{ ch.level }}</td>
                      <td class="hidden sm:table-cell px-4 py-2.5 text-text-muted">{{ ch.race }}</td>
                      <td class="px-4 py-2.5 text-center">
                        <WowButton variant="secondary" class="text-xs py-1 px-2.5" @click="openCharDetail(ch)">
                          🔍
                        </WowButton>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="text-center py-12 text-text-muted text-sm bg-bg-secondary/30 rounded-lg border border-border-default">{{ t('guild.settings.noRosterData') }}</div>
            </div>
          </template>
        </WowCard>
      </div>
    </div>
    </template>

    <!-- Character Detail Modal -->
    <CharacterDetailModal
      v-model="showCharDetailModal"
      :character="charDetailTarget"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import CharacterDetailModal from '@/components/common/CharacterDetailModal.vue'
import { useGuildStore } from '@/stores/guild'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import { useWowIcons } from '@/composables/useWowIcons'
import { usePermissions } from '@/composables/usePermissions'
import * as guildsApi from '@/api/guilds'
import * as adminApi from '@/api/admin'
import * as guildRealmsApi from '@/api/guild_realms'
import * as armoryLookupApi from '@/api/armory_lookup'
import { useTimezone } from '@/composables/useTimezone'
import discordIcon from '@/assets/icons/discord/discord-mark-white.svg'

const { t } = useI18n()
const guildStore = useGuildStore()
const authStore = useAuthStore()
const toast = useToast()
const { getClassIcon, getClassColor, getFactionIcon, getGuildIcon } = useWowIcons()
const permissions = usePermissions()
const tzHelper = useTimezone()

const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const saveError = ref(null)
const noGuild = ref(false)
const form = reactive({ name: '', realm: '', description: '', timezone: 'Europe/Warsaw' })
const guildRealmNames = ref([])
const isArmorySource = ref(false)

// Discord webhook
const discordWebhookUrl = ref('')
const discordSaving = ref(false)
const discordSaveError = ref(null)
const discordSaveSuccess = ref(false)

// Bench settings
const benchDisplayLimit = ref(8)
const benchSaving = ref(false)

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

function tzLabel(tz) {
  const key = 'timezones.' + tz.replace(/\//g, '_').replace(/-/g, '_')
  const label = t(key)
  return label !== key ? label : tz
}

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
  noGuild.value = false
  try {
    const g = guildStore.currentGuild
    if (!g) {
      noGuild.value = true
      return
    }
    Object.assign(form, { name: g.name ?? '', realm: g.realm_name ?? '', description: g.description ?? '', timezone: g.timezone ?? 'Europe/Warsaw' })
    isArmorySource.value = !!g.armory_source
    discordWebhookUrl.value = (g.settings || {}).discord_webhook_url || ''
    benchDisplayLimit.value = parseInt((g.settings || {}).bench_display_limit, 10) || 8
    // Load guild-configured realms from API
    try {
      const data = await guildRealmsApi.getGuildRealms(g.id)
      const realmList = (data.realms || []).map(r => r.name)
      // Always include the current guild realm in the list
      if (g.realm_name && !realmList.includes(g.realm_name)) {
        realmList.push(g.realm_name)
      }
      guildRealmNames.value = realmList.sort()
    } catch {
      // Fallback: at least show the current realm
      guildRealmNames.value = g.realm_name ? [g.realm_name] : []
    }
  } catch {
    error.value = t('guildSettings.failedToLoad')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadGuildData()
  if (isArmorySource.value) {
    await fetchArmoryRoster()
    await loadAutoRefreshInterval()
  }
})

watch(
  () => guildStore.currentGuild?.id,
  async (newId, oldId) => {
    if (newId && newId !== oldId) {
      stopAutoRefresh()
      await loadGuildData()
      armoryGuildData.value = null
      armoryError.value = null
      if (isArmorySource.value) {
        await fetchArmoryRoster()
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
    toast.success(t('guildSettings.toasts.settingsSaved'))
  } catch (err) {
    saveError.value = err?.response?.data?.message ?? 'Failed to save'
  } finally {
    saving.value = false
  }
}

async function saveDiscordWebhook() {
  discordSaveError.value = null
  discordSaveSuccess.value = false
  discordSaving.value = true
  try {
    const g = guildStore.currentGuild
    const currentSettings = g.settings || {}
    const newSettings = { ...currentSettings, discord_webhook_url: discordWebhookUrl.value.trim() }
    await guildsApi.updateGuild(g.id, { settings_json: JSON.stringify(newSettings) })
    // Update local guild store
    g.settings = newSettings
    discordSaveSuccess.value = true
    setTimeout(() => { discordSaveSuccess.value = false }, 3000)
  } catch (err) {
    discordSaveError.value = err?.response?.data?.message ?? 'Failed to save'
  } finally {
    discordSaving.value = false
  }
}

async function saveBenchSettings() {
  benchSaving.value = true
  try {
    const g = guildStore.currentGuild
    const currentSettings = g.settings || {}
    const limit = Math.max(1, Math.min(100, benchDisplayLimit.value || 8))
    const newSettings = { ...currentSettings, bench_display_limit: limit }
    await guildsApi.updateGuild(g.id, { settings_json: JSON.stringify(newSettings) })
    g.settings = newSettings
    benchDisplayLimit.value = limit
    toast.success(t('guildSettings.toasts.settingsSaved'))
  } catch (err) {
    toast.error(err?.response?.data?.error ?? 'Failed to save')
  } finally {
    benchSaving.value = false
  }
}

// Armory guild info
const fetchingArmory = ref(false)
const armoryError = ref(null)
const armoryGuildData = ref(null)
const lastRefreshed = ref(null)
let autoRefreshTimer = null

// Character detail modal
const showCharDetailModal = ref(false)
const charDetailTarget = ref(null)

const fetchingCharDetail = ref(false)

async function openCharDetail(ch) {
  const realm = ch.realm || guildStore.currentGuild?.realm_name || ''
  // Show modal immediately with basic roster data
  charDetailTarget.value = {
    name: ch.name,
    class_name: ch.class_name,
    realm_name: realm,
    default_role: ch.role || '',
    primary_spec: ch.spec || '',
    secondary_spec: ch.secondary_spec || '',
    armory_url: ch.armory_url || '',
    level: ch.level,
    metadata: {
      level: ch.level,
      race: ch.race,
      faction: ch.faction,
      guild: armoryGuildData.value?.name,
      gear_score: ch.gear_score,
      achievement_points: ch.achievement_points,
      honorable_kills: ch.honorable_kills,
      professions: ch.professions || [],
      talents: ch.talents || [],
      equipment: ch.equipment || [],
    },
  }
  showCharDetailModal.value = true

  // Fetch full character data from armory (equipment, talents, etc.)
  if (realm && ch.name && guildStore.currentGuild?.id) {
    fetchingCharDetail.value = true
    try {
      const fullData = await armoryLookupApi.lookupCharacter(realm, ch.name, guildStore.currentGuild.id)
      if (fullData) {
        charDetailTarget.value = {
          name: fullData.name || ch.name,
          class_name: fullData.class_name || ch.class_name,
          realm_name: fullData.realm || realm,
          default_role: ch.role || '',
          primary_spec: ch.spec || '',
          secondary_spec: ch.secondary_spec || '',
          armory_url: fullData.armory_url || ch.armory_url || '',
          level: fullData.level || ch.level,
          metadata: {
            level: fullData.level || ch.level,
            race: fullData.race || ch.race,
            faction: fullData.faction || ch.faction,
            guild: fullData.guild || armoryGuildData.value?.name,
            gear_score: fullData.gear_score || ch.gear_score,
            achievement_points: fullData.achievement_points || ch.achievement_points,
            honorable_kills: fullData.honorable_kills || ch.honorable_kills,
            professions: fullData.professions || ch.professions || [],
            talents: fullData.talents || ch.talents || [],
            equipment: fullData.equipment || ch.equipment || [],
          },
        }
      }
    } catch {
      // Keep basic roster data on failure — modal already visible
    } finally {
      fetchingCharDetail.value = false
    }
  }
}

async function fetchArmoryRoster() {
  if (!guildStore.currentGuild?.id) return
  armoryError.value = null
  fetchingArmory.value = true
  const maxAttempts = 2
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      armoryGuildData.value = await guildsApi.getArmoryRoster(guildStore.currentGuild.id)
      lastRefreshed.value = tzHelper.formatGuildTime(new Date().toISOString(), { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
      armoryError.value = null
      break
    } catch (err) {
      if (attempt < maxAttempts) {
        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, 2000))
        continue
      }
      armoryError.value = err?.response?.data?.error ?? err?.response?.data?.message ?? 'Could not fetch roster from armory'
    }
  }
  fetchingArmory.value = false
}

// Class distribution computed from roster
const classDistribution = computed(() => {
  const roster = armoryGuildData.value?.roster
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
    const intervalMin = parseInt(settings.autosync_interval_minutes, 10) || 60
    if (enabled && intervalMin > 0) {
      autoRefreshTimer = setInterval(() => {
        if (isArmorySource.value) fetchArmoryRoster()
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
