<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="wow-heading text-xl sm:text-2xl">{{ t('common.labels.dashboard') }}</h1>
          <p class="text-text-muted text-sm mt-0.5">
            {{ t('dashboard.welcome', { name: authStore.user?.username }) }}
            <span v-if="tenantStore.activeTenant" class="text-accent-gold/70"> · {{ tenantStore.activeTenant.name }}</span>
          </p>
        </div>
        <RouterLink to="/calendar">
          <WowButton variant="secondary">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
            </svg>
            {{ t('common.labels.calendar') }}
          </WowButton>
        </RouterLink>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div v-for="i in 4" :key="i" class="h-24 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      </div>

      <!-- Stats row -->
      <div v-else class="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
        <WowCard class="text-center">
          <div class="text-2xl sm:text-3xl font-bold text-accent-gold">{{ upcomingEvents.length }}</div>
          <div class="text-xs text-text-muted mt-1">{{ t('dashboard.upcomingRaids') }}</div>
        </WowCard>
        <WowCard class="text-center">
          <div class="text-2xl sm:text-3xl font-bold text-green-400">{{ myGoingCount }}</div>
          <div class="text-xs text-text-muted mt-1">{{ t('common.labels.inLineup') }}</div>
        </WowCard>
        <WowCard class="text-center">
          <div class="text-2xl sm:text-3xl font-bold text-yellow-400">{{ myBenchCount }}</div>
          <div class="text-xs text-text-muted mt-1">{{ t('dashboard.onBench') }}</div>
        </WowCard>
        <WowCard class="text-center">
          <div class="text-2xl sm:text-3xl font-bold text-red-400">{{ missingResponseCount }}</div>
          <div class="text-xs text-text-muted mt-1">{{ t('dashboard.noResponse') }}</div>
        </WowCard>
      </div>

      <!-- Guild & Tenant info -->
      <div v-if="!loading && guildStore.currentGuild" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-4">
        <WowCard>
          <div class="flex items-center gap-3">
            <span class="text-2xl">⚔️</span>
            <div>
              <div class="text-sm font-semibold text-text-primary">{{ guildStore.currentGuild.name }}</div>
              <div class="text-xs text-text-muted">{{ guildStore.currentGuild.realm_name }}</div>
            </div>
          </div>
          <div class="mt-3 grid grid-cols-2 gap-2 text-xs">
            <div class="bg-bg-tertiary rounded p-2 text-center">
              <div class="text-lg font-bold text-accent-gold">{{ guildStore.members?.length ?? 0 }}</div>
              <div class="text-text-muted">{{ t('common.labels.members') }}</div>
            </div>
            <div class="bg-bg-tertiary rounded p-2 text-center">
              <div class="text-lg font-bold text-purple-400">{{ totalEvents }}</div>
              <div class="text-text-muted">{{ t('dashboard.totalEvents') }}</div>
            </div>
          </div>
        </WowCard>
        <WowCard>
          <div class="flex items-center gap-2 mb-2">
            <span class="text-lg">📊</span>
            <span class="text-sm font-semibold text-text-primary">{{ t('dashboard.raidActivity') }}</span>
          </div>
          <div class="space-y-2">
            <div class="flex items-center justify-between text-xs">
              <span class="text-text-muted">{{ t('dashboard.thisWeek') }}</span>
              <span class="text-text-primary font-medium">{{ eventsThisWeek }} {{ t('dashboard.raids') }}</span>
            </div>
            <div class="flex items-center justify-between text-xs">
              <span class="text-text-muted">{{ t('dashboard.nextWeek') }}</span>
              <span class="text-text-primary font-medium">{{ eventsNextWeek }} {{ t('dashboard.raids') }}</span>
            </div>
            <div class="flex items-center justify-between text-xs">
              <span class="text-text-muted">{{ t('dashboard.averageSignups') }}</span>
              <span class="text-text-primary font-medium">{{ avgSignupsPerRaid }}</span>
            </div>
          </div>
        </WowCard>
        <WowCard>
          <div class="flex items-center gap-2 mb-2">
            <span class="text-lg">⏳</span>
            <span class="text-sm font-semibold text-text-primary">{{ t('dashboard.benchQueue') }}</span>
          </div>
          <div v-if="benchedSignups.length === 0" class="text-xs text-text-muted py-2">
            {{ t('dashboard.noPlayersOnBench') }}
          </div>
          <div v-else class="space-y-1.5">
            <div v-for="su in benchedSignups.slice(0, 5)" :key="su.id" class="flex items-center gap-2 text-xs">
              <ClassBadge v-if="su.character?.class_name" :class-name="su.character.class_name" />
              <span class="text-text-primary truncate flex-1">{{ su.character?.name ?? t('dashboard.signedUp') }}</span>
              <span class="text-yellow-400 text-[10px]">{{ t('dashboard.queue') }} #{{ su.bench_info?.queue_position ?? '?' }}</span>
            </div>
            <p v-if="benchedSignups.length > 5" class="text-[10px] text-text-muted">
              +{{ benchedSignups.length - 5 }} {{ t('dashboard.more') }}
            </p>
          </div>
        </WowCard>
      </div>

      <!-- Pending Replacement Requests -->
      <div v-if="replacementRequests.length > 0" class="space-y-3">
        <h2 class="wow-heading text-lg">⚡ {{ t('dashboard.pendingSwaps') }}</h2>
        <div v-for="req in replacementRequests" :key="req.id">
          <WowCard class="border-blue-700 bg-blue-900/10">
            <div class="space-y-2">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-blue-300 text-xs font-semibold">{{ t('dashboard.swapRequested') }}</span>
                <span v-if="req.event_title" class="text-xs text-text-muted">·</span>
                <RouterLink
                  v-if="req.event_id && req.guild_id"
                  :to="`/raids/${req.event_id}`"
                  class="text-xs text-accent-gold hover:underline"
                >{{ req.event_title ?? 'Raid' }}</RouterLink>
                <span v-if="req.starts_at_utc" class="text-xs text-text-muted">{{ formatDateTime(req.starts_at_utc) }}</span>
              </div>
              <p class="text-text-muted text-xs">
                <strong class="text-text-primary">{{ req.requester_name }}</strong>
                {{ t('dashboard.wantsToReplace') }}
                <strong class="text-text-primary">{{ req.old_character?.name ?? '?' }}</strong>
                {{ t('dashboard.with') }}
                <strong class="text-accent-gold">{{ req.new_character?.name ?? '?' }}</strong>
                <span v-if="req.reason" class="italic"> — {{ req.reason }}</span>
              </p>
              <div class="flex flex-wrap gap-2">
                <button
                  class="text-xs px-3 py-1 rounded border border-green-700 bg-green-900/20 hover:border-green-500 text-green-400 hover:text-green-300 transition-colors"
                  @click="resolveReplacement(req, 'confirm')"
                >{{ t('common.buttons.confirm') }}</button>
                <button
                  class="text-xs px-3 py-1 rounded border border-red-700 bg-red-900/20 hover:border-red-500 text-red-400 hover:text-red-300 transition-colors"
                  @click="resolveReplacement(req, 'decline')"
                >{{ t('common.buttons.decline') }}</button>
                <button
                  class="text-xs px-3 py-1 rounded border border-border-default hover:border-red-500 text-text-muted hover:text-red-300 transition-colors"
                  @click="resolveReplacement(req, 'leave')"
                >{{ t('common.labels.leaveRaid') }}</button>
              </div>
            </div>
          </WowCard>
        </div>
      </div>

      <!-- Today's Raids (raids today that the player is signed up for) -->
      <div v-if="!loading && todaysRaids.length > 0" class="space-y-3">
        <h2 class="wow-heading text-lg">⚔️ {{ t('dashboard.todaysRaids') }}</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <RouterLink
            v-for="tr in todaysRaids"
            :key="tr.event.id"
            :to="`/raids/${tr.event.id}`"
            class="block"
          >
            <WowCard class="border-accent-gold/30 hover:border-border-gold transition-colors cursor-pointer">
              <div class="flex items-center gap-3">
                <img
                  :src="getRaidIcon(tr.event.raid_type)"
                  :alt="tr.event.raid_type"
                  class="w-10 h-10 rounded border border-border-default flex-shrink-0"
                />
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="font-semibold text-text-primary text-sm truncate">{{ tr.event.title }}</span>
                    <StatusBadge :status="tr.event.status ?? 'open'" />
                  </div>
                  <div class="text-xs text-text-muted mt-0.5">
                    🕐 {{ formatTimeOnly(tr.event.starts_at_utc ?? tr.event.start_time ?? tr.event.date) }}
                  </div>
                  <div v-if="tr.signup" class="flex items-center gap-1 mt-0.5">
                    <ClassBadge v-if="tr.signup.character?.class_name" :class-name="tr.signup.character.class_name" />
                    <span class="text-xs text-text-muted truncate">{{ tr.signup.character?.name ?? t('dashboard.signedUp') }}</span>
                    <span v-if="tr.signup.lineup_status === 'bench'" class="text-[10px] font-semibold text-yellow-400 bg-yellow-400/10 px-1 py-0.5 rounded">{{ t('common.labels.bench') }}</span>
                    <span v-else class="text-[10px] font-semibold text-green-400 bg-green-400/10 px-1 py-0.5 rounded">{{ t('common.labels.inLineup') }}</span>
                  </div>
                </div>
              </div>
            </WowCard>
          </RouterLink>
        </div>
      </div>

      <!-- Main grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        <!-- Upcoming raids (2/3 width) -->
        <div class="lg:col-span-2 space-y-3">
          <div class="flex items-center justify-between flex-wrap gap-2">
            <h2 class="wow-heading text-lg">{{ t('dashboard.upcomingRaids') }}</h2>
            <select
              v-model.number="filterDays"
              class="text-xs bg-bg-secondary border border-border-default rounded px-2 py-1 text-text-primary focus:border-accent-gold focus:outline-none"
            >
              <option :value="1">{{ t('dashboard.filterDays.1') }}</option>
              <option :value="3">{{ t('dashboard.filterDays.3') }}</option>
              <option :value="7">{{ t('dashboard.filterDays.7') }}</option>
              <option :value="14">{{ t('dashboard.filterDays.14') }}</option>
              <option :value="30">{{ t('dashboard.filterDays.30') }}</option>
              <option :value="60">{{ t('dashboard.filterDays.60') }}</option>
            </select>
          </div>
          <div v-if="loading" class="space-y-2">
            <div v-for="i in 3" :key="i" class="h-16 rounded bg-bg-secondary border border-border-default loading-pulse" />
          </div>
          <div v-else-if="upcomingEvents.length === 0" class="text-center py-8 text-text-muted">
            {{ t('dashboard.noUpcomingRaids') }}
          </div>
          <RouterLink
            v-else
            v-for="ev in upcomingEvents"
            :key="ev.id"
            :to="`/raids/${ev.id}`"
            class="block"
          >
            <WowCard class="hover:border-border-gold transition-colors cursor-pointer">
              <div class="flex items-center gap-3 sm:gap-4">
                <img
                  :src="getRaidIcon(ev.raid_type)"
                  :alt="ev.raid_type"
                  class="w-10 h-10 sm:w-12 sm:h-12 rounded border border-border-default flex-shrink-0"
                />
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="font-semibold text-text-primary">{{ ev.title }}</span>
                    <RaidSizeBadge v-if="ev.raid_size || ev.size" :size="ev.raid_size ?? ev.size" />
                    <StatusBadge :status="ev.status ?? 'open'" />
                  </div>
                  <div class="text-sm text-text-muted mt-1 flex items-center gap-2 flex-wrap">
                    <span>📅 {{ formatDateTime(ev.starts_at_utc ?? ev.start_time ?? ev.date) }}</span>
                    <span v-if="ev.duration_minutes" class="text-text-muted">· ⏱️ ~{{ formatDuration(ev.duration_minutes) }}</span>
                  </div>
                  <div class="flex items-center gap-2 mt-1 flex-wrap">
                    <span v-if="raidTypeLabel(ev.raid_type, raidTypes)" class="text-[10px] text-amber-300">⚔️ {{ raidTypeLabel(ev.raid_type, raidTypes) }}</span>
                    <RealmBadge v-if="ev.realm_name || ev.realm" :realm="ev.realm_name ?? ev.realm" />
                    <span v-if="ev.close_signups_at" class="text-[10px] text-text-muted">🔒 {{ t('dashboard.signupsClose', { time: formatDateTime(ev.close_signups_at) }) }}</span>
                  </div>
                </div>
                <svg class="w-5 h-5 text-text-muted flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
              </div>
            </WowCard>
          </RouterLink>
        </div>

        <!-- My signups sidebar (1/3 width) -->
        <div class="space-y-3">
          <h2 class="wow-heading text-lg">{{ t('dashboard.mySignups') }}</h2>
          <div v-if="loading" class="space-y-2">
            <div v-for="i in 3" :key="i" class="h-14 rounded bg-bg-secondary border border-border-default loading-pulse" />
          </div>
          <div v-else-if="sortedMySignups.length === 0" class="text-center py-8 text-text-muted text-sm">
            {{ t('common.labels.noSignups') }}
          </div>
          <RouterLink
            v-else
            v-for="su in sortedMySignups"
            :key="su.id"
            :to="`/raids/${su.raid_event_id}`"
            class="block"
          >
            <WowCard class="py-2 hover:border-border-gold transition-colors cursor-pointer">
              <div class="flex items-center gap-2">
                <ClassBadge v-if="su.character?.class_name" :class-name="su.character.class_name" />
                <div class="flex-1 min-w-0">
                  <span class="text-sm text-text-primary truncate block">{{ su.event_title ?? 'Raid' }}</span>
                  <span v-if="raidTypeLabel(su.raid_type, raidTypes)" class="text-[10px] text-amber-300 truncate block">{{ raidTypeLabel(su.raid_type, raidTypes) }}</span>
                  <span v-if="su.character?.name" class="text-xs text-text-muted truncate block">
                    {{ su.character.name }}
                  </span>
                  <span v-if="su.chosen_spec" class="inline-flex items-center gap-1 flex-wrap mt-0.5">
                    <SpecBadge v-for="sp in su.chosen_spec.split(',').map(s => s.trim()).filter(Boolean)" :key="sp" :spec="sp" :class-name="su.character?.class_name" />
                  </span>
                </div>
                <span v-if="su.lineup_status === 'bench' || su.bench_info" class="text-[10px] font-semibold text-yellow-400 bg-yellow-400/10 px-1.5 py-0.5 rounded flex-shrink-0">
                  {{ t('dashboard.queue') }}{{ su.bench_info ? ' #' + su.bench_info.queue_position : '' }}{{ su.bench_info?.waiting_for ? ' · ' + benchRoleLabel(su.bench_info.waiting_for) : '' }}
                </span>
                <span v-else-if="su.lineup_status === 'declined'" class="text-[10px] font-semibold text-red-400 bg-red-400/10 px-1.5 py-0.5 rounded flex-shrink-0">{{ t('common.labels.declined') }}</span>
                <span v-else class="text-[10px] font-semibold text-green-400 bg-green-400/10 px-1.5 py-0.5 rounded flex-shrink-0">{{ t('common.labels.inLineup') }}</span>
                <!-- Attendance status indicator -->
                <span v-if="su.attendance_status && su.attendance_status !== 'going'" class="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded flex-shrink-0" :class="(ATTENDANCE_STATUS_STYLE[su.attendance_status] || {}).badge">
                  <img :src="getAttendanceStatusIcon(su.attendance_status)" class="w-3 h-3 rounded-sm" alt="" />
                  {{ t(ATTENDANCE_STATUS_I18N_MAP[su.attendance_status]) }}{{ su.attendance_status === 'late' && su.late_minutes ? ' ~' + su.late_minutes + 'min' : '' }}
                </span>
              </div>
            </WowCard>
          </RouterLink>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import RaidSizeBadge from '@/components/common/RaidSizeBadge.vue'
