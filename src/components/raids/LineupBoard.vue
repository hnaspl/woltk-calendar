<template>
  <WowCard :padded="false">
    <div class="flex items-center justify-between px-5 py-3 border-b border-border-default">
      <h3 class="wow-heading text-base">Lineup Board</h3>
      <div v-if="isOfficer" class="flex items-center gap-2">
        <span v-if="dirty" class="text-xs text-yellow-400">Unsaved changes</span>
        <WowButton variant="secondary" @click="saveLineup" :loading="saving" class="text-xs py-1 px-3">
          Save Lineup
        </WowButton>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-px bg-border-default" :class="gridClass">
      <div
        v-for="col in columns"
        :key="col.key"
        class="bg-bg-secondary p-4 transition-colors"
        :class="{ 'bg-accent-gold/5 ring-1 ring-inset ring-accent-gold/30': isOfficer && dragOverTarget === col.key }"
        @dragover.prevent="isOfficer && handleDragOver($event, col.key)"
        @dragenter.prevent="isOfficer && (dragOverTarget = col.key)"
        @dragleave="isOfficer && handleDragLeave($event, col.key)"
        @drop.prevent="isOfficer && onDropColumn($event, col.key)"
      >
        <div class="flex items-center gap-2 mb-3">
          <img :src="getRoleIcon(col.role)" class="w-5 h-5 rounded" :alt="col.label" />
          <span :class="col.labelClass" class="font-semibold text-sm">{{ col.label }}</span>
          <span class="ml-auto text-xs" :class="lineup[col.key].length >= col.slots ? 'text-red-400 font-semibold' : 'text-text-muted'">{{ lineup[col.key].length }} / {{ col.slots }}</span>
        </div>
        <div class="space-y-1.5 min-h-[2rem]">
          <!-- Assigned slots -->
          <CharacterTooltip
            v-for="(s, i) in lineup[col.key]"
            :key="s.id"
            :character="s.character"
            position="bottom"
          >
            <div
              class="flex items-center gap-2 px-2 py-1.5 rounded bg-bg-primary border border-border-default group hover:border-border-gold transition-colors"
              :class="{ 'cursor-grab active:cursor-grabbing': isOfficer, 'opacity-50': draggedId === s.id }"
              :draggable="isOfficer"
              @dragstart="onDragStart($event, s, col.key, i)"
              @dragend="onDragEnd"
            >
              <img
                :src="getClassIcon(s.character?.class_name)"
                :alt="s.character?.class_name ?? ''"
                class="w-6 h-6 rounded flex-shrink-0"
                loading="lazy"
              />
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1">
                  <span
                    class="text-xs font-medium truncate"
                    :style="{ color: getClassColor(s.character?.class_name) ?? '#ccc' }"
                  >{{ s.character?.name ?? '?' }}</span>
                  <span v-if="s.character?.metadata?.level" class="text-[10px] text-text-muted">
                    Lv{{ s.character.metadata.level }}
                  </span>
                </div>
                <div class="flex items-center gap-1 text-[10px] text-text-muted">
                  <span v-if="s.chosen_spec" class="text-amber-300">{{ s.chosen_spec }}</span>
                  <span v-if="profString(s)">{{ profString(s) }}</span>
                </div>
              </div>
              <button
                v-if="isOfficer"
                type="button"
                class="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition-all"
                @click="removeFromRole(col.key, i)"
              >×</button>
            </div>
          </CharacterTooltip>

        </div>
      </div>
    </div>

    <!-- Bench queue: ordered list of players waiting for a slot -->
    <div
      v-if="bench.length > 0 || (isOfficer && draggedId)"
      class="px-5 py-4 border-t border-border-default transition-colors"
      :class="{ 'bg-yellow-900/10 ring-1 ring-inset ring-yellow-500/30': isOfficer && dragOverTarget === 'bench' }"
      @dragover.prevent="isOfficer && handleDragOver($event, 'bench')"
      @dragenter.prevent="isOfficer && (dragOverTarget = 'bench')"
      @dragleave="isOfficer && handleDragLeave($event, 'bench')"
      @drop.prevent="isOfficer && onDropBench()"
    >
      <p class="text-xs text-yellow-400/80 mb-2 uppercase tracking-wider">Bench Queue ({{ bench.length }})</p>
      <div class="flex flex-wrap gap-2">
        <CharacterTooltip
          v-for="(s, i) in bench"
          :key="s.id"
          :character="s.character"
          position="top"
        >
          <div
            class="flex items-center gap-1.5 px-2 py-1 rounded bg-bg-tertiary text-xs border border-yellow-700/40 hover:border-yellow-500 transition-colors"
            :class="{
              'cursor-grab active:cursor-grabbing': isOfficer,
              'opacity-50': draggedId === s.id
            }"
            :draggable="isOfficer"
            @dragstart="onDragStart($event, s, 'bench', -1)"
            @dragend="onDragEnd"
          >
            <span class="text-[10px] text-yellow-400 font-bold w-4 text-center">#{{ i + 1 }}</span>
            <ClassBadge v-if="s.character?.class_name" :class-name="s.character.class_name" />
            <span>{{ s.character?.name ?? '?' }}</span>
            <span class="text-text-muted">({{ ROLE_LABEL_MAP[s.chosen_role] ?? s.chosen_role }})</span>
            <span v-if="s.character?.metadata?.level" class="text-[10px] text-text-muted">
              Lv{{ s.character.metadata.level }}
            </span>
          </div>
        </CharacterTooltip>
      </div>
      <p v-if="bench.length === 0 && draggedId" class="text-xs text-yellow-400/60 italic">
        Drop here to move to bench
      </p>
    </div>

  </WowCard>

  <!-- Role change confirmation modal -->
  <WowModal v-model="showRoleChangeModal" title="Change Player Role?" size="sm">
    <div v-if="roleChangePending" class="space-y-3">
      <p class="text-text-muted text-sm">
        <strong class="text-text-primary">{{ roleChangePending.signup.character?.name ?? 'Player' }}</strong>
        is signed up as
        <strong class="text-accent-gold">{{ ROLE_LABEL_MAP[roleChangePending.signup.chosen_role] ?? roleChangePending.signup.chosen_role }}</strong>.
      </p>
      <p class="text-text-muted text-sm">
        Do you want to change their role to
        <strong class="text-accent-gold">{{ roleChangePending.targetCol.label }}</strong>
        and place them in the lineup?
      </p>
      <p class="text-xs text-yellow-400/80">
        This will update their signup role and move them into the {{ roleChangePending.targetCol.label }} column.
      </p>
    </div>
    <template #footer>
      <div class="flex justify-end gap-3">
        <WowButton variant="secondary" @click="cancelRoleChange">Leave on Bench</WowButton>
        <WowButton variant="primary" @click="confirmRoleChange">Change Role &amp; Place</WowButton>
      </div>
    </template>
  </WowModal>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import ClassBadge from '@/components/common/ClassBadge.vue'
