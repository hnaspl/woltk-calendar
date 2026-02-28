<template>
  <WowCard :padded="false">
    <div class="flex items-center justify-between px-5 py-3 border-b border-border-default">
      <h3 class="wow-heading text-base">Lineup Board</h3>
      <div v-if="isOfficer" class="flex items-center gap-2">
        <WowButton variant="secondary" @click="saveLineup" :loading="saving" class="text-xs py-1 px-3">
          Save Lineup
        </WowButton>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-5 gap-px bg-border-default">
      <!-- MAIN TANKS -->
      <div class="bg-bg-secondary p-4">
        <div class="flex items-center gap-2 mb-3">
          <img :src="getRoleIcon('main_tank')" class="w-5 h-5 rounded" alt="Main Tank" />
          <span class="text-blue-200 font-semibold text-sm">MT</span>
          <span class="ml-auto text-xs text-text-muted">{{ lineup.main_tanks.length }}</span>
        </div>
        <LineupColumn
          role="main_tank"
          :slots="lineup.main_tanks"
          :signups="availableMainTanks"
          :editable="isOfficer"
          @assign="(s) => assignToRole('main_tanks', s)"
          @remove="(i) => removeFromRole('main_tanks', i)"
        />
      </div>

      <!-- OFF TANKS -->
      <div class="bg-bg-secondary p-4">
        <div class="flex items-center gap-2 mb-3">
          <img :src="getRoleIcon('off_tank')" class="w-5 h-5 rounded" alt="Off Tank" />
          <span class="text-cyan-300 font-semibold text-sm">OT</span>
          <span class="ml-auto text-xs text-text-muted">{{ lineup.off_tanks.length }}</span>
        </div>
        <LineupColumn
          role="off_tank"
          :slots="lineup.off_tanks"
          :signups="availableOffTanks"
          :editable="isOfficer"
          @assign="(s) => assignToRole('off_tanks', s)"
          @remove="(i) => removeFromRole('off_tanks', i)"
        />
      </div>

      <!-- TANKS -->
      <div class="bg-bg-secondary p-4">
        <div class="flex items-center gap-2 mb-3">
          <img :src="getRoleIcon('tank')" class="w-5 h-5 rounded" alt="Tank" />
          <span class="text-blue-300 font-semibold text-sm">Tanks</span>
          <span class="ml-auto text-xs text-text-muted">{{ lineup.tanks.length }} / {{ tankSlots }}</span>
        </div>
        <LineupColumn
          role="tank"
          :slots="lineup.tanks"
          :signups="availableTanks"
          :editable="isOfficer"
          @assign="(s) => assignToRole('tanks', s)"
          @remove="(i) => removeFromRole('tanks', i)"
        />
      </div>

      <!-- HEALERS -->
      <div class="bg-bg-secondary p-4">
        <div class="flex items-center gap-2 mb-3">
          <img :src="getRoleIcon('healer')" class="w-5 h-5 rounded" alt="Healer" />
          <span class="text-green-300 font-semibold text-sm">Healers</span>
          <span class="ml-auto text-xs text-text-muted">{{ lineup.healers.length }} / {{ healerSlots }}</span>
        </div>
        <LineupColumn
          role="healer"
          :slots="lineup.healers"
          :signups="availableHealers"
          :editable="isOfficer"
          @assign="(s) => assignToRole('healers', s)"
          @remove="(i) => removeFromRole('healers', i)"
        />
      </div>

      <!-- DPS -->
      <div class="bg-bg-secondary p-4">
        <div class="flex items-center gap-2 mb-3">
          <img :src="getRoleIcon('dps')" class="w-5 h-5 rounded" alt="DPS" />
          <span class="text-red-300 font-semibold text-sm">DPS</span>
          <span class="ml-auto text-xs text-text-muted">{{ lineup.dps.length }} / {{ dpsSlots }}</span>
        </div>
        <LineupColumn
          role="dps"
          :slots="lineup.dps"
          :signups="availableDps"
          :editable="isOfficer"
          @assign="(s) => assignToRole('dps', s)"
          @remove="(i) => removeFromRole('dps', i)"
        />
      </div>
    </div>

    <!-- Unassigned pool -->
    <div v-if="unassigned.length > 0" class="px-5 py-4 border-t border-border-default">
      <p class="text-xs text-text-muted mb-2 uppercase tracking-wider">Unassigned ({{ unassigned.length }})</p>
      <div class="flex flex-wrap gap-2">
        <CharacterTooltip
          v-for="s in unassigned"
          :key="s.id"
          :character="s.character"
          position="top"
        >
          <div
            class="flex items-center gap-1.5 px-2 py-1 rounded bg-bg-tertiary border border-border-default text-xs cursor-pointer hover:border-border-gold transition-colors"
          >
            <ClassBadge v-if="s.character?.class_name" :class-name="s.character.class_name" />
            <span>{{ s.character?.name ?? '?' }}</span>
            <span class="text-text-muted">({{ s.chosen_role }})</span>
            <span v-if="s.character?.metadata?.level" class="text-[10px] text-text-muted">
              Lv{{ s.character.metadata.level }}
            </span>
          </div>
        </CharacterTooltip>
      </div>
    </div>
  </WowCard>
