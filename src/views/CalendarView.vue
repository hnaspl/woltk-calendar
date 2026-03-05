<template>
  <AppShell>
    <div class="flex flex-col md:flex-row h-full overflow-hidden">
      <!-- Sidebar filters -->
      <aside class="w-full md:w-64 flex-shrink-0 border-b md:border-b-0 md:border-r border-border-default bg-bg-secondary p-4 space-y-4 overflow-y-auto">
        <h2 class="wow-heading text-base">{{ t('calendar.filters') }}</h2>

        <div v-if="guildStore.currentGuild?.realm_name" class="text-xs text-text-muted">
          <span class="text-accent-gold">🌐</span> {{ t('common.labels.realmColon') }} <span class="text-text-primary font-medium">{{ guildStore.currentGuild.realm_name }}</span>
        </div>

        <label class="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            :checked="calStore.filters.showAllGuilds"
            class="accent-accent-gold w-4 h-4 rounded"
            @change="calStore.setFilter('showAllGuilds', $event.target.checked)"
          />
          <span class="text-xs text-text-muted">{{ t('calendar.viewAllGuilds') }}</span>
        </label>

        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('calendar.raidType') }}</label>
          <select
            :value="calStore.filters.raidType"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
            @change="calStore.setFilter('raidType', $event.target.value)"
          >
            <option value="">{{ t('calendar.allRaids') }}</option>
            <option v-for="r in raidTypes" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
        </div>

        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('calendar.size') }}</label>
          <select
            :value="calStore.filters.size"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
            @change="calStore.setFilter('size', $event.target.value)"
          >
            <option value="">{{ t('calendar.allSizes') }}</option>
            <option value="10">{{ t('calendar.tenMan') }}</option>
            <option value="25">{{ t('calendar.twentyFiveMan') }}</option>
          </select>
        </div>

        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.status') }}</label>
          <select
            :value="calStore.filters.status"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
            @change="calStore.setFilter('status', $event.target.value)"
          >
            <option value="">{{ t('calendar.allStatuses') }}</option>
            <option value="open">{{ t('common.status.open') }}</option>
            <option value="locked">{{ t('common.status.locked') }}</option>
            <option value="completed">{{ t('common.status.completed') }}</option>
            <option value="cancelled">{{ t('common.status.cancelled') }}</option>
          </select>
        </div>

        <WowButton variant="ghost" class="w-full text-xs" @click="calStore.clearFilters()">
          {{ t('calendar.clearFilters') }}
        </WowButton>

        <WowButton v-if="permissions.can('create_events')" class="w-full text-sm" @click="openCreateModal">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          {{ t('calendar.scheduleRaid') }}
        </WowButton>
      </aside>

      <!-- Calendar -->
      <div class="flex-1 p-2 sm:p-4 overflow-y-auto">
        <div v-if="calStore.loading" class="flex items-center justify-center h-64">
          <div class="text-text-muted loading-pulse">{{ t('calendar.loadingCalendar') }}</div>
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
    <WowModal v-model="showCreateModal" :title="t('calendar.scheduleRaid')" size="lg">
      <form @submit.prevent="createEvent" class="space-y-4">
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('calendar.guild') }}</label>
          <select v-model.number="eventForm.guild_id" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" @change="onGuildSelectChange">
            <option value="">{{ t('calendar.selectGuild') }}</option>
            <option v-for="g in guildStore.guilds" :key="g.id" :value="g.id">{{ g.name }} ({{ g.realm_name }})</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.raidDefinition') }}</label>
          <select v-model.number="eventForm.raid_definition_id" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" @change="onRaidDefChange">
            <option value="">{{ t('calendar.selectRaidDef') }}</option>
            <optgroup :label="t('calendar.builtInRaids')">
              <option v-for="rd in builtinDefs" :key="rd.id" :value="rd.id">{{ rd.name }} ({{ rd.default_raid_size ?? rd.size }}-man)</option>
            </optgroup>
            <optgroup v-if="customDefs.length" :label="t('calendar.customRaids')">
              <option v-for="rd in customDefs" :key="rd.id" :value="rd.id">{{ rd.name }} ({{ rd.default_raid_size ?? rd.size }}-man)</option>
            </optgroup>
          </select>
          <p class="text-[10px] text-text-muted mt-1">{{ t('calendar.manageCustomRaids') }} <router-link to="/guild/raid-definitions" class="text-accent-gold hover:underline">{{ t('nav.raidDefinitions') }}</router-link></p>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.titleRequired') }}</label>
          <input v-model="eventForm.title" required :placeholder="t('calendar.titlePlaceholder')" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('calendar.size') }}</label>
            <select v-model.number="eventForm.raid_size" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option :value="10">{{ t('calendar.tenMan') }}</option>
              <option :value="25">{{ t('calendar.twentyFiveMan') }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('calendar.difficulty') }}</label>
            <select v-model="eventForm.difficulty" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="normal">{{ t('calendar.normal') }}</option>
              <option value="heroic">{{ t('calendar.heroic') }}</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.startDateTime') }}</label>
            <input v-model="eventForm.starts_at_utc" type="datetime-local" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('calendar.durationMinutes') }}</label>
            <input v-model.number="eventForm.duration_minutes" type="number" min="30" max="720" step="15" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('calendar.closeSignupsAt') }}</label>
            <input v-model="eventForm.close_signups_at" type="datetime-local" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
            <span class="text-[10px] text-text-muted">{{ t('calendar.closeSignupsHelp') }}</span>
          </div>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('calendar.instructions') }}</label>
          <textarea v-model="eventForm.instructions" rows="2" :placeholder="t('calendar.instructionsPlaceholder')" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none resize-none placeholder:text-text-muted/50" />
        </div>
        <div v-if="createError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ createError }}</div>
      </form>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showCreateModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton :loading="creating" @click="createEvent">{{ t('common.buttons.schedule') }}</WowButton>
        </div>
      </template>
    </WowModal>
  </AppShell>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import RaidCalendar from '@/components/calendar/RaidCalendar.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import { useCalendarStore } from '@/stores/calendar'