import CharacterTooltip from '@/components/common/CharacterTooltip.vue'
import * as lineupApi from '@/api/lineup'
import { useWowIcons } from '@/composables/useWowIcons'
import { useDragDrop } from '@/composables/useDragDrop'
import { useSocket } from '@/composables/useSocket'
import { useUiStore } from '@/stores/ui'

const props = defineProps({
  signups:        { type: Array,          default: () => [] },
  eventId:        { type: [Number,String], required: true },
  guildId:        { type: [Number,String], required: true },
  isOfficer:      { type: Boolean, default: false },
  tankSlots:      { type: Number, default: 0 },
  mainTankSlots:  { type: Number, default: 1 },
  offTankSlots:   { type: Number, default: 1 },
  healerSlots:    { type: Number, default: 5 },
  dpsSlots:       { type: Number, default: 18 }
})

const emit = defineEmits(['saved', 'lineup-updated'])
const { getClassIcon, getClassColor, getRoleIcon } = useWowIcons()
const {
  draggedId, dragSourceKey, dragSourceIndex, dragOverTarget,
  isDragging, startDrag, endDrag, handleDragOver, handleDragLeave,
} = useDragDrop()
const uiStore = useUiStore()
const saving = ref(false)
const dirty = ref(false)
const lineupVersion = ref(null)
const benchQueue = ref([]) // Ordered list of bench signup objects from API

// Role change confirmation modal state
const showRoleChangeModal = ref(false)
const roleChangePending = ref(null) // { signup, targetKey, targetCol }

const ROLE_LABEL_MAP = { tank: 'Tank', main_tank: 'Main Tank', off_tank: 'Off Tank', healer: 'Healer', dps: 'DPS' }