import RealmBadge from '@/components/common/RealmBadge.vue'
import ClassBadge from '@/components/common/ClassBadge.vue'
import SpecBadge from '@/components/common/SpecBadge.vue'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'
import { useCalendarStore } from '@/stores/calendar'
import { useTenantStore } from '@/stores/tenant'
import { useUiStore } from '@/stores/ui'
import { useWowIcons } from '@/composables/useWowIcons'
import { useTimezone } from '@/composables/useTimezone'
import { useFormatting } from '@/composables/useFormatting'
import { useSocket } from '@/composables/useSocket'
import { ROLE_LABEL_MAP, formatDuration, raidTypeLabel, ATTENDANCE_STATUS_I18N_MAP, ATTENDANCE_STATUS_STYLE } from '@/constants'
import { useExpansionData } from '@/composables/useExpansionData'
import { useConstantsStore } from '@/stores/constants'
import * as guildExpansionsApi from '@/api/guild_expansions'
import * as eventsApi from '@/api/events'
import * as signupsApi from '@/api/signups'
import { useI18n } from 'vue-i18n'

const authStore = useAuthStore()
const guildStore = useGuildStore()
const calStore = useCalendarStore()
const tenantStore = useTenantStore()
const uiStore = useUiStore()
const constantsStore = useConstantsStore()
const { getRaidIcon, getAttendanceStatusIcon } = useWowIcons()
const tzHelper = useTimezone()
const { formatDateTime, formatTimeOnly } = useFormatting()
const { joinGuild, leaveGuild, on, off } = useSocket()
const { t } = useI18n()
const { raidTypes: expansionRaidTypes } = useExpansionData()
const guildRaidTypes = ref([])