import { useGuildStore } from '@/stores/guild'
import { usePermissions } from '@/composables/usePermissions'
import { useUiStore } from '@/stores/ui'
import { useSocket } from '@/composables/useSocket'
import { useTimezone } from '@/composables/useTimezone'
import { useExpansionData } from '@/composables/useExpansionData'
import * as eventsApi from '@/api/events'
import * as raidDefsApi from '@/api/raidDefinitions'
import * as guildExpansionsApi from '@/api/guild_expansions'
import { useI18n } from 'vue-i18n'

const calStore = useCalendarStore()
const guildStore = useGuildStore()
const uiStore = useUiStore()
const permissions = usePermissions()
const router = useRouter()
const { joinGuild, leaveGuild, on, off } = useSocket()
const tzHelper = useTimezone()
const { t } = useI18n()

const { raidTypes } = useExpansionData()

const showCreateModal = ref(false)
const creating = ref(false)
const createError = ref(null)
const raidDefs = ref([])
const guildExpansionSlugs = ref([])

// Filter raid definitions by guild's enabled expansions
const filteredRaidDefs = computed(() => {
  if (!guildExpansionSlugs.value.length) return raidDefs.value
  return raidDefs.value.filter(d => guildExpansionSlugs.value.includes(d.expansion))
})

const builtinDefs = computed(() => filteredRaidDefs.value.filter(d => d.is_builtin))
const customDefs = computed(() => filteredRaidDefs.value.filter(d => !d.is_builtin))

const eventForm = reactive({
  title: '',
  guild_id: null,
  realm_name: '',
  raid_definition_id: '',
  raid_size: 25,
  starts_at_utc: '',
  duration_minutes: 180,
  difficulty: 'normal',
  raid_type: '',
  close_signups_at: '',
  instructions: ''
})

onMounted(async () => {
  await guildStore.fetchGuilds()
  const tasks = [calStore.fetchEvents()]
  if (guildStore.currentGuild) {
    tasks.push(guildStore.fetchMembers(guildStore.currentGuild.id))
    joinGuild(guildStore.currentGuild.id)
  }
  await Promise.all(tasks)
  on('events_changed', handleEventsChanged)
})

