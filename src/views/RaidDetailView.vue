<template>
  <AppShell>
    <div class="p-4 md:p-6 space-y-6">
      <!-- Loading state -->
      <div v-if="loading" class="space-y-4">
        <div class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
        <div class="h-64 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      </div>

      <!-- Error -->
      <div v-else-if="error" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">
        {{ error }}
      </div>

      <template v-else-if="event">
        <!-- Event header -->
        <WowCard :gold="true">
          <div class="flex flex-col sm:flex-row items-start gap-4">
            <img
              :src="getRaidIcon(event.raid_type)"
              :alt="event.raid_type"
              class="w-20 h-20 rounded-lg border border-border-gold shadow-gold flex-shrink-0"
            />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap mb-2">
                <h1 class="wow-heading text-xl">{{ event.title }}</h1>
                <RaidSizeBadge v-if="event.raid_size || event.size" :size="event.raid_size ?? event.size" />
                <StatusBadge :status="event.status ?? 'open'" />
                <LockBadge :locked="event.status === 'locked' || event.is_locked" />
              </div>

              <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-text-muted">
                <span>📅 {{ formatDateTime(event.starts_at_utc ?? event.start_time ?? event.date) }}</span>
                <span v-if="event.ends_at_utc || event.end_time">→ {{ formatDateTime(event.ends_at_utc ?? event.end_time) }}</span>
                <RealmBadge v-if="event.realm_name || event.realm" :realm="event.realm_name ?? event.realm" />
              </div>

              <p v-if="event.instructions || event.description" class="mt-3 text-sm text-text-muted">
                {{ event.instructions ?? event.description }}
              </p>
            </div>

            <!-- Officer actions -->
            <div v-if="permissions.isOfficer.value" class="flex flex-wrap gap-2 flex-shrink-0">
              <WowButton variant="secondary" @click="openEditModal">Edit</WowButton>
              <WowButton variant="secondary" @click="toggleLock">
                {{ (event.status === 'locked' || event.is_locked) ? 'Unlock' : 'Lock' }}
              </WowButton>
              <WowButton variant="secondary" @click="doDuplicate">Duplicate</WowButton>
              <WowButton v-if="event.status !== 'completed'" variant="primary" @click="markComplete">
                Mark Done
              </WowButton>
              <WowButton variant="danger" @click="confirmCancel = true">Cancel Event</WowButton>
            </div>
          </div>
        </WowCard>

        <!-- Main content grid -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- Left column: signup form + composition -->
          <div class="space-y-6">
            <SignupForm
              v-if="event.status === 'open' || event.status === 'draft'"
              :event-id="event.id"
              :guild-id="guildId"
              :existing-signup="editingSignup"
              :signed-up-character-ids="mySignedUpCharacterIds"
              :banned-character-ids="bannedCharacterIds"
              :available-roles="availableRoles"
              :role-slot-info="roleSlotInfo"
              @signed-up="onSignedUp"
              @updated="onSignupUpdated"
            />
            <!-- My signups list for switching active character -->
            <WowCard v-if="mySignups.length > 0">
              <h3 class="wow-heading text-base mb-3">My Signups ({{ mySignups.length }})</h3>
              <div class="space-y-2">
                <div
                  v-for="s in mySignups"
                  :key="s.id"
                  class="space-y-2"
                >
                  <div
                    class="flex items-center gap-2 px-3 py-2 rounded border text-sm transition-colors"
                    :class="editingSignupId === s.id
                      ? 'border-accent-gold bg-accent-gold/10'
                      : 'border-border-default bg-bg-tertiary hover:border-border-gold'"
                  >
                    <span class="font-medium" :style="{ color: getClassColor(s.character?.class_name) }">
                      {{ s.character?.name ?? '?' }}
                    </span>
                    <span class="text-text-muted text-xs">{{ ROLE_LABEL_MAP[s.chosen_role] || s.chosen_role }} / {{ s.chosen_spec || '—' }}</span>
                    <span v-if="s.note" class="text-text-muted text-[10px] italic truncate max-w-[120px]" :title="s.note">📝 {{ s.note }}</span>
                    <span v-if="s.lineup_status === 'bench' || s.bench_info" class="text-[10px] font-semibold text-yellow-400 bg-yellow-400/10 px-1.5 py-0.5 rounded">
                      Bench{{ s.bench_info ? ' #' + s.bench_info.queue_position : '' }}
                    </span>
                    <span v-else-if="s.lineup_status === 'declined'" class="text-xs text-red-400">declined</span>
                    <span v-else class="text-xs text-green-400">in lineup</span>
                    <div class="ml-auto flex gap-1">
                      <button
                        v-if="event.status === 'open' || event.status === 'draft'"
                        class="text-xs px-2 py-0.5 rounded border border-border-default hover:border-accent-gold text-text-muted hover:text-accent-gold transition-colors"
                        @click="editingSignupId = editingSignupId === s.id ? null : s.id"
                      >
                        {{ editingSignupId === s.id ? 'Cancel Edit' : 'Edit' }}
                      </button>
                      <button
                        v-if="event.status === 'open' || event.status === 'draft'"
                        class="text-xs px-2 py-0.5 rounded border border-red-800 hover:border-red-500 text-red-400 hover:text-red-300 transition-colors"
                        @click="leaveRaid(s)"
                      >
                        Leave Raid
                      </button>
                    </div>
                  </div>
                  <!-- Pending character replacement request -->
                  <div
                    v-if="pendingReplacementForSignup(s.id)"
                    class="ml-4 px-3 py-2 rounded border border-blue-700 bg-blue-900/20 text-sm space-y-2"
                  >
                    <p class="text-blue-300 text-xs font-medium">⚡ Character Swap Requested</p>
                    <p class="text-text-muted text-xs">
                      <strong class="text-text-primary">{{ pendingReplacementForSignup(s.id).requester_name }}</strong>
                      wants to replace
                      <strong class="text-text-primary">{{ pendingReplacementForSignup(s.id).old_character?.name ?? '?' }}</strong>
                      with
                      <strong class="text-accent-gold">{{ pendingReplacementForSignup(s.id).new_character?.name ?? '?' }}</strong>
                      <span v-if="pendingReplacementForSignup(s.id).reason" class="italic"> — {{ pendingReplacementForSignup(s.id).reason }}</span>
                    </p>
                    <div class="flex gap-2">
                      <button
                        class="text-xs px-3 py-1 rounded border border-green-700 bg-green-900/20 hover:border-green-500 text-green-400 hover:text-green-300 transition-colors"
                        @click="resolveReplacement(pendingReplacementForSignup(s.id).id, 'confirm')"
                      >Confirm</button>
                      <button
                        class="text-xs px-3 py-1 rounded border border-red-700 bg-red-900/20 hover:border-red-500 text-red-400 hover:text-red-300 transition-colors"
                        @click="resolveReplacement(pendingReplacementForSignup(s.id).id, 'decline')"
                      >Decline</button>
                      <button
                        class="text-xs px-3 py-1 rounded border border-border-default hover:border-red-500 text-text-muted hover:text-red-300 transition-colors"
                        @click="leaveRaid(s)"
                      >Leave Raid</button>
                    </div>
                  </div>
                </div>
              </div>
              <button
                v-if="editingSignupId && (event.status === 'open' || event.status === 'draft')"
                class="mt-2 text-xs text-accent-gold hover:underline"
                @click="editingSignupId = null"
              >
                + Add another character
              </button>
            </WowCard>
            <CompositionSummary
              :lineup-counts="lineupCounts"
              :max-size="event.raid_size ?? event.size"
              :tank-slots="event.tank_slots ?? 0"
              :main-tank-slots="event.main_tank_slots ?? 1"
              :off-tank-slots="event.off_tank_slots ?? 1"
              :healer-slots="event.healer_slots ?? 5"
              :dps-slots="event.dps_slots ?? 18"
            />
          </div>

          <!-- Right columns: signup list + lineup -->
          <div class="lg:col-span-2 space-y-6">
            <SignupList
              :signups="signups"
              :is-officer="permissions.isOfficer.value"
              :guild-id="guildId"
              :event-id="event.id"
              :available-roles="availableRoles"
              @signup-updated="onSignupUpdated"
              @signup-removed="onSignupRemoved"
              @signup-error="msg => uiStore.showToast(msg, 'error')"
            />

            <LineupBoard
              :signups="signups"
              :event-id="event.id"
              :guild-id="guildId"
              :is-officer="permissions.isOfficer.value"
              :tank-slots="event.tank_slots ?? 0"
              :main-tank-slots="event.main_tank_slots ?? 1"
              :off-tank-slots="event.off_tank_slots ?? 1"
              :healer-slots="event.healer_slots ?? 5"
              :dps-slots="event.dps_slots ?? 18"
              @saved="onLineupSaved"
              @lineup-updated="onLineupUpdated"
            />
          </div>
        </div>
      </template>
    </div>

    <!-- Edit Event modal -->
    <WowModal v-model="showEditModal" title="Edit Event" size="md">
      <form @submit.prevent="saveEvent" class="space-y-4">
        <div>
          <label class="block text-xs text-text-muted mb-1">Title *</label>
          <input v-model="editForm.title" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Raid Definition</label>
          <select v-model.number="editForm.raid_definition_id" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" @change="onEditRaidDefChange">
            <option value="">None (use defaults)</option>
            <optgroup label="Built-in Raids">
              <option v-for="rd in editBuiltinDefs" :key="rd.id" :value="rd.id">{{ rd.name }} ({{ rd.default_raid_size ?? rd.size }}-man)</option>
            </optgroup>
            <optgroup v-if="editCustomDefs.length" label="Custom Raids">
              <option v-for="rd in editCustomDefs" :key="rd.id" :value="rd.id">{{ rd.name }} ({{ rd.default_raid_size ?? rd.size }}-man)</option>
            </optgroup>
          </select>
          <p class="text-[10px] text-text-muted mt-1">Manage custom raids in <router-link to="/guild/raid-definitions" class="text-accent-gold hover:underline">Raid Definitions</router-link></p>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">Size</label>
            <select v-model.number="editForm.raid_size" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option :value="10">10-man</option>
              <option :value="25">25-man</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Difficulty</label>
            <select v-model="editForm.difficulty" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="normal">Normal</option>
              <option value="heroic">Heroic</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Status</label>
            <select v-model="editForm.status" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="draft">Draft</option>
              <option value="open">Open</option>
              <option value="locked">Locked</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">Date &amp; Time *</label>
            <input v-model="editForm.starts_at_utc" type="datetime-local" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Close Signups At</label>
            <input v-model="editForm.close_signups_at" type="datetime-local" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
            <span class="text-[10px] text-text-muted">Must be before event start time</span>
          </div>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Instructions</label>
          <textarea v-model="editForm.instructions" rows="2" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none resize-none" />
        </div>
        <div v-if="editError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ editError }}</div>
      </form>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showEditModal = false">Cancel</WowButton>
          <WowButton :loading="actionLoading" @click="saveEvent">Save</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Cancel confirmation modal -->
    <WowModal v-model="confirmCancel" title="Cancel Event" size="sm">
      <p class="text-text-muted mb-4">Are you sure you want to cancel this event? This cannot be undone.</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="confirmCancel = false">Nevermind</WowButton>
          <WowButton variant="danger" :loading="actionLoading" @click="cancelEvent">Cancel Event</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Leave Raid confirmation modal -->
    <WowModal v-model="showLeaveModal" title="Leave Raid" size="sm">
      <p class="text-text-muted">
        Are you sure you want to remove
        <strong class="text-text-primary">{{ leaveSignup?.character?.name ?? 'this character' }}</strong>
        from this raid? This will remove the character from the signup list and lineup.
      </p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showLeaveModal = false">Cancel</WowButton>
          <WowButton variant="danger" :loading="actionLoading" @click="confirmLeaveRaid">Leave Raid</WowButton>
        </div>
      </template>
    </WowModal>
  </AppShell>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import RaidSizeBadge from '@/components/common/RaidSizeBadge.vue'