// Use guild-specific raidTypes if loaded, otherwise fall back to constants store then expansion data
const raidTypes = computed(() => {
  if (guildRaidTypes.value.length) return guildRaidTypes.value
  if (constantsStore.raidTypes.length) return constantsStore.raidTypes
  return expansionRaidTypes.value
})

let isActive = true
const loading = ref(true)
const mySignups = ref([])
const replacementRequests = ref([])
const filterDays = ref(14)

async function refreshSignups() {
  try {
    const allSignups = await eventsApi.getMySignups()
    const nowMs = Date.now()
    mySignups.value = allSignups.filter(su => {
      const status = su.event_status
      if (status === 'completed' || status === 'cancelled') return false
      const startsAt = su.starts_at_utc
      if (startsAt && new Date(startsAt).getTime() < nowMs) return false
      return true
    })
  } catch {
    mySignups.value = []
  }
}

async function refreshReplacements() {
  try {
    replacementRequests.value = await eventsApi.getMyReplacementRequests()
  } catch {
    replacementRequests.value = []
  }
}

async function refreshDashboard() {
  if (!isActive) return
  await calStore.fetchEvents()
  await refreshSignups()
  await refreshReplacements()
}

function handleEventsChanged() { if (isActive) refreshDashboard() }
function handleGuildsChanged() { if (isActive) { guildStore.fetchGuilds(); refreshDashboard() } }
function handleGuildChanged() { if (isActive) refreshDashboard() }

