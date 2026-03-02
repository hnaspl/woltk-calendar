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

        <!-- Modal content — wider when equipment is present for two-column layout -->
        <div
          class="relative bg-[#0d1117] border border-[#2a3450] rounded-xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col"
          :class="equipment.length > 0 ? 'w-full max-w-md sm:max-w-lg md:max-w-3xl' : 'w-full max-w-md'"
        >
          <!-- Close button (top-left) -->
          <button
            class="absolute top-3 left-3 z-10 w-7 h-7 flex items-center justify-center rounded-full bg-[#161b22] border border-[#2a3450] text-text-muted hover:text-text-primary hover:border-border-gold transition-colors"
            :aria-label="t('characterDetail.closeDetails')"
            @click="$emit('update:modelValue', false)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>

          <!-- Header -->
          <div class="flex items-center gap-3 px-3 sm:px-4 py-2 sm:py-3 border-b border-[#2a3450] bg-[#161b22]">
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
            >{{ t('characterDetail.armory') }}</a>
          </div>

          <!-- Body — two-column when equipment is present -->
          <div class="overflow-y-auto flex-1" :class="equipment.length > 0 ? 'grid grid-cols-1 md:grid-cols-2' : ''">
            <!-- Left column: character info -->
            <div class="px-4 py-3 space-y-4" :class="equipment.length > 0 ? 'md:border-r md:border-[#2a3450] overflow-y-auto' : ''">
              <!-- Specs & Role -->
              <div v-if="character.default_role || character.primary_spec || character.secondary_spec">
                <div class="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">{{ t('characterDetail.roleAndSpec') }}</div>
                <div class="space-y-1.5">
                  <div v-if="character.default_role" class="flex items-center gap-2">
                    <img :src="getRoleIcon(character.default_role)" class="w-5 h-5 rounded" />
                    <span class="text-sm text-text-primary capitalize">{{ character.default_role?.replace('_', ' ') }}</span>
                  </div>
                  <div v-if="character.primary_spec" class="flex items-center gap-2">
                    <img v-if="getSpecIcon(character.primary_spec, character.class_name)" :src="getSpecIcon(character.primary_spec, character.class_name)" class="w-5 h-5 rounded" />
                    <span class="text-sm">
                      <span class="text-amber-300 font-medium">{{ character.primary_spec }}</span>
                      <span class="text-text-muted text-xs ml-1">{{ t('characterDetail.primary') }}</span>
                    </span>
                  </div>
                  <div v-if="character.secondary_spec" class="flex items-center gap-2">
                    <img v-if="getSpecIcon(character.secondary_spec, character.class_name)" :src="getSpecIcon(character.secondary_spec, character.class_name)" class="w-5 h-5 rounded" />
                    <span class="text-sm">
                      <span class="text-gray-300">{{ character.secondary_spec }}</span>
                      <span class="text-text-muted text-xs ml-1">{{ t('characterDetail.secondary') }}</span>
                    </span>
                  </div>
                </div>
              </div>

              <!-- Professions -->
              <div v-if="professions.length > 0">
                <div class="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">{{ t('characterDetail.professions') }}</div>
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
                <div class="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">{{ t('characterDetail.talentTrees') }}</div>
                <div class="space-y-1.5">
                  <div v-for="(tal, i) in talents" :key="i" class="flex items-center gap-2">
                    <img v-if="getSpecIcon(tal.tree, character.class_name)" :src="getSpecIcon(tal.tree, character.class_name)" class="w-5 h-5 rounded" />
                    <span class="text-sm text-text-primary">{{ tal.tree ?? t('common.labels.unknown') }}</span>
                    <span v-if="tal.points" class="text-sm text-text-muted ml-auto">{{ formatPoints(tal.points) }}</span>
                  </div>
                </div>
              </div>

              <!-- Glyphs -->
              <div v-if="glyphs.length > 0">
                <div class="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">{{ t('characterDetail.glyphs') }}</div>
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
                <div class="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">{{ t('characterDetail.stats') }}</div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <div v-if="meta.gear_score" class="flex items-center gap-2 px-3 py-2 bg-amber-500/10 rounded-lg border border-amber-500/20">
                    <span class="text-amber-300">⚡</span>
                    <div>
                      <div class="text-[10px] text-text-muted">{{ t('characterDetail.gearScore') }}</div>
                      <div class="text-sm font-bold text-amber-300">{{ meta.gear_score }}</div>
                    </div>
                  </div>
                  <div v-if="meta.honorable_kills" class="flex items-center gap-2 px-3 py-2 bg-red-500/10 rounded-lg border border-red-500/20">
                    <span class="text-red-400">⚔</span>
                    <div>
                      <div class="text-[10px] text-text-muted">{{ t('characterDetail.honorableKills') }}</div>
                      <div class="text-sm font-bold text-red-300">{{ meta.honorable_kills.toLocaleString() }}</div>
                    </div>
                  </div>
                  <div v-if="meta.faction" class="flex items-center gap-2 px-3 py-2 bg-bg-secondary rounded-lg border border-border-default">
                    <span>{{ meta.faction === 'Alliance' ? '🔵' : '🔴' }}</span>
                    <div>
                      <div class="text-[10px] text-text-muted">{{ t('common.fields.faction') }}</div>
                      <div class="text-sm text-text-primary">{{ meta.faction }}</div>
                    </div>
                  </div>
                  <div v-if="meta.guild" class="flex items-center gap-2 px-3 py-2 bg-green-500/10 rounded-lg border border-green-500/20">
                    <span class="text-green-400">🛡</span>
                    <div class="min-w-0">
                      <div class="text-[10px] text-text-muted">{{ t('common.labels.guild') }}</div>
                      <div class="text-sm text-green-300 truncate">&lt;{{ meta.guild }}&gt;</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Last synced -->
              <div v-if="meta.last_synced" class="text-[10px] text-text-muted pt-2 border-t border-[#2a3450]">
                {{ t('characterDetail.lastSynced') }} {{ formatDate(meta.last_synced) }}
              </div>
            </div>

            <!-- Right column: equipment (only when items exist) -->
            <div v-if="equipment.length > 0" class="px-4 py-3 overflow-y-auto">
              <div class="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">
                {{ t('characterDetail.equipment', { count: equipment.length }) }}
              </div>
              <div class="space-y-0.5" ref="equipmentContainer">
                <!-- Wowhead mode: entire row is a link for tooltip on hover -->
                <template v-if="useWowhead">
                  <a
                    v-for="(item, i) in equipment"
                    :key="i"
                    :href="item.item ? `https://www.wowhead.com/wotlk/item=${item.item}` : undefined"
                    :data-wowhead="item.item ? `item=${item.item}&domain=wotlk` : undefined"
                    target="_blank"
                    class="equip-link flex items-center gap-2 px-2 py-1.5 rounded hover:bg-[#1a2035] transition-colors no-underline cursor-pointer"
                    @click.stop
                  >
                    <!-- Default slot icon — hidden once Wowhead injects its own item icon -->
                    <div
                      class="slot-icon-fallback w-8 h-8 flex-shrink-0 rounded flex items-center justify-center text-[10px] font-bold"
                      :class="slotIconClasses(item)"
                    >
                      <svg v-if="EQUIP_SLOTS[i]?.svg" class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                        <path :d="EQUIP_SLOTS[i].svg" />
                      </svg>
                      <span v-else>{{ EQUIP_SLOTS[i]?.abbr ?? '?' }}</span>
                    </div>
                    <div class="flex-1 min-w-0">
                      <span
                        class="text-[12px] font-medium truncate block"
                        :class="itemQualityText(item)"
                      >{{ item.name }}</span>
                      <div class="text-[10px] text-text-muted flex items-center gap-1.5">
                        <span>{{ equipSlotLabel(i) }}</span>
                        <span v-if="item.enchant" class="text-green-400">✦ {{ t('characterDetail.enchanted') }}</span>
                        <span v-if="item.gems?.length" class="text-blue-400">◆ {{ item.gems.length }} gem{{ item.gems.length > 1 ? 's' : '' }}</span>
                      </div>
                    </div>
                  </a>
                </template>
                <!-- Basic mode: show inline stats without Wowhead -->
                <template v-else>
                  <div
                    v-for="(item, i) in equipment"
                    :key="i"
                    class="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-[#1a2035] transition-colors"
                  >
                    <!-- WoW-themed slot icon -->
                    <div
                      class="w-8 h-8 flex-shrink-0 rounded flex items-center justify-center text-[10px] font-bold"
                      :class="slotIconClasses(item)"
                    >
                      <svg v-if="EQUIP_SLOTS[i]?.svg" class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                        <path :d="EQUIP_SLOTS[i].svg" />
                      </svg>
                      <span v-else>{{ EQUIP_SLOTS[i]?.abbr ?? '?' }}</span>
                    </div>
                    <div class="flex-1 min-w-0">
                      <span
                        class="text-[12px] font-medium truncate block"
                        :class="itemQualityText(item)"
                      >{{ item.name }}</span>
                      <div class="text-[10px] text-text-muted flex items-center gap-1.5">
                        <span>{{ equipSlotLabel(i) }}</span>
                        <span v-if="item.quality != null" class="capitalize" :class="itemQualityText(item)">{{ qualityLabel(item.quality) }}</span>
                        <span v-if="item.enchant" class="text-green-400">✦ {{ item.enchant }}</span>
                        <span v-if="item.gems?.length" class="text-blue-400">◆ {{ item.gems.map(g => g.name || g).join(', ') }}</span>
                      </div>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useWowIcons } from '@/composables/useWowIcons'
