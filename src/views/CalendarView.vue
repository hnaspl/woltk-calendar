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

        <WowButton v-if="permissions.isOfficer.value" class="w-full text-sm" @click="openCreateModal">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          Schedule Raid
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

    <!-- Schedule Raid Modal -->
    <WowModal v-model="showCreateModal" title="Schedule Raid" size="md">
      <form @submit.prevent="createEvent" class="space-y-4">
        <div>
          <label class="block text-xs text-text-muted mb-1">Title *</label>
          <input v-model="eventForm.title" required placeholder="e.g. ICC 25 Heroic" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">Guild *</label>
            <select v-model.number="eventForm.guild_id" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" @change="onGuildSelectChange">
              <option value="">Select guild…</option>
              <option v-for="g in guildStore.guilds" :key="g.id" :value="g.id">{{ g.name }} ({{ g.realm_name }})</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Size</label>
            <select v-model.number="eventForm.raid_size" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option :value="10">10-man</option>
              <option :value="25">25-man</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">Date &amp; Time *</label>
            <input v-model="eventForm.starts_at_utc" type="datetime-local" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Difficulty</label>
            <select v-model="eventForm.difficulty" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="normal">Normal</option>
              <option value="heroic">Heroic</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Instructions</label>
          <textarea v-model="eventForm.instructions" rows="2" placeholder="Bring flasks, food, etc." class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none resize-none placeholder:text-text-muted/50" />
        </div>
        <div v-if="createError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ createError }}</div>
      </form>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showCreateModal = false">Cancel</WowButton>
          <WowButton :loading="creating" @click="createEvent">Schedule</WowButton>
        </div>
      </template>
    </WowModal>
  </AppShell>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import RaidCalendar from '@/components/calendar/RaidCalendar.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import { useCalendarStore } from '@/stores/calendar'
import { useGuildStore } from '@/stores/guild'
import { usePermissions } from '@/composables/usePermissions'
import { useUiStore } from '@/stores/ui'
import { WARMANE_REALMS, RAID_TYPES } from '@/constants'
import * as eventsApi from '@/api/events'

const calStore = useCalendarStore()
const guildStore = useGuildStore()
const uiStore = useUiStore()
const permissions = usePermissions()
const router = useRouter()

const raidTypes = RAID_TYPES
const warmaneRealms = WARMANE_REALMS

const showCreateModal = ref(false)
const creating = ref(false)
const createError = ref(null)
const eventForm = reactive({
  title: '',
  guild_id: '',
  realm_name: '',
  raid_size: 25,
  starts_at_utc: '',
  difficulty: 'normal',
  instructions: ''
})

onMounted(async () => {
  await guildStore.fetchGuilds()
  const tasks = [calStore.fetchEvents()]
  if (guildStore.currentGuild) {
    tasks.push(guildStore.fetchMembers(guildStore.currentGuild.id))
  }
  await Promise.all(tasks)
})

function openCreateModal() {
  Object.assign(eventForm, { title: '', guild_id: guildStore.currentGuild?.id ?? '', realm_name: guildStore.currentGuild?.realm_name ?? '', raid_size: 25, starts_at_utc: '', difficulty: 'normal', instructions: '' })
  createError.value = null
  showCreateModal.value = true
}

function onGuildSelectChange() {
  const selected = guildStore.guilds.find(g => g.id === eventForm.guild_id)
  if (selected) eventForm.realm_name = selected.realm_name
}

async function createEvent() {
  if (!eventForm.title || !eventForm.guild_id || !eventForm.starts_at_utc) {
    createError.value = 'Title, guild and date are required'
    return
  }
  createError.value = null
  creating.value = true
  try {
    const payload = {
      title: eventForm.title,
      realm_name: eventForm.realm_name,
      raid_size: eventForm.raid_size,
      starts_at_utc: eventForm.starts_at_utc,
      difficulty: eventForm.difficulty,
      instructions: eventForm.instructions,
      status: 'open'
    }
    const newEvent = await eventsApi.createEvent(eventForm.guild_id, payload)
    showCreateModal.value = false
    uiStore.showToast('Raid scheduled!', 'success')
    await calStore.fetchEvents()
    router.push(`/raids/${newEvent.id}`)
  } catch (err) {
    createError.value = err?.response?.data?.message ?? 'Failed to schedule raid'
  } finally {
    creating.value = false
  }
}

function onEventClick(event) {
  router.push(`/raids/${event.id}`)
}
</script>