</template>

<script setup>
import { ref, computed, onMounted, watch, defineComponent, h } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import ClassBadge from '@/components/common/ClassBadge.vue'
import CharacterTooltip from '@/components/common/CharacterTooltip.vue'
import * as lineupApi from '@/api/lineup'
import { useWowIcons } from '@/composables/useWowIcons'

const props = defineProps({
  signups:     { type: Array,          default: () => [] },
  eventId:     { type: [Number,String], required: true },
  guildId:     { type: [Number,String], required: true },
  isOfficer:   { type: Boolean, default: false },
  tankSlots:   { type: Number, default: 2 },
  healerSlots: { type: Number, default: 5 },
  dpsSlots:    { type: Number, default: 18 }
})

const emit = defineEmits(['saved'])
const { getClassIcon, getClassColor, getRoleIcon } = useWowIcons()
const saving = ref(false)

const lineup = ref({ main_tanks: [], off_tanks: [], tanks: [], healers: [], dps: [] })

async function loadLineup() {
  try {
    const data = await lineupApi.getLineup(props.guildId, props.eventId)
    lineup.value.main_tanks = data.main_tanks ?? []
    lineup.value.off_tanks  = data.off_tanks  ?? []
    lineup.value.tanks      = data.tanks      ?? []
    lineup.value.healers    = data.healers    ?? []
    lineup.value.dps        = data.dps        ?? []
  } catch {
    // No existing lineup – auto-populate from going signups
    autoPopulateFromSignups()
  }
}

onMounted(loadLineup)

// Reload lineup when signups change (e.g. new signup, removal, status change)
watch(
  () => props.signups.map(s => `${s.id}:${s.status}`).join(','),
  loadLineup
)

function autoPopulateFromSignups() {
  const going = props.signups.filter(s => s.status === 'going')
  lineup.value.main_tanks = going.filter(s => s.chosen_role === 'main_tank')
  lineup.value.off_tanks  = going.filter(s => s.chosen_role === 'off_tank')
  lineup.value.tanks      = going.filter(s => s.chosen_role === 'tank')
  lineup.value.healers    = going.filter(s => s.chosen_role === 'healer')
  lineup.value.dps        = going.filter(s => s.chosen_role === 'dps')
}

const activeSignups = computed(() =>
  props.signups.filter(s => ['going', 'tentative'].includes(s.status))
)

const assignedIds = computed(() => {
  const ids = new Set()
  ;[...lineup.value.main_tanks, ...lineup.value.off_tanks, ...lineup.value.tanks, ...lineup.value.healers, ...lineup.value.dps].forEach(s => ids.add(s.id))
  return ids
})

const unassigned = computed(() =>
  activeSignups.value.filter(s => !assignedIds.value.has(s.id))
)

const availableMainTanks = computed(() => unassigned.value.filter(s => s.chosen_role === 'main_tank'))
const availableOffTanks  = computed(() => unassigned.value.filter(s => s.chosen_role === 'off_tank'))
const availableTanks     = computed(() => unassigned.value.filter(s => s.chosen_role === 'tank'))
const availableHealers   = computed(() => unassigned.value.filter(s => s.chosen_role === 'healer'))
const availableDps       = computed(() => unassigned.value.filter(s => s.chosen_role === 'dps'))

