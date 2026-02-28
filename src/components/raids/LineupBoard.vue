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
        @dragover.prevent="isOfficer && onDragOver($event, col.key)"
        @dragenter.prevent="isOfficer && (dragOverTarget = col.key)"
        @dragleave="isOfficer && onDragLeave($event, col.key)"
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
            position="left"
          >
            <div
              class="flex items-center gap-2 px-2 py-1.5 rounded bg-bg-primary border border-border-default group hover:border-border-gold transition-colors"
              :class="{ 'cursor-grab active:cursor-grabbing': isOfficer, 'opacity-50': draggedId === s.id }"
              :draggable="isOfficer"
              @dragstart="isOfficer && onDragStart($event, s, col.key, i)"
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
          <!-- Dropdown to assign (officer only) -->
          <select
            v-if="isOfficer && availableFor(col.key).length > 0"
            class="w-full bg-bg-tertiary border border-dashed border-border-default text-text-muted text-xs rounded px-2 py-1.5 mt-1 focus:border-border-gold outline-none"
            @change="onSelectAssign($event, col.key)"
          >
            <option value="">+ Add player…</option>
            <option v-for="s in availableFor(col.key)" :key="s.id" :value="s.id">
              {{ s.character?.name ?? '?' }} ({{ s.chosen_spec || s.chosen_role }}){{ s.character?.metadata?.level ? ` Lv${s.character.metadata.level}` : '' }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <!-- Unassigned pool -->
    <div
      v-if="unassigned.length > 0 || (isOfficer && draggedId)"
      class="px-5 py-4 border-t border-border-default transition-colors"
      :class="{ 'bg-red-900/10 ring-1 ring-inset ring-red-500/30': isOfficer && dragOverTarget === 'unassigned' }"
      @dragover.prevent="isOfficer && onDragOver($event, 'unassigned')"
      @dragenter.prevent="isOfficer && (dragOverTarget = 'unassigned')"
      @dragleave="isOfficer && onDragLeave($event, 'unassigned')"
      @drop.prevent="isOfficer && onDropUnassigned()"
    >
      <p class="text-xs text-text-muted mb-2 uppercase tracking-wider">Unassigned ({{ unassigned.length }})</p>
      <div class="flex flex-wrap gap-2">
        <CharacterTooltip
          v-for="s in unassigned"
          :key="s.id"
          :character="s.character"
          position="top"
        >
          <div
            class="flex items-center gap-1.5 px-2 py-1 rounded bg-bg-tertiary border border-border-default text-xs transition-colors"
            :class="{
              'cursor-grab active:cursor-grabbing hover:border-border-gold': isOfficer,
              'cursor-pointer hover:border-border-gold': !isOfficer,
              'opacity-50': draggedId === s.id
            }"
            :draggable="isOfficer"
            @dragstart="isOfficer && onDragStart($event, s, 'unassigned', -1)"
            @dragend="onDragEnd"
          >
            <ClassBadge v-if="s.character?.class_name" :class-name="s.character.class_name" />
            <span>{{ s.character?.name ?? '?' }}</span>
            <span class="text-text-muted">({{ ROLE_LABEL_MAP[s.chosen_role] ?? s.chosen_role }})</span>
            <span v-if="s.status === 'bench'" class="text-[10px] text-yellow-400 font-semibold">Bench</span>
            <span v-if="s.character?.metadata?.level" class="text-[10px] text-text-muted">
              Lv{{ s.character.metadata.level }}
            </span>
          </div>
        </CharacterTooltip>
      </div>
      <p v-if="unassigned.length === 0 && draggedId" class="text-xs text-text-muted italic">
        Drop here to unassign
      </p>
    </div>
  </WowCard>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import ClassBadge from '@/components/common/ClassBadge.vue'
import CharacterTooltip from '@/components/common/CharacterTooltip.vue'
import * as lineupApi from '@/api/lineup'
import { useWowIcons } from '@/composables/useWowIcons'
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

const emit = defineEmits(['saved'])
const { getClassIcon, getClassColor, getRoleIcon } = useWowIcons()
const uiStore = useUiStore()
const saving = ref(false)
const dirty = ref(false)

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

// ── Drag state ──
const draggedId = ref(null)
const dragSourceKey = ref(null)
const dragSourceIndex = ref(-1)
const dragOverTarget = ref(null)

function onDragStart(e, signup, sourceKey, idx) {
  draggedId.value = signup.id
  dragSourceKey.value = sourceKey
  dragSourceIndex.value = idx
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', String(signup.id))
}

function onDragEnd() {
  draggedId.value = null
  dragSourceKey.value = null
  dragSourceIndex.value = -1
  dragOverTarget.value = null
}

function onDragOver(e, target) {
  e.dataTransfer.dropEffect = 'move'
  dragOverTarget.value = target
}

function onDragLeave(e, target) {
  if (dragOverTarget.value === target) {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX; const y = e.clientY
    if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
      dragOverTarget.value = null
    }
  }
}

function findSignupById(id) {
  for (const key of ['main_tanks', 'off_tanks', 'tanks', 'healers', 'dps']) {
    const idx = lineup.value[key].findIndex(s => Number(s.id) === id)
    if (idx !== -1) return { key, idx, signup: lineup.value[key][idx] }
  }
  const fromUnassigned = unassigned.value.find(s => Number(s.id) === id)
  if (fromUnassigned) return { key: 'unassigned', idx: -1, signup: fromUnassigned }
  return null
}

