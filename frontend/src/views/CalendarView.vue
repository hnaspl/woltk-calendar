<template>
  <AppShell>
    <div class="flex flex-col md:flex-row h-full overflow-hidden">
      <!-- Sidebar filters -->
      <aside class="w-full md:w-64 flex-shrink-0 border-b md:border-b-0 md:border-r border-border-default bg-bg-secondary p-4 space-y-4 overflow-y-auto">
        <h2 class="wow-heading text-base">Filters</h2>

        <div>
          <label class="block text-xs text-text-muted mb-1">Realm</label>
          <select
            :value="calStore.filters.realm"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
            @change="calStore.setFilter('realm', $event.target.value)"
          >
            <option value="">All realms</option>
            <option v-for="r in warmaneRealms" :key="r" :value="r">{{ r }}</option>
          </select>
        </div>

        <div>
          <label class="block text-xs text-text-muted mb-1">Raid Type</label>
          <select
            :value="calStore.filters.raidType"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
            @change="calStore.setFilter('raidType', $event.target.value)"
          >
            <option value="">All raids</option>
            <option v-for="r in raidTypes" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
        </div>

        <div>
          <label class="block text-xs text-text-muted mb-1">Size</label>
          <select
            :value="calStore.filters.size"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
            @change="calStore.setFilter('size', $event.target.value)"
          >
            <option value="">All sizes</option>
            <option value="10">10-man</option>
            <option value="25">25-man</option>
          </select>
        </div>

        <div>
          <label class="block text-xs text-text-muted mb-1">Status</label>
          <select
            :value="calStore.filters.status"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
            @change="calStore.setFilter('status', $event.target.value)"
          >
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="locked">Locked</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        <WowButton variant="ghost" class="w-full text-xs" @click="calStore.clearFilters()">
          Clear Filters
        </WowButton>
      </aside>

      <!-- Calendar -->
      <div class="flex-1 p-4 overflow-y-auto">
        <div v-if="calStore.loading" class="flex items-center justify-center h-64">
          <div class="text-text-muted loading-pulse">Loading calendar…</div>
        </div>
        <RaidCalendar
          v-else
          :events="calStore.filteredEvents"
          initial-view="dayGridMonth"
          @event-click="onEventClick"
        />
      </div>
    </div>
  </AppShell>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import RaidCalendar from '@/components/calendar/RaidCalendar.vue'
import WowButton from '@/components/common/WowButton.vue'
import { useCalendarStore } from '@/stores/calendar'
import { useGuildStore } from '@/stores/guild'
import { WARMANE_REALMS, RAID_TYPES } from '@/constants'

const calStore = useCalendarStore()
const guildStore = useGuildStore()
const router = useRouter()

const raidTypes = RAID_TYPES
const warmaneRealms = WARMANE_REALMS

onMounted(async () => {
  if (!guildStore.currentGuild) await guildStore.fetchGuilds()
  if (guildStore.currentGuild) {
    await calStore.fetchEvents(guildStore.currentGuild.id)
  }
})

function onEventClick(event) {
  router.push(`/raids/${event.id}`)
}
</script>