function assignToRole(role, signup) {
  lineup.value[role].push(signup)
}

function removeFromRole(role, index) {
  lineup.value[role].splice(index, 1)
}

async function saveLineup() {
  saving.value = true
  try {
    await lineupApi.saveLineup(props.guildId, props.eventId, {
      main_tanks: lineup.value.main_tanks.map(s => s.id),
      off_tanks:  lineup.value.off_tanks.map(s => s.id),
      tanks:      lineup.value.tanks.map(s => s.id),
      healers:    lineup.value.healers.map(s => s.id),
      dps:        lineup.value.dps.map(s => s.id)
    })
    emit('saved', lineup.value)
  } catch (err) {
    console.error('Failed to save lineup', err)
  } finally {
    saving.value = false
  }
}

// ── Inline LineupColumn sub-component ────────────────────────
const LineupColumn = defineComponent({
  name: 'LineupColumn',
  props: {
    role:     { type: String, required: true },
    slots:    { type: Array, default: () => [] },
    signups:  { type: Array, default: () => [] },
    editable: { type: Boolean, default: false }
  },
  emits: ['assign', 'remove'],
  setup(colProps, { emit: colEmit }) {
    const { getClassIcon, getClassColor } = useWowIcons()
    return () => h('div', { class: 'space-y-1.5' }, [
      // Assigned slots with enriched info + tooltip
      ...colProps.slots.map((s, i) => {
        const meta = s.character?.metadata ?? {}
        const profs = (meta.professions ?? []).map(p => p.name).join(', ')
        const level = meta.level ?? ''
        const classColor = getClassColor(s.character?.class_name) ?? '#ccc'

        const slotContent = h('div', {
          key: s.id,
          class: 'flex items-center gap-2 px-2 py-1.5 rounded bg-bg-primary border border-border-default group hover:border-border-gold transition-colors'
        }, [
          h('img', {
            src: getClassIcon(s.character?.class_name),
            alt: s.character?.class_name ?? '',
            class: 'w-6 h-6 rounded flex-shrink-0',
            loading: 'lazy'
          }),
          h('div', { class: 'flex-1 min-w-0' }, [
            h('div', { class: 'flex items-center gap-1' }, [
              h('span', {
                class: 'text-xs font-medium truncate',
                style: { color: classColor }
              }, s.character?.name ?? '?'),
              level ? h('span', { class: 'text-[10px] text-text-muted' }, `Lv${level}`) : null,
            ]),
            // Spec + professions line
            h('div', { class: 'flex items-center gap-1 text-[10px] text-text-muted' }, [
              s.chosen_spec ? h('span', { class: 'text-amber-300' }, s.chosen_spec) : null,
              profs ? h('span', {}, profs) : null,
            ].filter(Boolean)),
          ]),
          colProps.editable
            ? h('button', {
                type: 'button',
                class: 'opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition-all',
                onClick: () => colEmit('remove', i)
              }, '×')
            : null
        ])

        // Wrap with CharacterTooltip
        return h(CharacterTooltip, {
          key: s.id,
          character: s.character,
          position: 'left'
        }, () => slotContent)
      }),
      // Dropdown to assign from available signups (officer only)
      colProps.editable && colProps.signups.length > 0
        ? h('select', {
            class: 'w-full bg-bg-tertiary border border-dashed border-border-default text-text-muted text-xs rounded px-2 py-1.5 mt-1 focus:border-border-gold outline-none',
            onChange: (e) => {
              const found = colProps.signups.find(s => String(s.id) === e.target.value)
              if (found) { colEmit('assign', found); e.target.value = '' }
            }
          }, [
            h('option', { value: '' }, '+ Add player…'),
            ...colProps.signups.map(s => {
              const lvl = s.character?.metadata?.level ? ` Lv${s.character.metadata.level}` : ''
              return h('option', { key: s.id, value: s.id },
                `${s.character?.name ?? '?'} (${s.chosen_spec || s.chosen_role})${lvl}`
              )
            })
          ])
        : null
    ])
  }
})
</script>