onMounted(async () => {
  loading.value = true
  nowTimer = setInterval(() => { now.value = new Date() }, 60000)
  try {
    await guildStore.fetchGuilds()
    if (guildStore.currentGuild) {
      joinGuild(guildStore.currentGuild.id)
      // Load guild-specific raid type labels
      guildExpansionsApi.getGuildConstants(guildStore.currentGuild.id).then(data => {
        if (data?.raid_types) {
          guildRaidTypes.value = data.raid_types.map(r => ({ value: r.code, label: r.name }))
        }
      }).catch(() => { /* ignore — fall back to expansion data */ })
      guildStore.fetchMembers(guildStore.currentGuild.id).catch(() => {})
    }
    await refreshDashboard()
  } finally {
    loading.value = false
  }
  on('events_changed', handleEventsChanged)
  on('guilds_changed', handleGuildsChanged)
  on('guild_changed', handleGuildChanged)
  on('signups_changed', handleEventsChanged)
  on('lineup_changed', handleEventsChanged)
})

onUnmounted(() => {
  isActive = false
  if (nowTimer) clearInterval(nowTimer)
  if (guildStore.currentGuild) leaveGuild(guildStore.currentGuild.id)
  off('events_changed', handleEventsChanged)
  off('guilds_changed', handleGuildsChanged)
  off('guild_changed', handleGuildChanged)
  off('signups_changed', handleEventsChanged)
  off('lineup_changed', handleEventsChanged)
})

