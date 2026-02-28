<template>
  <div
    class="relative inline-flex"
    @mouseenter="onMouseEnter"
    @mouseleave="onMouseLeave"
    @focusin="show = true"
    @focusout="onMouseLeave"
    tabindex="0"
  >
    <slot />
    <Transition name="fade">
      <div
        v-if="show && character"
        class="absolute z-50 w-72 bg-[#0d1117] border border-[#2a3450] rounded-lg shadow-xl"
        :class="positionClass"
        @mouseenter="onMouseEnter"
        @mouseleave="onMouseLeave"
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
          <!-- Specs -->
          <div v-if="character.primary_spec || character.secondary_spec">
            <div class="text-[10px] uppercase tracking-wider text-text-muted mb-1">Specializations</div>
            <div class="flex flex-wrap gap-1">
              <span v-if="character.primary_spec" class="px-1.5 py-0.5 bg-amber-500/15 text-amber-300 rounded text-[11px]">
                ⭐ {{ character.primary_spec }}
              </span>
              <span v-if="character.secondary_spec" class="px-1.5 py-0.5 bg-gray-500/15 text-gray-400 rounded text-[11px]">
                {{ character.secondary_spec }}
              </span>
            </div>
          </div>

          <!-- Talents (from metadata) -->
          <div v-if="talents.length > 0">
            <div class="text-[10px] uppercase tracking-wider text-text-muted mb-1">Talent Trees</div>
            <div class="space-y-0.5">
              <div v-for="(t, i) in talents" :key="i" class="flex items-center gap-1.5">
                <span class="text-text-primary">{{ t.tree ?? 'Unknown' }}</span>
                <span v-if="t.points" class="text-text-muted">({{ formatPoints(t.points) }})</span>
              </div>
            </div>
          </div>

          <!-- Professions -->
          <div v-if="professions.length > 0">
            <div class="text-[10px] uppercase tracking-wider text-text-muted mb-1">Professions</div>
            <div class="space-y-0.5">
              <div v-for="p in professions" :key="p.name" class="flex justify-between">
                <span class="text-text-primary">{{ p.name }}</span>
                <span class="text-amber-300">{{ p.skill }}</span>
              </div>
            </div>
          </div>

          <!-- Stats row -->
          <div class="flex flex-wrap gap-x-3 gap-y-1 pt-1 border-t border-[#2a3450]">
            <div v-if="meta.achievement_points" class="flex items-center gap-1">
              <span class="text-amber-400">🏆</span>
              <span class="text-text-muted">{{ meta.achievement_points }}</span>
            </div>
            <div v-if="meta.honorable_kills" class="flex items-center gap-1">
              <span class="text-red-400">⚔</span>
              <span class="text-text-muted">{{ meta.honorable_kills }}</span>
            </div>
            <div v-if="meta.faction" class="flex items-center gap-1">
              <span>{{ meta.faction === 'Alliance' ? '🔵' : '🔴' }}</span>
              <span class="text-text-muted">{{ meta.faction }}</span>
            </div>
            <div v-if="meta.guild" class="flex items-center gap-1">
              <span class="text-green-400">🛡</span>
              <span class="text-text-muted truncate max-w-[120px]">&lt;{{ meta.guild }}&gt;</span>
            </div>
          </div>

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
let hideTimeout = null
const { getClassIcon, getClassColor } = useWowIcons()

function onMouseEnter() {
  if (hideTimeout) { clearTimeout(hideTimeout); hideTimeout = null }
  show.value = true
}

function onMouseLeave() {
  hideTimeout = setTimeout(() => { show.value = false }, 150)
}

const classIcon = computed(() => props.character?.class_name ? getClassIcon(props.character.class_name) : null)
const classColor = computed(() => props.character?.class_name ? getClassColor(props.character.class_name) : '#ccc')

const meta = computed(() => props.character?.metadata ?? {})
const talents = computed(() => meta.value.talents ?? [])
const professions = computed(() => meta.value.professions ?? [])
const equipment = computed(() => (meta.value.equipment ?? []).filter(e => e?.name))

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
