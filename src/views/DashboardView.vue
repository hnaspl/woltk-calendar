<template>
  <AppShell>
    <div class="p-4 md:p-6 space-y-6">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="wow-heading text-2xl">Dashboard</h1>
          <p class="text-text-muted text-sm mt-0.5">Welcome back, {{ authStore.user?.username }}!</p>
        </div>
        <RouterLink to="/calendar">
          <WowButton variant="secondary">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
            </svg>
            Calendar
          </WowButton>
        </RouterLink>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div v-for="i in 4" :key="i" class="h-24 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      </div>

      <!-- Stats row -->
      <div v-else class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <WowCard class="text-center">
          <div class="text-3xl font-bold text-accent-gold">{{ upcomingEvents.length }}</div>
          <div class="text-xs text-text-muted mt-1">Upcoming Raids</div>
        </WowCard>
        <WowCard class="text-center">
          <div class="text-3xl font-bold text-green-400">{{ myGoingCount }}</div>
          <div class="text-xs text-text-muted mt-1">In Lineup</div>
        </WowCard>
        <WowCard class="text-center">
          <div class="text-3xl font-bold text-yellow-400">{{ myBenchCount }}</div>
          <div class="text-xs text-text-muted mt-1">On Bench</div>
        </WowCard>
        <WowCard class="text-center">
          <div class="text-3xl font-bold text-red-400">{{ missingResponseCount }}</div>
          <div class="text-xs text-text-muted mt-1">No Response</div>
        </WowCard>
      </div>

      <!-- Pending Replacement Requests -->
      <div v-if="replacementRequests.length > 0" class="space-y-3">
        <h2 class="wow-heading text-lg">⚡ Pending Character Swaps</h2>
        <div v-for="req in replacementRequests" :key="req.id">
          <WowCard class="border-blue-700 bg-blue-900/10">
            <div class="space-y-2">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-blue-300 text-xs font-semibold">Character Swap Requested</span>
                <span v-if="req.event_title" class="text-xs text-text-muted">·</span>
                <RouterLink
                  v-if="req.event_id && req.guild_id"
                  :to="`/raids/${req.event_id}`"
                  class="text-xs text-accent-gold hover:underline"
                >{{ req.event_title ?? 'Raid' }}</RouterLink>
                <span v-if="req.starts_at_utc" class="text-[10px] text-text-muted">{{ formatDateTime(req.starts_at_utc) }}</span>
              </div>
              <p class="text-text-muted text-xs">
                <strong class="text-text-primary">{{ req.requester_name }}</strong>
                wants to replace
                <strong class="text-text-primary">{{ req.old_character?.name ?? '?' }}</strong>
                with
                <strong class="text-accent-gold">{{ req.new_character?.name ?? '?' }}</strong>
                <span v-if="req.reason" class="italic"> — {{ req.reason }}</span>
              </p>
              <div class="flex gap-2">
                <button
                  class="text-xs px-3 py-1 rounded border border-green-700 bg-green-900/20 hover:border-green-500 text-green-400 hover:text-green-300 transition-colors"
                  @click="resolveReplacement(req, 'confirm')"
                >Confirm</button>
                <button
                  class="text-xs px-3 py-1 rounded border border-red-700 bg-red-900/20 hover:border-red-500 text-red-400 hover:text-red-300 transition-colors"
                  @click="resolveReplacement(req, 'decline')"
                >Decline</button>
                <button
                  class="text-xs px-3 py-1 rounded border border-border-default hover:border-red-500 text-text-muted hover:text-red-300 transition-colors"
                  @click="resolveReplacement(req, 'leave')"
                >Leave Raid</button>
              </div>
            </div>
          </WowCard>
        </div>
      </div>

      <!-- Main grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Upcoming raids (2/3 width) -->
        <div class="lg:col-span-2 space-y-3">
          <h2 class="wow-heading text-lg">Upcoming Raids</h2>
          <div v-if="loading" class="space-y-2">
            <div v-for="i in 3" :key="i" class="h-16 rounded bg-bg-secondary border border-border-default loading-pulse" />
          </div>
          <div v-else-if="upcomingEvents.length === 0" class="text-center py-8 text-text-muted">
            No upcoming raids scheduled.
          </div>
          <RouterLink
            v-else
            v-for="ev in upcomingEvents"
            :key="ev.id"
            :to="`/raids/${ev.id}`"
            class="block"
          >
            <WowCard class="hover:border-border-gold transition-colors cursor-pointer">
              <div class="flex items-center gap-4">
                <img
                  :src="getRaidIcon(ev.raid_type)"
                  :alt="ev.raid_type"
                  class="w-12 h-12 rounded border border-border-default flex-shrink-0"
                />
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="font-semibold text-text-primary">{{ ev.title }}</span>
                    <RaidSizeBadge v-if="ev.raid_size || ev.size" :size="ev.raid_size ?? ev.size" />
                    <StatusBadge :status="ev.status ?? 'open'" />
                  </div>
                  <div class="text-sm text-text-muted mt-1">
                    {{ formatDateTime(ev.starts_at_utc ?? ev.start_time ?? ev.date) }}
                    <RealmBadge v-if="ev.realm_name || ev.realm" :realm="ev.realm_name ?? ev.realm" class="ml-2" />
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
          <h2 class="wow-heading text-lg">My Signups</h2>
          <div v-if="loading" class="space-y-2">
            <div v-for="i in 3" :key="i" class="h-14 rounded bg-bg-secondary border border-border-default loading-pulse" />
          </div>
          <div v-else-if="mySignups.length === 0" class="text-center py-8 text-text-muted text-sm">
            No signups yet.
          </div>
          <RouterLink
            v-else
            v-for="su in mySignups"
            :key="su.id"
            :to="`/raids/${su.raid_event_id}`"
            class="block"
          >
            <WowCard class="py-2 hover:border-border-gold transition-colors cursor-pointer">
              <div class="flex items-center gap-2">
                <ClassBadge v-if="su.character?.class_name" :class-name="su.character.class_name" />
                <div class="flex-1 min-w-0">
                  <span class="text-sm text-text-primary truncate block">{{ su.event_title ?? 'Raid' }}</span>
                  <span v-if="raidLabel(su.raid_type)" class="text-[10px] text-amber-300 truncate block">{{ raidLabel(su.raid_type) }}</span>
                  <span v-if="su.character?.name" class="text-xs text-text-muted truncate block">
                    {{ su.character.name }}
                    <span v-if="su.chosen_spec" class="text-amber-200"> · {{ su.chosen_spec }}</span>
                  </span>
                </div>
                <span v-if="su.lineup_status === 'bench' || su.bench_info" class="text-[10px] font-semibold text-yellow-400 bg-yellow-400/10 px-1.5 py-0.5 rounded flex-shrink-0">
                  Bench{{ su.bench_info ? ' #' + su.bench_info.queue_position : '' }}
                </span>
                <span v-else-if="su.lineup_status === 'declined'" class="text-[10px] font-semibold text-red-400 bg-red-400/10 px-1.5 py-0.5 rounded flex-shrink-0">Declined</span>
                <span v-else class="text-[10px] font-semibold text-green-400 bg-green-400/10 px-1.5 py-0.5 rounded flex-shrink-0">In Lineup</span>
              </div>
            </WowCard>
          </RouterLink>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import RaidSizeBadge from '@/components/common/RaidSizeBadge.vue'