import { normalizeSpecName, getItemQuality, getItemQualityText, getItemQualityLabel } from '@/constants'
import { refreshWowheadTooltips } from '@/composables/useWowheadTooltips'
import { useFormatting } from '@/composables/useFormatting'

const { t } = useI18n()

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  character: { type: Object, default: null },
  useWowhead: { type: Boolean, default: true },
})

defineEmits(['update:modelValue'])

const { getClassIcon, getClassColor, getSpecIcon, getRoleIcon, getProfessionIcon } = useWowIcons()
const { formatDate } = useFormatting()

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

// Refresh Wowhead tooltips when modal opens or equipment changes (only if enabled)
watch(() => props.modelValue, (visible) => {
  if (visible && equipment.value.length > 0 && props.useWowhead) refreshWowheadTooltips()
})
watch(equipment, (items) => {
  if (props.modelValue && items.length > 0 && props.useWowhead) refreshWowheadTooltips()
})
onMounted(() => {
  if (props.modelValue && equipment.value.length > 0 && props.useWowhead) refreshWowheadTooltips()
})

// Equipment slot definitions with WoW-themed SVG paths and abbreviations
const EQUIP_SLOTS = [
  { label: 'Head',      abbr: 'HD', svg: 'M12 2C9 2 6 4 5 7l-1 5c0 1 .5 2 1.5 2h1L7 17c0 1 .5 2 1.5 2h7c1 0 1.5-1 1.5-2l.5-3h1c1 0 1.5-1 1.5-2l-1-5c-1-3-4-5-7-5z' },
  { label: 'Neck',      abbr: 'NK', svg: 'M12 2a3 3 0 00-3 3v1H7l-1 4 2 2v8a2 2 0 004 0v-8l2-2-1-4h-2V5a1 1 0 012 0v1h2l-1-4h-2V5a3 3 0 00-3-3z' },
  { label: 'Shoulders', abbr: 'SH', svg: 'M2 10c0-2 2-4 4-4h2a4 4 0 018 0h2c2 0 4 2 4 4v2c0 1-1 2-2 2h-4v-4h-4v4H6c-1 0-2-1-2-2v-2z' },
  { label: 'Back',      abbr: 'BK', svg: 'M8 3h8l2 4v10c0 2-1 4-3 4H9c-2 0-3-2-3-4V7l2-4zm2 2v3h4V5h-4z' },
  { label: 'Chest',     abbr: 'CH', svg: 'M6 3h12l2 5v8c0 2-2 4-4 4h-2v-6h-4v6H8c-2 0-4-2-4-4V8l2-5zm4 2v4h4V5h-4z' },
  { label: 'Shirt',     abbr: 'SR', svg: 'M7 4h10l3 3-2 2-2-1v12H8V8L6 9 4 7l3-3z' },
  { label: 'Tabard',    abbr: 'TB', svg: 'M7 3h10v2l2 1v4l-2 1v10H7V11l-2-1V6l2-1V3zm3 4v6h4V7h-4z' },
  { label: 'Wrists',    abbr: 'WR', svg: 'M6 8h12c1 0 2 1 2 2v4c0 1-1 2-2 2H6c-1 0-2-1-2-2v-4c0-1 1-2 2-2zm2 2v4h2v-4H8zm4 0v4h2v-4h-2z' },
  { label: 'Hands',     abbr: 'HN', svg: 'M8 4v6H6v4h2v2h2v-5h1v5h2v-5h1v5h2v-2h2v-4h-2V4h-2v5h-1V3h-2v6h-1V4H8z' },
  { label: 'Waist',     abbr: 'WA', svg: 'M4 10h16c1 0 2 1 2 2v2c0 1-1 2-2 2H4c-1 0-2-1-2-2v-2c0-1 1-2 2-2zm7 1v4h2v-4h-2z' },
  { label: 'Legs',      abbr: 'LG', svg: 'M7 4h10l1 8-2 8h-3l-1-7-1 7H8l-2-8 1-8zm3 2v4h4V6h-4z' },
  { label: 'Feet',      abbr: 'FT', svg: 'M6 8h4v6H6l-2 2v2h6v-4h4v4h6v-2l-2-2h-4V8h4l1-2H5l1 2z' },
  { label: 'Ring 1',    abbr: 'R1', svg: 'M12 4a8 8 0 100 16 8 8 0 000-16zm0 3a5 5 0 110 10 5 5 0 010-10z' },
  { label: 'Ring 2',    abbr: 'R2', svg: 'M12 4a8 8 0 100 16 8 8 0 000-16zm0 3a5 5 0 110 10 5 5 0 010-10z' },
  { label: 'Trinket 1', abbr: 'T1', svg: 'M12 2l3 7h7l-5.5 4 2 7L12 16l-6.5 4 2-7L2 9h7l3-7z' },
  { label: 'Trinket 2', abbr: 'T2', svg: 'M12 2l3 7h7l-5.5 4 2 7L12 16l-6.5 4 2-7L2 9h7l3-7z' },
  { label: 'Main Hand', abbr: 'MH', svg: 'M4 20l2-2 4 2 8-12 2-4-4 2-12 8 2 4-2 2z' },
  { label: 'Off Hand',  abbr: 'OH', svg: 'M6 4h12c1 0 2 1 2 2v12c0 1-1 2-2 2H6c-1 0-2-1-2-2V6c0-1 1-2 2-2zm2 3v10h8V7H8z' },
  { label: 'Ranged',    abbr: 'RN', svg: 'M4 4l16 16M4 20L20 4M12 2v4M12 18v4M2 12h4M18 12h4' },
]

function equipSlotLabel(index) {
  return EQUIP_SLOTS[index]?.label ?? `Slot ${index + 1}`
}

function slotIconClasses(item) {
  const q = getItemQuality(item)
  return `${q.border} ${q.bg} border`
}

function itemQualityText(item) {
  return getItemQualityText(item)
}

function qualityLabel(q) {
  return getItemQualityLabel(q)
}

function formatPoints(points) {
  if (Array.isArray(points)) return points.join('/')
  return String(points)
}
</script>

<style>
/*
 * Hide default equipment slot icons when Wowhead has injected its own item icons.
 * Wowhead's iconizeLinks adds elements with class 'iconsmall' / 'iconmedium' / 'iconlarge'.
 * The :has() selector detects their presence and hides our fallback icon.
 */
.equip-link:has(.iconsmall, .iconmedium, .iconlarge) > .slot-icon-fallback {
  display: none;
}
</style>
