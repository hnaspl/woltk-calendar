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
          <div class="text-xs text-text-muted mt-1">Confirmed</div>
        </WowCard>
        <WowCard class="text-center">
          <div class="text-3xl font-bold text-yellow-400">{{ myTentativeCount }}</div>
          <div class="text-xs text-text-muted mt-1">Tentative</div>
        </WowCard>
        <WowCard class="text-center">
          <div class="text-3xl font-bold text-red-400">{{ missingResponseCount }}</div>
          <div class="text-xs text-text-muted mt-1">No Response</div>
        </WowCard>
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
          <WowCard v-else v-for="su in mySignups" :key="su.id" class="py-2">
            <div class="flex items-center gap-2">
              <ClassBadge v-if="su.character?.class_name" :class-name="su.character.class_name" />
              <span class="text-sm text-text-primary flex-1 truncate">{{ su.event_title ?? 'Raid' }}</span>
              <StatusBadge :status="su.status" />
            </div>
          </WowCard>
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
import * as signupsApi from '@/api/signups'

const authStore = useAuthStore()
const guildStore = useGuildStore()
const calStore = useCalendarStore()
const { getRaidIcon } = useWowIcons()

const loading = ref(true)
const mySignups = ref([])

onMounted(async () => {
  loading.value = true
  try {
    await guildStore.fetchGuilds()
    if (guildStore.currentGuild) {
      await calStore.fetchEvents(guildStore.currentGuild.id)
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

const myGoingCount = computed(() => mySignups.value.filter(s => s.status === 'going').length)
const myTentativeCount = computed(() => mySignups.value.filter(s => s.status === 'tentative').length)
const missingResponseCount = computed(() => upcomingEvents.value.length - mySignups.value.length)

function formatDateTime(d) {
  if (!d) return '?'
  return new Date(d).toLocaleString('en-GB', {
    weekday: 'short', day: '2-digit', month: 'short',
    hour: '2-digit', minute: '2-digit'
  })
}
</script>