import RealmBadge from '@/components/common/RealmBadge.vue'
import LockBadge from '@/components/common/LockBadge.vue'
import SignupForm from '@/components/raids/SignupForm.vue'
import SignupList from '@/components/raids/SignupList.vue'
import CompositionSummary from '@/components/raids/CompositionSummary.vue'
import LineupBoard from '@/components/raids/LineupBoard.vue'
import { useGuildStore } from '@/stores/guild'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { usePermissions } from '@/composables/usePermissions'
import { useWowIcons } from '@/composables/useWowIcons'
import { useSocket } from '@/composables/useSocket'
import { RAID_TYPES } from '@/constants'
import * as eventsApi from '@/api/events'
import * as signupsApi from '@/api/signups'
import * as raidDefsApi from '@/api/raidDefinitions'

const route = useRoute()
const router = useRouter()
const guildStore = useGuildStore()
const authStore = useAuthStore()
const uiStore = useUiStore()
const permissions = usePermissions()
const { getRaidIcon } = useWowIcons()
const { getClassColor } = useWowIcons()
const { joinEvent, leaveEvent, on: socketOn, off: socketOff } = useSocket()

const event = ref(null)
const signups = ref([])
const lineupCounts = ref(null)
const loading = ref(true)
const error = ref(null)
const actionLoading = ref(false)
const confirmCancel = ref(false)
const showEditModal = ref(false)
const showLeaveModal = ref(false)
const leaveSignup = ref(null)
const editError = ref(null)
const editingSignupId = ref(null)
const raidTypes = RAID_TYPES
const ROLE_LABEL_MAP = { tank: 'Melee DPS', main_tank: 'Main Tank', off_tank: 'Off Tank', healer: 'Heal', dps: 'Range DPS' }
const editRaidDefs = ref([])
const editBuiltinDefs = computed(() => editRaidDefs.value.filter(d => d.is_builtin))
const editCustomDefs = computed(() => editRaidDefs.value.filter(d => !d.is_builtin))

