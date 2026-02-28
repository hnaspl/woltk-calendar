<template>
  <div
    class="relative inline-flex"
    @mouseenter="onMouseEnter"
    @mouseleave="onMouseLeave"
    @focusin="onFocusIn"
    @focusout="onMouseLeave"
    @dragstart="onChildDragStart"
    @dragend="onChildDragEnd"
  >
    <slot />
    <Transition name="fade">
      <div
        v-if="show && character && !dragging"
        class="absolute z-50 w-72 bg-[#0d1117] border border-[#2a3450] rounded-lg shadow-xl pointer-events-none"
        :class="positionClass"
      >
        <!-- Header -->
        <div class="flex items-center gap-3 px-3 py-2 border-b border-[#2a3450] bg-[#161b22] rounded-t-lg">
          <img
            v-if="classIcon"
            :src="classIcon"
            :alt="character.class_name"
            class="w-8 h-8 rounded border border-[#2a3450]"
          />
          <div class="min-w-0">
            <div class="text-sm font-semibold truncate" :style="{ color: classColor }">
              {{ character.name }}
            </div>
            <div class="text-[10px] text-text-muted">
              Lv {{ meta.level ?? character.level ?? '?' }}
              {{ meta.race ?? '' }}
              {{ character.class_name ?? '' }}
            </div>
          </div>
          <a
            v-if="character.armory_url"
            :href="character.armory_url"
            target="_blank"
            class="ml-auto text-[10px] text-amber-400 hover:underline flex-shrink-0"
            @click.stop
          >Armory</a>
        </div>

        <!-- Body -->
        <div class="px-3 py-2 space-y-2 text-xs">
          <!-- Specs & Role -->
          <table v-if="character.primary_spec || character.secondary_spec || character.tertiary_spec || character.default_role" class="w-full">
            <tbody>
              <tr v-if="character.default_role">
                <td class="text-text-muted pr-2 py-0.5 whitespace-nowrap">Role</td>
                <td class="text-text-primary py-0.5 capitalize">{{ character.default_role?.replace('_', ' ') }}</td>
              </tr>
              <tr v-if="character.primary_spec">
                <td class="text-text-muted pr-2 py-0.5 whitespace-nowrap">Primary</td>
                <td class="py-0.5"><span class="px-1.5 py-0.5 bg-amber-500/15 text-amber-300 rounded text-[11px]">⭐ {{ character.primary_spec }}</span></td>
              </tr>
              <tr v-if="character.secondary_spec">
                <td class="text-text-muted pr-2 py-0.5 whitespace-nowrap">Secondary</td>
                <td class="py-0.5"><span class="px-1.5 py-0.5 bg-gray-500/15 text-gray-400 rounded text-[11px]">{{ character.secondary_spec }}</span></td>
              </tr>
              <tr v-if="character.tertiary_spec">
                <td class="text-text-muted pr-2 py-0.5 whitespace-nowrap">Tertiary</td>
                <td class="py-0.5"><span class="px-1.5 py-0.5 bg-gray-500/15 text-gray-400 rounded text-[11px]">{{ character.tertiary_spec }}</span></td>
              </tr>
            </tbody>
          </table>

          <!-- Talents (from metadata) -->
          <div v-if="talents.length > 0">
            <div class="text-[10px] uppercase tracking-wider text-text-muted mb-1">Talent Trees</div>
            <table class="w-full">
              <tbody>
                <tr v-for="(t, i) in talents" :key="i">
                  <td class="text-text-primary py-0.5">{{ t.tree ?? 'Unknown' }}</td>
                  <td v-if="t.points" class="text-text-muted text-right py-0.5">{{ formatPoints(t.points) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Glyphs (from metadata) -->
          <div v-if="glyphs.length > 0">
            <div class="text-[10px] uppercase tracking-wider text-text-muted mb-1">Glyphs</div>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="(g, i) in glyphs"
                :key="i"
                class="text-[10px] px-1.5 py-0.5 bg-purple-500/10 border border-purple-500/20 rounded text-purple-300"
              >{{ g.name ?? g }}</span>
            </div>
          </div>

          <!-- Professions -->
          <div v-if="professions.length > 0">
            <div class="text-[10px] uppercase tracking-wider text-text-muted mb-1">Professions</div>
            <table class="w-full">
              <tbody>
                <tr v-for="p in professions" :key="p.name">
                  <td class="text-text-primary py-0.5">{{ p.name }}</td>
                  <td class="text-amber-300 text-right py-0.5">{{ p.skill }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Stats table -->
          <table v-if="hasStats" class="w-full border-t border-[#2a3450] pt-1">
            <tbody>
              <tr v-if="meta.achievement_points">
                <td class="text-text-muted py-0.5"><span class="text-amber-400">🏆</span> Achievements</td>
                <td class="text-text-primary text-right py-0.5">{{ meta.achievement_points }}</td>
              </tr>
              <tr v-if="meta.honorable_kills">
                <td class="text-text-muted py-0.5"><span class="text-red-400">⚔</span> HKs</td>
                <td class="text-text-primary text-right py-0.5">{{ meta.honorable_kills }}</td>
              </tr>
              <tr v-if="meta.faction">
                <td class="text-text-muted py-0.5">{{ meta.faction === 'Alliance' ? '🔵' : '🔴' }} Faction</td>
                <td class="text-text-primary text-right py-0.5">{{ meta.faction }}</td>
              </tr>
              <tr v-if="meta.guild">
                <td class="text-text-muted py-0.5"><span class="text-green-400">🛡</span> Guild</td>
                <td class="text-text-primary text-right py-0.5 truncate max-w-[120px]">&lt;{{ meta.guild }}&gt;</td>
              </tr>
              <tr v-if="meta.gear_score">
                <td class="text-text-muted py-0.5"><span class="text-amber-300">⚡</span> Gear Score</td>
                <td class="text-amber-300 text-right py-0.5 font-semibold">{{ meta.gear_score }}</td>
              </tr>
            </tbody>
          </table>

          <!-- Equipment summary -->
          <div v-if="equipment.length > 0">
            <div class="text-[10px] uppercase tracking-wider text-text-muted mb-1">
              Equipment ({{ equipment.length }} slots)
            </div>
            <div class="max-h-28 overflow-y-auto space-y-0.5 pr-1 scrollbar-thin">
              <div
                v-for="(item, i) in equipment"
                :key="i"
                class="text-[11px] text-text-muted truncate"
              >
                <span class="text-text-primary">{{ item.name }}</span>
              </div>
            </div>
          </div>

          <!-- Last synced -->
          <div v-if="meta.last_synced" class="text-[10px] text-text-muted pt-1 border-t border-[#2a3450]">
            Synced: {{ formatDate(meta.last_synced) }}
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useWowIcons } from '@/composables/useWowIcons'

const props = defineProps({
  character: { type: Object, default: null },
  position: { type: String, default: 'right', validator: v => ['top', 'bottom', 'left', 'right'].includes(v) }
})

const show = ref(false)
const hideTimeout = ref(null)
const dragging = ref(false)
const { getClassIcon, getClassColor } = useWowIcons()

function onMouseEnter() {
  if (dragging.value) return
  if (hideTimeout.value) { clearTimeout(hideTimeout.value); hideTimeout.value = null }
  show.value = true
}

function onMouseLeave() {
  hideTimeout.value = setTimeout(() => { show.value = false }, 150)
}

function onFocusIn() {
  if (!dragging.value) show.value = true
}

/** Hide tooltip when a child element starts being dragged */
function onChildDragStart() {
  dragging.value = true
  show.value = false
  if (hideTimeout.value) { clearTimeout(hideTimeout.value); hideTimeout.value = null }
}

/** Re-enable tooltip after drag ends */
function onChildDragEnd() {
  dragging.value = false
}

const classIcon = computed(() => props.character?.class_name ? getClassIcon(props.character.class_name) : null)
const classColor = computed(() => props.character?.class_name ? getClassColor(props.character.class_name) : '#ccc')

const meta = computed(() => props.character?.metadata ?? {})
const talents = computed(() => meta.value.talents ?? [])
const glyphs = computed(() => meta.value.glyphs ?? [])
const professions = computed(() => meta.value.professions ?? [])
const equipment = computed(() => (meta.value.equipment ?? []).filter(e => e?.name))
const hasStats = computed(() =>
  meta.value.achievement_points || meta.value.honorable_kills || meta.value.faction || meta.value.guild || meta.value.gear_score
)

function formatPoints(points) {
  if (Array.isArray(points)) return points.join('/')
  return String(points)
}

function formatDate(iso) {
  if (!iso) return '?'
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

const positionClass = computed(() => ({
  top:    'bottom-full left-1/2 -translate-x-1/2 mb-2',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
  left:   'right-full top-0 mr-2',
  right:  'left-full top-0 ml-2'
}[props.position]))
</script>