function onDropColumn(e, targetKey) {
  dragOverTarget.value = null
  const id = Number(e.dataTransfer.getData('text/plain'))
  if (!id) return

  const found = findSignupById(id)
  if (!found) return

  // Overflow protection: check if target column is full
  const col = allColumns.value.find(c => c.key === targetKey)
  if (col) {
    const currentCount = lineup.value[targetKey].length
    // Don't count the item if it's already in this column (re-ordering)
    const alreadyInTarget = lineup.value[targetKey].find(s => Number(s.id) === id)
    if (!alreadyInTarget && currentCount >= col.slots) {
      uiStore.showToast(`${col.label} slots are full (${currentCount}/${col.slots}). Remove someone first or choose a different role.`, 'error')
      return
    }
  }

  // Remove from source
  if (found.key !== 'unassigned') {
    lineup.value[found.key].splice(found.idx, 1)
  }

  // Add to target (avoid duplicates)
  if (!lineup.value[targetKey].find(s => Number(s.id) === id)) {
    lineup.value[targetKey].push(found.signup)
  }
  dirty.value = true
  autoSave()
}

function onDropUnassigned() {
  dragOverTarget.value = null
  const sourceKey = dragSourceKey.value
  const sourceIdx = dragSourceIndex.value
  if (sourceKey && sourceKey !== 'unassigned' && sourceIdx >= 0) {
    lineup.value[sourceKey].splice(sourceIdx, 1)
    dirty.value = true
    autoSave()
  }
}

// ── Auto-save on DnD ──
let autoSaveTimer = null
function autoSave() {
  clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => saveLineup(true), 300)
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
    dirty.value = false
  } catch {
    autoPopulateFromSignups()
  }
}

onMounted(loadLineup)

watch(
  () => props.signups.map(s => `${s.id}:${s.status}:${s.chosen_role}`).join(','),
  () => {
    // Skip reload when there are unsaved DnD changes to avoid overwriting them
    if (!dirty.value) loadLineup()
  }
)

function autoPopulateFromSignups() {
  const going = props.signups.filter(s => s.status === 'going')
  lineup.value.main_tanks = going.filter(s => s.chosen_role === 'main_tank')
  lineup.value.off_tanks  = going.filter(s => s.chosen_role === 'off_tank')
  lineup.value.tanks      = going.filter(s => s.chosen_role === 'tank')
  lineup.value.healers    = going.filter(s => s.chosen_role === 'healer')
  lineup.value.dps        = going.filter(s => s.chosen_role === 'dps')
}

// ── Computed helpers ──
const activeSignups = computed(() =>
  props.signups.filter(s => ['going', 'tentative', 'bench'].includes(s.status))
)

const assignedIds = computed(() => {
  const ids = new Set()
  ;['main_tanks', 'off_tanks', 'tanks', 'healers', 'dps'].forEach(k =>
    lineup.value[k].forEach(s => ids.add(s.id))
  )
  return ids
})

const unassigned = computed(() =>
  activeSignups.value.filter(s => !assignedIds.value.has(s.id))
)

const tankFamilyRoles = ['tank', 'main_tank', 'off_tank']

function availableFor(key) {
  const un = unassigned.value
  if (['main_tanks', 'off_tanks', 'tanks'].includes(key)) {
    return un.filter(s => tankFamilyRoles.includes(s.chosen_role))
  }
  if (key === 'healers') return un.filter(s => s.chosen_role === 'healer')
  if (key === 'dps') return un.filter(s => s.chosen_role === 'dps')
  return un
}

function profString(s) {
  return (s.character?.metadata?.professions ?? []).map(p => p.name).join(', ')
}

function onSelectAssign(e, key) {
  const found = unassigned.value.find(s => String(s.id) === e.target.value)
  if (found) {
    // Overflow protection: check if column is full
    const col = allColumns.value.find(c => c.key === key)
    if (col && lineup.value[key].length >= col.slots) {
      uiStore.showToast(`${col.label} slots are full (${lineup.value[key].length}/${col.slots}). Remove someone first or choose a different role.`, 'error')
      e.target.value = ''
      return
    }
    lineup.value[key].push(found)
    dirty.value = true
    autoSave()
  }
  e.target.value = ''
}

function removeFromRole(key, index) {
  lineup.value[key].splice(index, 1)
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
      dps:        lineup.value.dps.map(s => s.id)
    })
    // Update local state from server response
    lineup.value.main_tanks = result.main_tanks ?? []
    lineup.value.off_tanks  = result.off_tanks  ?? []
    lineup.value.tanks      = result.tanks      ?? []
    lineup.value.healers    = result.healers    ?? []
    lineup.value.dps        = result.dps        ?? []
    dirty.value = false
    emit('saved', { auto })
  } catch (err) {
    console.error('Failed to save lineup', err)
    if (!auto) {
      uiStore.showToast(err?.response?.data?.message ?? 'Failed to save lineup', 'error')
    }
  } finally {
    saving.value = false
  }
}
</script>