// Character replacement requests
const replacementRequests = ref([])

const editForm = reactive({
  title: '',
  raid_type: '',
  raid_definition_id: '',
  raid_size: 25,
  difficulty: 'normal',
  status: 'open',
  starts_at_utc: '',
  close_signups_at: '',
  instructions: ''
})

const guildId = computed(() => guildStore.currentGuild?.id)

const mySignups = computed(() => {
  if (!authStore.user) return []
  return signups.value.filter(s => s.user_id === authStore.user.id)
})

const editingSignup = computed(() => {
  if (!editingSignupId.value) return null
  return mySignups.value.find(s => s.id === editingSignupId.value) ?? null
})

const mySignedUpCharacterIds = computed(() =>
  mySignups.value.map(s => s.character_id)
)

const bans = ref([])
const bannedCharacterIds = computed(() =>
  bans.value.map(b => b.character_id)
)

const availableRoles = computed(() => {
  if (!event.value) return ['main_tank', 'off_tank', 'tank', 'healer', 'dps']
  const roles = []
  if ((event.value.main_tank_slots ?? 1) > 0) roles.push('main_tank')
  if ((event.value.off_tank_slots ?? 1) > 0) roles.push('off_tank')
  if ((event.value.tank_slots ?? 0) > 0) roles.push('tank')
  if ((event.value.healer_slots ?? 5) > 0) roles.push('healer')
  if ((event.value.dps_slots ?? 18) > 0) roles.push('dps')
  return roles
})