const allColumns = computed(() => [
  { key: 'main_tanks', role: 'main_tank', label: 'Main Tank',  labelClass: 'text-blue-200', slots: props.mainTankSlots },
  { key: 'off_tanks',  role: 'off_tank',  label: 'Off Tank',   labelClass: 'text-cyan-300',  slots: props.offTankSlots },
  { key: 'tanks',      role: 'tank',      label: 'Tanks',      labelClass: 'text-blue-300',  slots: props.tankSlots },
  { key: 'healers',    role: 'healer',    label: 'Healers',    labelClass: 'text-green-300', slots: props.healerSlots },
  { key: 'dps',        role: 'dps',       label: 'DPS',        labelClass: 'text-red-300',   slots: props.dpsSlots },
])

/** Only show columns that have at least 1 slot configured */
const columns = computed(() => allColumns.value.filter(c => c.slots > 0))

const gridClass = computed(() => {
  const count = columns.value.length
  if (count <= 2) return 'md:grid-cols-2'
  if (count === 3) return 'md:grid-cols-3'
  if (count === 4) return 'md:grid-cols-4'
  return 'md:grid-cols-5'
})

const lineup = ref({ main_tanks: [], off_tanks: [], tanks: [], healers: [], dps: [] })

// ── Drag handlers (state managed by useDragDrop composable) ──

function onDragStart(e, signup, sourceKey, idx) {
  if (!props.isOfficer) {
    e.preventDefault()
    return
  }
  startDrag(e, signup.id, sourceKey, idx)
}

function onDragEnd() {
  endDrag()
}

function findSignupById(id) {
  for (const key of ['main_tanks', 'off_tanks', 'tanks', 'healers', 'dps']) {
    const idx = lineup.value[key].findIndex(s => Number(s.id) === id)
    if (idx !== -1) return { key, idx, signup: lineup.value[key][idx] }
  }
  const fromPool = bench.value.find(s => Number(s.id) === id)
  if (fromPool) return { key: 'bench', idx: -1, signup: fromPool }
  return null
}

function onDropColumn(e, targetKey) {
  dragOverTarget.value = null
  // Use Vue reactive state as primary source; dataTransfer as fallback
  const rawId = draggedId.value || e.dataTransfer.getData('text/plain')
  const id = Number(rawId)
  if (!id) return

  const found = findSignupById(id)
  if (!found) return

  const col = allColumns.value.find(c => c.key === targetKey)
  const signupRole = found.signup.chosen_role

  // Role mismatch: show confirmation modal to change role
  if (col && signupRole !== col.role) {
    roleChangePending.value = { signup: found.signup, sourceKey: found.key, sourceIdx: found.idx, targetKey, targetCol: col }
    showRoleChangeModal.value = true
    return
  }

  // Overflow protection: check if target column is full
  if (col) {
    const currentCount = lineup.value[targetKey].length
    const alreadyInTarget = lineup.value[targetKey].find(s => Number(s.id) === id)
    if (!alreadyInTarget && currentCount >= col.slots) {
      uiStore.showToast(`${col.label} slots are full (${currentCount}/${col.slots}). Remove someone first.`, 'error')
      return
    }
  }

  // Remove from source column (column-to-column moves)
  if (found.key !== 'bench') {
    lineup.value[found.key].splice(found.idx, 1)
  }

  // Remove from bench queue when moving to a role column
  benchQueue.value = benchQueue.value.filter(s => Number(s.id) !== id)

  // Add to target (avoid duplicates)
  if (!lineup.value[targetKey].find(s => Number(s.id) === id)) {
    lineup.value[targetKey].push(found.signup)
  }
  dirty.value = true
  autoSave()
}

function onDropBench() {
  dragOverTarget.value = null
  const sourceKey = dragSourceKey.value
  const sourceIdx = dragSourceIndex.value

  // Only act when dragged from a role column (remove from lineup, add to end of bench queue)
  if (sourceKey && sourceKey !== 'bench' && sourceIdx >= 0) {
    const removed = lineup.value[sourceKey][sourceIdx]
    lineup.value[sourceKey].splice(sourceIdx, 1)
    // Add to end of bench queue
    if (removed) {
      const id = Number(removed.id)
      benchQueue.value = benchQueue.value.filter(s => Number(s.id) !== id)
      benchQueue.value.push(removed)
    }
    dirty.value = true
    autoSave()
  }
}

