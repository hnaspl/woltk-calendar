<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="modelValue && character"
        class="fixed inset-0 z-[100] flex items-center justify-center p-4"
        @click.self="$emit('update:modelValue', false)"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/70" @click="$emit('update:modelValue', false)" />

        <!-- Modal content -->
        <div class="relative w-full max-w-md bg-[#0d1117] border border-[#2a3450] rounded-xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
          <!-- Close button (top-left) -->
          <button
            class="absolute top-3 left-3 z-10 w-7 h-7 flex items-center justify-center rounded-full bg-[#161b22] border border-[#2a3450] text-text-muted hover:text-text-primary hover:border-border-gold transition-colors"
            aria-label="Close character details"
            @click="$emit('update:modelValue', false)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>

          <!-- Header -->
          <div class="flex items-center gap-3 px-4 py-3 border-b border-[#2a3450] bg-[#161b22]">
            <img
              v-if="classIcon"
              :src="classIcon"
              :alt="character.class_name"
              class="w-10 h-10 rounded-lg border border-[#2a3450] ml-8"
            />
            <div class="min-w-0 flex-1">
              <div class="text-base font-bold truncate" :style="{ color: classColor }">
                {{ character.name }}
              </div>
              <div class="text-xs text-text-muted flex items-center gap-2 flex-wrap">
                <span class="inline-flex items-center gap-1 px-2 py-0.5 bg-bg-secondary rounded-full text-[11px] font-medium text-accent-gold">
                  Lv {{ meta.level ?? character.level ?? '?' }}
                </span>
                <span>{{ meta.race ?? '' }} {{ character.class_name ?? '' }}</span>
                <span v-if="meta.achievement_points" class="inline-flex items-center gap-1 text-amber-400 text-[11px]">
                  🏆 {{ meta.achievement_points.toLocaleString() }}
                </span>
              </div>
            </div>
            <a
              v-if="character.armory_url"
              :href="character.armory_url"
              target="_blank"
              class="text-[11px] text-amber-400 hover:underline flex-shrink-0 px-2 py-1 rounded border border-amber-500/30 hover:border-amber-400 transition-colors"
              @click.stop
            >Armory ↗</a>
          </div>

          <!-- Body (scrollable) -->
          <div class="overflow-y-auto flex-1 px-4 py-3 space-y-4">
            <!-- Specs & Role -->
            <div v-if="character.default_role || character.primary_spec || character.secondary_spec">
              <div class="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">Role &amp; Specialization</div>
              <div class="space-y-1.5">
                <div v-if="character.default_role" class="flex items-center gap-2">
                  <img :src="getRoleIcon(character.default_role)" class="w-5 h-5 rounded" />
                  <span class="text-sm text-text-primary capitalize">{{ character.default_role?.replace('_', ' ') }}</span>
                </div>
                <div v-if="character.primary_spec" class="flex items-center gap-2">
                  <img v-if="getSpecIcon(character.primary_spec, character.class_name)" :src="getSpecIcon(character.primary_spec, character.class_name)" class="w-5 h-5 rounded" />
                  <span class="text-sm">
                    <span class="text-amber-300 font-medium">{{ character.primary_spec }}</span>
                    <span class="text-text-muted text-xs ml-1">(Primary)</span>
                  </span>
                </div>
                <div v-if="character.secondary_spec" class="flex items-center gap-2">
                  <img v-if="getSpecIcon(character.secondary_spec, character.class_name)" :src="getSpecIcon(character.secondary_spec, character.class_name)" class="w-5 h-5 rounded" />
                  <span class="text-sm">
                    <span class="text-gray-300">{{ character.secondary_spec }}</span>
                    <span class="text-text-muted text-xs ml-1">(Secondary)</span>
                  </span>
                </div>
              </div>
            </div>

            <!-- Professions -->
            <div v-if="professions.length > 0">
              <div class="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">Professions</div>
              <div class="space-y-1.5">
                <div v-for="p in professions" :key="p.name" class="flex items-center gap-2">
                  <img :src="getProfessionIcon(p.name)" :alt="p.name" class="w-5 h-5 rounded" />
                  <span class="text-sm text-text-primary">{{ p.name }}</span>
                  <span class="text-sm text-amber-300 ml-auto font-medium">{{ p.skill }}</span>
                </div>
              </div>
            </div>

            <!-- Talents -->
            <div v-if="talents.length > 0">
              <div class="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">Talent Trees</div>
              <div class="space-y-1.5">
                <div v-for="(t, i) in talents" :key="i" class="flex items-center gap-2">
                  <img v-if="getSpecIcon(t.tree, character.class_name)" :src="getSpecIcon(t.tree, character.class_name)" class="w-5 h-5 rounded" />
                  <span class="text-sm text-text-primary">{{ t.tree ?? 'Unknown' }}</span>
                  <span v-if="t.points" class="text-sm text-text-muted ml-auto">{{ formatPoints(t.points) }}</span>
                </div>
              </div>
            </div>

            <!-- Glyphs -->
            <div v-if="glyphs.length > 0">
              <div class="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">Glyphs</div>
              <div class="flex flex-wrap gap-1.5">
                <span
                  v-for="(g, i) in glyphs"
                  :key="i"
                  class="text-[11px] px-2 py-1 bg-purple-500/10 border border-purple-500/20 rounded text-purple-300"
                >{{ g.name ?? g }}</span>
              </div>
            </div>

            <!-- Stats -->
            <div v-if="hasStats">
              <div class="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">Stats</div>
              <div class="grid grid-cols-2 gap-2">
                <div v-if="meta.gear_score" class="flex items-center gap-2 px-3 py-2 bg-amber-500/10 rounded-lg border border-amber-500/20">
                  <span class="text-amber-300">⚡</span>
                  <div>
                    <div class="text-[10px] text-text-muted">Gear Score</div>
                    <div class="text-sm font-bold text-amber-300">{{ meta.gear_score }}</div>
                  </div>
                </div>
                <div v-if="meta.honorable_kills" class="flex items-center gap-2 px-3 py-2 bg-red-500/10 rounded-lg border border-red-500/20">
                  <span class="text-red-400">⚔</span>
                  <div>
                    <div class="text-[10px] text-text-muted">Honorable Kills</div>
                    <div class="text-sm font-bold text-red-300">{{ meta.honorable_kills.toLocaleString() }}</div>
                  </div>
                </div>
                <div v-if="meta.faction" class="flex items-center gap-2 px-3 py-2 bg-bg-secondary rounded-lg border border-border-default">
                  <span>{{ meta.faction === 'Alliance' ? '🔵' : '🔴' }}</span>
                  <div>
                    <div class="text-[10px] text-text-muted">Faction</div>
                    <div class="text-sm text-text-primary">{{ meta.faction }}</div>
                  </div>
                </div>
                <div v-if="meta.guild" class="flex items-center gap-2 px-3 py-2 bg-green-500/10 rounded-lg border border-green-500/20">
                  <span class="text-green-400">🛡</span>
                  <div class="min-w-0">
                    <div class="text-[10px] text-text-muted">Guild</div>
                    <div class="text-sm text-green-300 truncate">&lt;{{ meta.guild }}&gt;</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Equipment -->
            <div v-if="equipment.length > 0">
              <div class="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">
                Equipment ({{ equipment.length }} items)
              </div>
              <div class="grid grid-cols-1 gap-1 bg-bg-secondary rounded-lg p-2 border border-border-default max-h-72 overflow-y-auto scrollbar-thin">
                <div
                  v-for="(item, i) in equipment"
                  :key="i"
                  class="group relative flex items-center gap-2 px-2 py-1.5 rounded hover:bg-[#1a2035] transition-colors cursor-default"
                >
                  <!-- Slot icon -->
                  <div class="w-8 h-8 flex-shrink-0 rounded border flex items-center justify-center text-[11px]"
                    :class="itemQualityBorder(item)"
                    :style="{ backgroundColor: 'rgba(0,0,0,0.4)' }"
                  >
                    <span class="text-text-muted">{{ equipSlotIcon(i) }}</span>
                  </div>
                  <!-- Item name -->
                  <div class="flex-1 min-w-0">
                    <div class="text-[12px] font-medium truncate" :class="itemQualityText(item)">
                      {{ item.name }}
                    </div>
                    <div class="text-[10px] text-text-muted">{{ equipSlotLabel(i) }}</div>
                  </div>
                  <!-- Item ID badge -->
                  <div v-if="item.item" class="flex-shrink-0">
                    <a
                      :href="`https://wowhead.com/wotlk/item=${item.item}`"
                      target="_blank"
                      class="text-[10px] text-amber-400/60 hover:text-amber-400 transition-colors"
                      @click.stop
                      :title="`Item #${item.item} — Click for Wowhead tooltip`"
                    >🔗</a>
                  </div>
                  <!-- Tooltip on hover -->
                  <div class="absolute left-0 bottom-full mb-1 z-50 hidden group-hover:block pointer-events-none w-56">
                    <div class="bg-[#0d1117] border border-[#2a3450] rounded-lg shadow-xl p-3 text-xs">
                      <div class="font-bold mb-1" :class="itemQualityText(item)">{{ item.name }}</div>
                      <div class="text-text-muted">{{ equipSlotLabel(i) }}</div>
                      <div v-if="item.item" class="text-text-muted mt-1">Item ID: {{ item.item }}</div>
                      <div v-if="item.transmog" class="mt-1 text-purple-300 text-[10px]">
                        Transmogrified: {{ typeof item.transmog === 'object' ? item.transmog.name || item.transmog.item : item.transmog }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Last synced -->
            <div v-if="meta.last_synced" class="text-[10px] text-text-muted pt-2 border-t border-[#2a3450]">
              Last synced: {{ formatDate(meta.last_synced) }}
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useWowIcons } from '@/composables/useWowIcons'
import { normalizeSpecName } from '@/constants'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  character: { type: Object, default: null },
})

