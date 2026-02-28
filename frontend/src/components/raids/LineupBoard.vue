<template>
  <WowCard :padded="false">
    <div class="flex items-center justify-between px-5 py-3 border-b border-border-default">
      <h3 class="wow-heading text-base">Lineup Board</h3>
      <div class="flex items-center gap-2">
        <WowButton variant="secondary" @click="saveLineup" :loading="saving" class="text-xs py-1 px-3">
          Save Lineup
        </WowButton>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-px bg-border-default">
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
          @assign="(s) => assignToRole('dps', s)"
          @remove="(i) => removeFromRole('dps', i)"
        />
      </div>
    </div>

    <!-- Unassigned pool -->
    <div v-if="unassigned.length > 0" class="px-5 py-4 border-t border-border-default">
      <p class="text-xs text-text-muted mb-2 uppercase tracking-wider">Unassigned ({{ unassigned.length }})</p>
      <div class="flex flex-wrap gap-2">
        <div
          v-for="s in unassigned"
          :key="s.id"
          class="flex items-center gap-1.5 px-2 py-1 rounded bg-bg-tertiary border border-border-default text-xs cursor-pointer hover:border-border-gold transition-colors"
        >
          <ClassBadge v-if="s.character?.class" :class-name="s.character.class" />
          <span>{{ s.character?.name ?? '?' }}</span>
          <span class="text-text-muted">({{ s.chosen_role }})</span>
        </div>
      </div>
    </div>
  </WowCard>
</template>

<script setup>
import { ref, computed, onMounted, defineComponent, h } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import ClassBadge from '@/components/common/ClassBadge.vue'
import * as lineupApi from '@/api/lineup'
import { useWowIcons } from '@/composables/useWowIcons'

const props = defineProps({
  signups:     { type: Array,          default: () => [] },
  eventId:     { type: [Number,String], required: true },
  guildId:     { type: [Number,String], required: true },
  tankSlots:   { type: Number, default: 2 },
  healerSlots: { type: Number, default: 5 },
  dpsSlots:    { type: Number, default: 18 }
})

const emit = defineEmits(['saved'])
const { getClassIcon, getClassColor, getRoleIcon } = useWowIcons()
const saving = ref(false)

const lineup = ref({ tanks: [], healers: [], dps: [] })

onMounted(async () => {
  try {
    const data = await lineupApi.getLineup(props.guildId, props.eventId)
    lineup.value.tanks   = data.tanks   ?? []
    lineup.value.healers = data.healers ?? []
    lineup.value.dps     = data.dps     ?? []
  } catch {
    // No existing lineup – start fresh
  }
})

const activeSignups = computed(() =>
  props.signups.filter(s => ['going', 'tentative'].includes(s.status))
)

const assignedIds = computed(() => {
  const ids = new Set()
  ;[...lineup.value.tanks, ...lineup.value.healers, ...lineup.value.dps].forEach(s => ids.add(s.id))
  return ids
})

const unassigned = computed(() =>
  activeSignups.value.filter(s => !assignedIds.value.has(s.id))
)

const availableTanks   = computed(() => unassigned.value.filter(s => s.chosen_role === 'tank'))
const availableHealers = computed(() => unassigned.value.filter(s => s.chosen_role === 'healer'))
const availableDps     = computed(() => unassigned.value.filter(s => s.chosen_role === 'dps'))

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
      tanks:   lineup.value.tanks.map(s => s.id),
      healers: lineup.value.healers.map(s => s.id),
      dps:     lineup.value.dps.map(s => s.id)
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
    role:    { type: String, required: true },
    slots:   { type: Array, default: () => [] },
    signups: { type: Array, default: () => [] }
  },
  emits: ['assign', 'remove'],
  setup(colProps, { emit: colEmit }) {
    const { getClassIcon } = useWowIcons()
    return () => h('div', { class: 'space-y-1.5' }, [
      // Assigned slots
      ...colProps.slots.map((s, i) =>
        h('div', {
          key: s.id,
          class: 'flex items-center gap-2 px-2 py-1.5 rounded bg-bg-primary border border-border-default group'
        }, [
          h('img', { src: getClassIcon(s.character?.class), alt: s.character?.class ?? '', class: 'w-6 h-6 rounded flex-shrink-0', loading: 'lazy' }),
          h('span', { class: 'flex-1 text-xs text-text-primary truncate' }, s.character?.name ?? '?'),
          h('button', {
            type: 'button',
            class: 'opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition-all',
            onClick: () => colEmit('remove', i)
          }, '×')
        ])
      ),
      // Dropdown to assign from available signups
      colProps.signups.length > 0
        ? h('select', {
            class: 'w-full bg-bg-tertiary border border-dashed border-border-default text-text-muted text-xs rounded px-2 py-1.5 mt-1 focus:border-border-gold outline-none',
            onChange: (e) => {
              const found = colProps.signups.find(s => String(s.id) === e.target.value)
              if (found) { colEmit('assign', found); e.target.value = '' }
            }
          }, [
            h('option', { value: '' }, '+ Add player…'),
            ...colProps.signups.map(s =>
              h('option', { key: s.id, value: s.id }, `${s.character?.name ?? '?'} (${s.chosen_spec || s.chosen_role})`)
            )
          ])
        : null
    ])
  }
})
</script>