// Live role slot info: max slots, current going count, and remaining for each role
const roleSlotInfo = computed(() => {
  if (!event.value) return {}
  const slotMap = {
    main_tank: event.value.main_tank_slots ?? 1,
    off_tank:  event.value.off_tank_slots ?? 1,
    tank:      event.value.tank_slots ?? 0,
    healer:    event.value.healer_slots ?? 5,
    dps:       event.value.dps_slots ?? 18,
  }
  const info = {}
  for (const [role, max] of Object.entries(slotMap)) {
    if (max <= 0) continue
    const current = signups.value.filter(s => s.chosen_role === role && s.lineup_status !== 'declined').length
    info[role] = { max, current, remaining: Math.max(0, max - current) }
  }
  return info
})

onMounted(async () => {
  loading.value = true
  error.value = null
  try {
    if (!guildStore.currentGuild) await guildStore.fetchGuilds()
    const [ev, su] = await Promise.all([
      eventsApi.getEvent(guildId.value, route.params.id),
      signupsApi.getSignups(guildId.value, route.params.id),
      guildStore.members.length === 0 && guildId.value ? guildStore.fetchMembers(guildId.value) : Promise.resolve()
    ])
    event.value = ev
    signups.value = su
    // Fetch bans for this event
    try { bans.value = await signupsApi.getBans(guildId.value, route.params.id) } catch { bans.value = [] }
    // Fetch pending character replacement requests
    await loadReplacementRequests()
  } catch (err) {
    error.value = err?.response?.data?.message ?? 'Failed to load raid details'
  } finally {
    loading.value = false
  }
  // Join Socket.IO room for real-time updates
  if (event.value) joinEvent(event.value.id)
  socketOn('signups_changed', onSignupsChanged)
  socketOn('lineup_changed', onLineupChanged)
  // Fallback polling in case WebSocket disconnects
  startPolling()
  document.addEventListener('visibilitychange', onVisibilityChange)
})