// Also refresh when guild changes in sidebar
watch(
  () => guildStore.currentGuild?.id,
  (newId, oldId) => {
    if (oldId) leaveGuild(oldId)
    if (newId) joinGuild(newId)
    if (newId && newId !== oldId) {
      refreshDashboard()
      // Reload guild-specific raid type labels
      guildExpansionsApi.getGuildConstants(newId).then(data => {
        if (data?.raid_types) {
          guildRaidTypes.value = data.raid_types.map(r => ({ value: r.code, label: r.name }))
        }
      }).catch(() => { guildRaidTypes.value = [] })
    }
  }
)

const now = ref(new Date())
let nowTimer = null

const upcomingEvents = computed(() => {
  const nowMs = now.value.getTime()
  const cutoffMs = nowMs + filterDays.value * 86400000
  return calStore.events
    .filter(ev => {
      const t = new Date(ev.starts_at_utc ?? ev.start_time ?? ev.date).getTime()
      return t >= nowMs && t <= cutoffMs && ev.status !== 'cancelled'
    })
    .sort((a, b) => new Date(a.starts_at_utc ?? a.start_time ?? a.date) - new Date(b.starts_at_utc ?? b.start_time ?? b.date))
    .slice(0, 20)
})

const myGoingCount = computed(() => mySignups.value.filter(s => s.lineup_status === 'going').length)
const myBenchCount = computed(() => mySignups.value.filter(s => s.lineup_status === 'bench').length)
const missingResponseCount = computed(() => {
  const signedUpEventIds = new Set(mySignups.value.map(s => s.raid_event_id))
  return upcomingEvents.value.filter(ev => !signedUpEventIds.has(ev.id)).length
})