// Re-join guild room when current guild changes
const stopGuildWatch = watch(() => guildStore.currentGuild?.id, (newId, oldId) => {
  if (oldId) leaveGuild(oldId)
  if (newId) joinGuild(newId)
})

function handleEventsChanged() {
  calStore.fetchEvents()
}

onUnmounted(() => {
  off('events_changed', handleEventsChanged)
  if (guildStore.currentGuild) leaveGuild(guildStore.currentGuild.id)
  stopGuildWatch()
})

function loadRaidDefsForGuild(guildId) {
  raidDefsApi.getRaidDefinitions(guildId).then(defs => { raidDefs.value = defs }).catch(err => { console.warn('Failed to load raid definitions', err) })
  guildExpansionsApi.getGuildExpansions(guildId).then(res => {
    const exps = res?.expansions ?? res ?? []
    guildExpansionSlugs.value = exps.map(e => e.expansion_slug || e.slug).filter(Boolean)
  }).catch(() => { guildExpansionSlugs.value = [] })
}

function openCreateModal() {
  Object.assign(eventForm, { title: '', guild_id: guildStore.currentGuild?.id ?? null, realm_name: guildStore.currentGuild?.realm_name ?? '', raid_definition_id: '', raid_size: 25, starts_at_utc: '', duration_minutes: 180, difficulty: 'normal', raid_type: '', close_signups_at: '', instructions: '' })
  createError.value = null
  showCreateModal.value = true
  if (eventForm.guild_id) loadRaidDefsForGuild(eventForm.guild_id)
}

function onGuildSelectChange() {
  const selected = guildStore.guilds.find(g => g.id === eventForm.guild_id)
  if (selected) eventForm.realm_name = selected.realm_name
  eventForm.raid_definition_id = ''
  if (eventForm.guild_id) {
    loadRaidDefsForGuild(eventForm.guild_id)
  } else {
    raidDefs.value = []
    guildExpansionSlugs.value = []
  }
}

function onRaidDefChange() {
  const rd = raidDefs.value.find(d => d.id === eventForm.raid_definition_id)
  if (rd) {
    eventForm.raid_type = rd.raid_type || rd.code || ''
    eventForm.raid_size = rd.default_raid_size ?? rd.size ?? 25
    if (rd.default_duration_minutes) eventForm.duration_minutes = rd.default_duration_minutes
    // Auto-set difficulty based on raid definition
    eventForm.difficulty = rd.supports_heroic ? 'heroic' : 'normal'
  }
}

async function createEvent() {
  if (!eventForm.guild_id || !eventForm.starts_at_utc || !eventForm.raid_definition_id) {
    createError.value = t('calendar.validationError')
    return
  }
  if (!eventForm.title) {
    const rd = raidDefs.value.find(d => d.id === eventForm.raid_definition_id)
    eventForm.title = rd?.name ?? 'Raid'
  }
  if (eventForm.close_signups_at && new Date(eventForm.close_signups_at) >= new Date(eventForm.starts_at_utc)) {
    createError.value = t('calendar.closeSignupsError')
    return
  }
  createError.value = null
  creating.value = true
  try {
    const payload = {
      title: eventForm.title,
      realm_name: eventForm.realm_name,
      raid_size: eventForm.raid_size,
      starts_at_utc: tzHelper.guildLocalToUtc(eventForm.starts_at_utc),
      duration_minutes: eventForm.duration_minutes,
      difficulty: eventForm.difficulty,
      raid_type: eventForm.raid_type || undefined,
      raid_definition_id: eventForm.raid_definition_id || undefined,
      close_signups_at: eventForm.close_signups_at ? tzHelper.guildLocalToUtc(eventForm.close_signups_at) : undefined,
      instructions: eventForm.instructions,
      status: 'open'
    }
    const newEvent = await eventsApi.createEvent(eventForm.guild_id, payload)
    showCreateModal.value = false
    uiStore.showToast(t('calendar.raidScheduled'), 'success')
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