// ── Real-time: WebSocket handlers ──
async function onSignupsChanged(data) {
  if (!guildId.value || !event.value) return
  if (data?.event_id !== event.value.id) return
  try {
    signups.value = await signupsApi.getSignups(guildId.value, event.value.id)
    await loadReplacementRequests()
  } catch {
    // Silently ignore — next WS event or poll will retry
  }
}

async function onLineupChanged(data) {
  // LineupBoard manages its own state; just trigger a signups reload
  // so role slot info and signup list stay in sync
  if (!guildId.value || !event.value) return
  if (data?.event_id !== event.value.id) return
  try {
    signups.value = await signupsApi.getSignups(guildId.value, event.value.id)
  } catch {
    // Silently ignore
  }
}

// ── Fallback polling: only active when tab is visible, longer interval ──
const POLL_INTERVAL = 30_000 // 30 seconds (fallback only — WebSocket is primary)
let pollTimer = null

function startPolling() {
  stopPolling()
  pollTimer = setInterval(pollSignups, POLL_INTERVAL)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

function onVisibilityChange() {
  if (document.hidden) {
    stopPolling()
  } else {
    pollSignups()
    startPolling()
  }
}

async function pollSignups() {
  if (!guildId.value || !event.value) return
  try {
    const su = await signupsApi.getSignups(guildId.value, event.value.id)
    signups.value = su
  } catch {
    // Silently ignore polling errors
  }
}

onUnmounted(() => {
  socketOff('signups_changed', onSignupsChanged)
  socketOff('lineup_changed', onLineupChanged)
  if (event.value) leaveEvent(event.value.id)
  stopPolling()
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

// Reload everything when navigating between events (same route, different id)
watch(() => route.params.id, async (newId, oldId) => {
  if (!newId || newId === oldId) return
  // Leave old room, join new room
  if (oldId) leaveEvent(oldId)
  stopPolling()
  loading.value = true
  error.value = null
  editingSignupId.value = null
  lineupCounts.value = null
  try {
    const [ev, su] = await Promise.all([
      eventsApi.getEvent(guildId.value, newId),
      signupsApi.getSignups(guildId.value, newId),
    ])
    event.value = ev
    signups.value = su
  } catch (err) {
    error.value = err?.response?.data?.message ?? 'Failed to load raid details'
  } finally {
    loading.value = false
  }
  if (event.value) joinEvent(event.value.id)
  startPolling()
})

async function toggleLock() {
  if (!event.value) return
  actionLoading.value = true
  try {
    const isLocked = event.value.status === 'locked' || event.value.is_locked
    if (isLocked) {
      const updated = await eventsApi.unlockEvent(guildId.value, event.value.id)
      event.value = updated
    } else {
      const updated = await eventsApi.lockEvent(guildId.value, event.value.id)
      event.value = updated
    }
    const nowLocked = event.value.status === 'locked'
    uiStore.showToast(`Event ${nowLocked ? 'locked' : 'unlocked'}`, 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.message ?? 'Action failed', 'error')
  } finally {
    actionLoading.value = false
  }
}

async function markComplete() {
  actionLoading.value = true
  try {
    await eventsApi.completeEvent(guildId.value, event.value.id)
    event.value.status = 'completed'
    uiStore.showToast('Event marked as completed!', 'success')
  } catch {
    uiStore.showToast('Failed to complete event', 'error')
  } finally {
    actionLoading.value = false
  }
}

async function cancelEvent() {
  actionLoading.value = true
  try {
    await eventsApi.cancelEvent(guildId.value, event.value.id)
    event.value.status = 'cancelled'
    confirmCancel.value = false
    uiStore.showToast('Event cancelled', 'warning')
  } catch {
    uiStore.showToast('Failed to cancel event', 'error')
  } finally {
    actionLoading.value = false
  }
}

async function doDuplicate() {
  actionLoading.value = true
  try {
    const newEvent = await eventsApi.duplicateEvent(guildId.value, event.value.id)
    uiStore.showToast('Event duplicated! Redirecting…', 'success')
    router.push({ name: 'raid-detail', params: { id: newEvent.id } })
  } catch {
    uiStore.showToast('Failed to duplicate event', 'error')
  } finally {
    actionLoading.value = false
  }
}

function toLocalDatetime(utcStr) {
  if (!utcStr) return ''
  const d = new Date(utcStr)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function openEditModal() {
  if (!event.value) return
  Object.assign(editForm, {
    title: event.value.title ?? '',
    raid_type: event.value.raid_type ?? '',
    raid_definition_id: event.value.raid_definition_id ?? '',
    raid_size: event.value.raid_size ?? event.value.size ?? 25,
    difficulty: event.value.difficulty ?? 'normal',
    status: event.value.status ?? 'open',
    starts_at_utc: toLocalDatetime(event.value.starts_at_utc ?? event.value.start_time),
    close_signups_at: toLocalDatetime(event.value.close_signups_at),
    instructions: event.value.instructions ?? event.value.description ?? ''
  })
  editError.value = null
  showEditModal.value = true
  // Fetch raid definitions
  if (guildId.value) {
    raidDefsApi.getRaidDefinitions(guildId.value).then(defs => { editRaidDefs.value = defs }).catch(err => { console.warn('Failed to load raid definitions', err) })
  }
}

function onEditRaidDefChange() {
  const rd = editRaidDefs.value.find(d => d.id === editForm.raid_definition_id)
  if (rd) {
    editForm.raid_type = rd.raid_type || rd.code || ''
    editForm.raid_size = rd.default_raid_size ?? rd.size ?? 25
  }
}

async function saveEvent() {
  if (actionLoading.value) return
  if (!editForm.title || !editForm.starts_at_utc) {
    editError.value = 'Title and date are required'
    return
  }
  if (editForm.close_signups_at && new Date(editForm.close_signups_at) >= new Date(editForm.starts_at_utc)) {
    editError.value = 'Close signups time must be before the event start time'
    return
  }
  editError.value = null
  actionLoading.value = true
  try {
    const payload = {
      title: editForm.title,
      raid_type: editForm.raid_type || undefined,
      raid_definition_id: editForm.raid_definition_id || undefined,
      raid_size: editForm.raid_size,
      difficulty: editForm.difficulty,
      status: editForm.status,
      starts_at_utc: editForm.starts_at_utc,
      close_signups_at: editForm.close_signups_at || undefined,
      instructions: editForm.instructions
    }
    const updated = await eventsApi.updateEvent(guildId.value, event.value.id, payload)
    event.value = updated
    showEditModal.value = false
    uiStore.showToast('Event updated!', 'success')
  } catch (err) {
    editError.value = err?.response?.data?.error ?? err?.response?.data?.message ?? 'Failed to update event'
  } finally {
    actionLoading.value = false
  }
}

function onSignedUp(signup) {
  signups.value.push(signup)
  uiStore.showToast('Signed up successfully!', 'success')
}

function leaveRaid(signup) {
  leaveSignup.value = signup
  showLeaveModal.value = true
}

async function confirmLeaveRaid() {
  if (!leaveSignup.value) return
  const signupId = leaveSignup.value.id
  actionLoading.value = true
  try {
    await signupsApi.deleteSignup(guildId.value, event.value.id, signupId)
    showLeaveModal.value = false
    if (editingSignupId.value === signupId) {
      editingSignupId.value = null
    }
    leaveSignup.value = null
    // Reload signups to reflect auto-promote changes
    try {
      signups.value = await signupsApi.getSignups(guildId.value, event.value.id)
    } catch (err) {
      console.warn('Failed to reload signups', err)
      signups.value = signups.value.filter(s => s.id !== signupId)
    }
    uiStore.showToast('You have left the raid', 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.message ?? 'Failed to leave raid', 'error')
  } finally {
    actionLoading.value = false
  }
}

async function onSignupUpdated(updated) {
  // Reload all signups to reflect auto-promote changes from backend
  try {
    signups.value = await signupsApi.getSignups(guildId.value, event.value.id)
  } catch (err) {
    console.warn('Failed to reload signups, using local update', err)
    const idx = signups.value.findIndex(s => s.id === updated.id)
    if (idx !== -1) signups.value[idx] = updated
  }
  uiStore.showToast('Signup updated!', 'success')
  editingSignupId.value = null
}

async function onSignupRemoved(signupId) {
  // Reload all signups to reflect auto-promote changes from backend
  try {
    signups.value = await signupsApi.getSignups(guildId.value, event.value.id)
  } catch (err) {
    console.warn('Failed to reload signups, using local filter', err)
    signups.value = signups.value.filter(s => s.id !== signupId)
  }
  // Refresh bans in case a permanent kick was applied
  try { bans.value = await signupsApi.getBans(guildId.value, event.value.id) } catch { /* ignore */ }
  uiStore.showToast('Signup removed', 'success')
}

async function onLineupSaved(payload) {
  // Reload signups so role changes from drag-and-drop are reflected in the signup list
  try {
    signups.value = await signupsApi.getSignups(guildId.value, event.value.id)
  } catch (err) {
    console.warn('Failed to reload signups after lineup save', err)
  }
  if (!payload?.auto) {
    uiStore.showToast('Lineup saved!', 'success')
  }
}

function onLineupUpdated(counts) {
  lineupCounts.value = counts
}

// --- Character replacement requests ---
function pendingReplacementForSignup(signupId) {
  return replacementRequests.value.find(r => r.signup_id === signupId) ?? null
}

async function loadReplacementRequests() {
  if (!guildId.value || !event.value) return
  try {
    replacementRequests.value = await signupsApi.getMyReplacementRequests(guildId.value, event.value.id)
  } catch {
    replacementRequests.value = []
  }
}

async function resolveReplacement(requestId, action) {
  if (!guildId.value || !event.value) return
  try {
    await signupsApi.resolveReplaceRequest(guildId.value, event.value.id, requestId, { action })
    // Reload signups and replacement requests
    signups.value = await signupsApi.getSignups(guildId.value, event.value.id)
    await loadReplacementRequests()
    uiStore.showToast(
      action === 'confirm' ? 'Character swap confirmed!' : 'Character swap declined.',
      action === 'confirm' ? 'success' : 'info'
    )
  } catch (err) {
    uiStore.showToast(err?.response?.data?.message ?? 'Failed to process replacement', 'error')
  }
}

function formatDateTime(d) {
  if (!d) return '?'
  return new Date(d).toLocaleString('en-GB', {
    weekday: 'long', day: '2-digit', month: 'long',
    year: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}
</script>