import RealmBadge from '@/components/common/RealmBadge.vue'
import ClassBadge from '@/components/common/ClassBadge.vue'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'
import { useCalendarStore } from '@/stores/calendar'
import { useWowIcons } from '@/composables/useWowIcons'
import { RAID_TYPES } from '@/constants'
import * as eventsApi from '@/api/events'
import * as signupsApi from '@/api/signups'

const authStore = useAuthStore()
const guildStore = useGuildStore()
const calStore = useCalendarStore()
const { getRaidIcon } = useWowIcons()

const loading = ref(true)
const mySignups = ref([])
const replacementRequests = ref([])

onMounted(async () => {
  loading.value = true
  try {
    await guildStore.fetchGuilds()
    // Fetch events for all user's guilds (getAllEvents is guild-agnostic)
    await calStore.fetchEvents()
    // Fetch user's signups across all guilds
    try {
      const allSignups = await eventsApi.getMySignups()
      // Filter out signups for completed, cancelled, or past events
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
    // Fetch pending replacement requests
    try {
      replacementRequests.value = await eventsApi.getMyReplacementRequests()
    } catch {
      replacementRequests.value = []
    }
  } finally {
    loading.value = false
  }
})

const now = new Date()

const upcomingEvents = computed(() =>
  calStore.events
    .filter(ev => new Date(ev.starts_at_utc ?? ev.start_time ?? ev.date) >= now && ev.status !== 'cancelled')
    .sort((a, b) => new Date(a.starts_at_utc ?? a.start_time ?? a.date) - new Date(b.starts_at_utc ?? b.start_time ?? b.date))
    .slice(0, 8)
)

const myGoingCount = computed(() => mySignups.value.filter(s => s.lineup_status === 'going').length)
const myBenchCount = computed(() => mySignups.value.filter(s => s.lineup_status === 'bench').length)
const missingResponseCount = computed(() => {
  const signedUpEventIds = new Set(mySignups.value.map(s => s.raid_event_id))
  return upcomingEvents.value.filter(ev => !signedUpEventIds.has(ev.id)).length
})

function formatDateTime(d) {
  if (!d) return '?'
  return new Date(d).toLocaleString('en-GB', {
    weekday: 'short', day: '2-digit', month: 'short',
    hour: '2-digit', minute: '2-digit'
  })
}

function raidLabel(raidType) {
  if (!raidType) return null
  const found = RAID_TYPES.find(r => r.value === raidType)
  return found ? found.label : raidType
}

async function resolveReplacement(req, action) {
  if (!req.guild_id || !req.event_id) return
  try {
    await signupsApi.resolveReplaceRequest(req.guild_id, req.event_id, req.id, { action })
    // Remove from local list
    replacementRequests.value = replacementRequests.value.filter(r => r.id !== req.id)
    // Refresh signups in case lineup status changed
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
    } catch { /* ignore */ }
  } catch { /* ignore */ }
}
</script>