const totalEvents = computed(() => calStore.events.length)

const eventsThisWeek = computed(() => {
  const nowMs = now.value.getTime()
  const weekEnd = nowMs + 7 * 86400000
  return calStore.events.filter(ev => {
    const ts = new Date(ev.starts_at_utc ?? ev.start_time ?? ev.date).getTime()
    return ts >= nowMs && ts <= weekEnd && ev.status !== 'cancelled'
  }).length
})

const eventsNextWeek = computed(() => {
  const nowMs = now.value.getTime()
  const weekStart = nowMs + 7 * 86400000
  const weekEnd = nowMs + 14 * 86400000
  return calStore.events.filter(ev => {
    const ts = new Date(ev.starts_at_utc ?? ev.start_time ?? ev.date).getTime()
    return ts >= weekStart && ts <= weekEnd && ev.status !== 'cancelled'
  }).length
})

const avgSignupsPerRaid = computed(() => {
  const upcoming = upcomingEvents.value
  if (upcoming.length === 0) return '—'
  const total = upcoming.reduce((sum, ev) => sum + (ev.signup_count ?? 0), 0)
  return (total / upcoming.length).toFixed(1)
})

const benchedSignups = computed(() =>
  mySignups.value
    .filter(s => s.lineup_status === 'bench')
    .sort((a, b) => (a.bench_info?.queue_position ?? 999) - (b.bench_info?.queue_position ?? 999))
)

// Sort: lineup first, then bench ordered by queue position, then declined
const sortedMySignups = computed(() => {
  return [...mySignups.value].sort((a, b) => {
    const statusOrder = { going: 0, bench: 1, declined: 2 }
    const aOrder = statusOrder[a.lineup_status] ?? 1
    const bOrder = statusOrder[b.lineup_status] ?? 1
    if (aOrder !== bOrder) return aOrder - bOrder
    // Within bench, sort by queue position
    if (a.lineup_status === 'bench' && b.lineup_status === 'bench') {
      const aPos = a.bench_info?.queue_position ?? 999
      const bPos = b.bench_info?.queue_position ?? 999
      return aPos - bPos
    }
    return 0
  })
})

// Today's raids that the player is signed up for
const todaysRaids = computed(() => {
  const guildTz = tzHelper.guildTimezone.value
  const todayStr = now.value.toLocaleDateString('en-CA', { timeZone: guildTz })
  const signupMap = new Map()
  for (const su of mySignups.value) {
    signupMap.set(su.raid_event_id, su)
  }
  return calStore.events
    .filter(ev => {
      const iso = ev.starts_at_utc ?? ev.start_time ?? ev.date
      if (!iso || ev.status === 'cancelled') return false
      const evDate = new Date(iso).toLocaleDateString('en-CA', { timeZone: guildTz })
      return evDate === todayStr && signupMap.has(ev.id)
    })
    .sort((a, b) => new Date(a.starts_at_utc ?? a.start_time ?? a.date) - new Date(b.starts_at_utc ?? b.start_time ?? b.date))
    .map(ev => ({ event: ev, signup: signupMap.get(ev.id) }))
})

function benchRoleLabel(role) {
  return ROLE_LABEL_MAP[role] || role
}

async function resolveReplacement(req, action) {
  if (!req.guild_id || !req.event_id) return
  try {
    await signupsApi.resolveReplaceRequest(req.guild_id, req.event_id, req.id, { action })
    // Remove from local list
    replacementRequests.value = replacementRequests.value.filter(r => r.id !== req.id)
    uiStore.showToast(
      action === 'confirm' ? t('dashboard.swapConfirmed') : action === 'leave' ? t('dashboard.leftRaid') : t('dashboard.swapDeclined'),
      action === 'confirm' ? 'success' : 'info'
    )
    // Refresh signups in case lineup status changed
    await refreshSignups()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('common.toasts.failedToProcessReplacement'), 'error')
  }
}
</script>