// ── Role change confirmation handlers ──
function confirmRoleChange() {
  const pending = roleChangePending.value
  if (!pending) return

  const { signup, sourceKey, sourceIdx, targetKey, targetCol } = pending

  // Overflow check
  const currentCount = lineup.value[targetKey].length
  if (currentCount >= targetCol.slots) {
    uiStore.showToast(`${targetCol.label} slots are full (${currentCount}/${targetCol.slots}). Remove someone first.`, 'error')
    showRoleChangeModal.value = false
    roleChangePending.value = null
    return
  }

  // Remove from source column if coming from a role column
  if (sourceKey !== 'bench' && sourceIdx >= 0) {
    lineup.value[sourceKey].splice(sourceIdx, 1)
  }

  // Remove from bench queue when placing in a role column
  const id = Number(signup.id)
  benchQueue.value = benchQueue.value.filter(s => Number(s.id) !== id)

  // Add to target (avoid duplicates)
  if (!lineup.value[targetKey].find(s => Number(s.id) === id)) {
    lineup.value[targetKey].push(signup)
  }

  dirty.value = true
  autoSave()
  showRoleChangeModal.value = false
  roleChangePending.value = null
}

function cancelRoleChange() {
  showRoleChangeModal.value = false
  roleChangePending.value = null
}

// ── Auto-save on DnD ──
let autoSaveTimer = null
function autoSave() {
  clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => saveLineup(true), 300)
}

// ── Enforce slot limits: move excess players back to bench ──
function enforceSlotLimits() {
  let changed = false
  for (const col of allColumns.value) {
    if (col.slots > 0 && lineup.value[col.key].length > col.slots) {
      // Trim excess from the end
      lineup.value[col.key] = lineup.value[col.key].slice(0, col.slots)
      changed = true
    }
  }
  if (changed) {
    dirty.value = true
    autoSave()
  }
}

// ── Data loading ──
async function loadLineup() {
  try {
    const data = await lineupApi.getLineup(props.guildId, props.eventId)
    // Guard: skip applying server data if user made DnD changes while request was in flight
    if (dirty.value) return
    lineup.value.main_tanks = data.main_tanks ?? []
    lineup.value.off_tanks  = data.off_tanks  ?? []
    lineup.value.tanks      = data.tanks      ?? []
    lineup.value.healers    = data.healers    ?? []
    lineup.value.dps        = data.dps        ?? []
    benchQueue.value        = data.bench_queue ?? []
    lineupVersion.value     = data.version ?? null
    enforceSlotLimits()
  } catch {
    autoPopulateFromSignups()
  }
}

const { on: socketOn, off: socketOff } = useSocket()

onMounted(() => {
  loadLineup()
  // Listen for real-time lineup changes from other clients
  socketOn('lineup_changed', onLineupSocketUpdate)
  // Fallback polling at a longer interval
  startLineupPolling()
})

onUnmounted(() => {
  socketOff('lineup_changed', onLineupSocketUpdate)
  stopLineupPolling()
  clearTimeout(autoSaveTimer)
})

function onLineupSocketUpdate(data) {
  if (data?.event_id !== Number(props.eventId)) return
  if (!dirty.value) loadLineup()
}

// ── Fallback lineup polling (longer interval, WebSocket is primary) ──
const LINEUP_POLL_INTERVAL = 30_000
let lineupPollTimer = null

function startLineupPolling() {
  stopLineupPolling()
  lineupPollTimer = setInterval(() => {
    if (!dirty.value) loadLineup()
  }, LINEUP_POLL_INTERVAL)
}

function stopLineupPolling() {
  if (lineupPollTimer) { clearInterval(lineupPollTimer); lineupPollTimer = null }
}

watch(
  () => props.signups.map(s => `${s.id}:${s.status}:${s.chosen_role}`).join(','),
  () => {
    // Skip reload when there are unsaved DnD changes to avoid overwriting them
    if (!dirty.value) loadLineup()
  }
)

// After DnD auto-save completes, reload lineup to pick up any changes
// that arrived via polling while dirty was true
watch(dirty, (isDirty, wasDirty) => {
  if (wasDirty && !isDirty) loadLineup()
})

function autoPopulateFromSignups() {
  const going = props.signups.filter(s => s.status === 'going')
  lineup.value.main_tanks = going.filter(s => s.chosen_role === 'main_tank')
  lineup.value.off_tanks  = going.filter(s => s.chosen_role === 'off_tank')
  lineup.value.tanks      = going.filter(s => s.chosen_role === 'tank')
  lineup.value.healers    = going.filter(s => s.chosen_role === 'healer')
  lineup.value.dps        = going.filter(s => s.chosen_role === 'dps')
  enforceSlotLimits()
}