defineEmits(['update:modelValue'])

const { getClassIcon, getClassColor, getSpecIcon, getRoleIcon, getProfessionIcon } = useWowIcons()

const classIcon = computed(() => props.character?.class_name ? getClassIcon(props.character.class_name) : null)
const classColor = computed(() => props.character?.class_name ? getClassColor(props.character.class_name) : '#ccc')

const meta = computed(() => props.character?.metadata ?? {})
const talents = computed(() => {
  const raw = meta.value.talents ?? []
  const cls = props.character?.class_name ?? ''
  return raw.map(t => ({
    ...t,
    tree: normalizeSpecName(t.tree, cls) ?? t.tree,
  }))
})
const glyphs = computed(() => meta.value.glyphs ?? [])
const professions = computed(() => meta.value.professions ?? [])
const equipment = computed(() => (meta.value.equipment ?? []).filter(e => e?.name))
const hasStats = computed(() =>
  meta.value.gear_score || meta.value.honorable_kills || meta.value.faction || meta.value.guild
)

// Equipment slot labels & icons matching WoW armory order
const EQUIP_SLOTS = [
  { label: 'Head', icon: '🪖' },
  { label: 'Neck', icon: '📿' },
  { label: 'Shoulders', icon: '🛡' },
  { label: 'Back', icon: '🧣' },
  { label: 'Chest', icon: '👕' },
  { label: 'Shirt', icon: '👔' },
  { label: 'Tabard', icon: '🏴' },
  { label: 'Wrists', icon: '⌚' },
  { label: 'Hands', icon: '🧤' },
  { label: 'Waist', icon: '🎗' },
  { label: 'Legs', icon: '👖' },
  { label: 'Feet', icon: '👢' },
  { label: 'Ring 1', icon: '💍' },
  { label: 'Ring 2', icon: '💍' },
  { label: 'Trinket 1', icon: '🔮' },
  { label: 'Trinket 2', icon: '🔮' },
  { label: 'Main Hand', icon: '⚔' },
  { label: 'Off Hand', icon: '🛡' },
  { label: 'Ranged', icon: '🏹' },
]

function equipSlotLabel(index) {
  return EQUIP_SLOTS[index]?.label ?? `Slot ${index + 1}`
}

function equipSlotIcon(index) {
  return EQUIP_SLOTS[index]?.icon ?? '📦'
}

function itemQualityBorder(item) {
  // Warmane equipment items don't always include quality; use item ID heuristic for epic+ items
  if (!item.item) return 'border-[#2a3450]'
  return 'border-purple-500/50'
}

function itemQualityText(item) {
  if (!item.item) return 'text-text-primary'
  return 'text-purple-300'
}

function formatPoints(points) {
  if (Array.isArray(points)) return points.join('/')
  return String(points)
}

function formatDate(iso) {
  if (!iso) return '?'
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}
</script>