// ── Computed helpers ──
const activeSignups = computed(() =>
  props.signups.filter(s => ['going', 'tentative', 'bench'].includes(s.status))
)

const assignedIds = computed(() => {
  const ids = new Set()
  ;['main_tanks', 'off_tanks', 'tanks', 'healers', 'dps'].forEach(k =>
    lineup.value[k].forEach(s => ids.add(Number(s.id)))
  )
  return ids
})

// Emit lineup counts so CompositionSummary can reflect the Lineup Board
const lineupCounts = computed(() => ({
  main_tank: lineup.value.main_tanks.length,
  off_tank:  lineup.value.off_tanks.length,
  tank:      lineup.value.tanks.length,
  healer:    lineup.value.healers.length,
  dps:       lineup.value.dps.length,
}))

watch(lineupCounts, (counts) => {
  emit('lineup-updated', counts)
}, { deep: true, immediate: true })

const bench = computed(() => {
  const allUnassigned = activeSignups.value.filter(s => !assignedIds.value.has(Number(s.id)))
  const unassignedMap = new Map(allUnassigned.map(s => [Number(s.id), s]))

  // Start with bench queue order (use fresh signup data for display)
  const ordered = []
  for (const bq of benchQueue.value) {
    const fresh = unassignedMap.get(Number(bq.id))
    if (fresh) {
      ordered.push(fresh)
      unassignedMap.delete(Number(bq.id))
    }
  }

  // Append any remaining unassigned players not yet in queue (new signups)
  for (const s of unassignedMap.values()) {
    ordered.push(s)
  }

  return ordered
})

function profString(s) {
  return (s.character?.metadata?.professions ?? []).map(p => p.name).join(', ')
}

function removeFromRole(key, index) {
  const removed = lineup.value[key][index]
  lineup.value[key].splice(index, 1)
  // Add to end of bench queue
  if (removed) {
    const id = Number(removed.id)
    benchQueue.value = benchQueue.value.filter(s => Number(s.id) !== id)
    benchQueue.value.push(removed)
  }
  dirty.value = true
  autoSave()
}

async function saveLineup(auto = false) {
  if (saving.value) return
  saving.value = true
  try {
    const result = await lineupApi.saveLineup(props.guildId, props.eventId, {
      main_tanks: lineup.value.main_tanks.map(s => s.id),
      off_tanks:  lineup.value.off_tanks.map(s => s.id),
      tanks:      lineup.value.tanks.map(s => s.id),
      healers:    lineup.value.healers.map(s => s.id),
      dps:        lineup.value.dps.map(s => s.id),
      bench_queue: bench.value.map(s => s.id),
      version:    lineupVersion.value,
    })
    // Update local state from server response
    lineup.value.main_tanks = result.main_tanks ?? []
    lineup.value.off_tanks  = result.off_tanks  ?? []
    lineup.value.tanks      = result.tanks      ?? []
    lineup.value.healers    = result.healers    ?? []
    lineup.value.dps        = result.dps        ?? []
    benchQueue.value        = result.bench_queue ?? []
    lineupVersion.value     = result.version ?? null
    dirty.value = false
    emit('saved', { auto })
  } catch (err) {
    if (err?.response?.status === 409 && err?.response?.data?.error === 'lineup_conflict') {
      // Another officer modified the lineup — apply their version and notify
      const fresh = err.response.data.lineup
      lineup.value.main_tanks = fresh.main_tanks ?? []
      lineup.value.off_tanks  = fresh.off_tanks  ?? []
      lineup.value.tanks      = fresh.tanks      ?? []
      lineup.value.healers    = fresh.healers    ?? []
      lineup.value.dps        = fresh.dps        ?? []
      benchQueue.value        = fresh.bench_queue ?? []
      lineupVersion.value     = fresh.version ?? null
      dirty.value = false
      uiStore.showToast('Lineup was updated by another officer. Your changes were reset.', 'warning')
      emit('saved', { auto: true })
    } else {
      console.error('Failed to save lineup', err)
      if (!auto) {
        uiStore.showToast(err?.response?.data?.message ?? 'Failed to save lineup', 'error')
      }
    }
  } finally {
    saving.value = false
  }
}
</script>
