<template>
  <WowCard>
    <div class="flex items-center justify-between mb-4">
      <h3 class="wow-heading text-base">Signups</h3>
      <span class="text-sm text-text-muted">{{ signups.length }} total</span>
    </div>

    <div v-if="signups.length === 0" class="text-center py-6 text-text-muted text-sm">
      No signups yet.
    </div>

    <template v-for="group in groups" :key="group.status">
      <div v-if="group.items.length > 0" class="mb-5">
        <div class="flex items-center gap-2 mb-2">
          <StatusBadge :status="group.status" />
          <span class="text-xs text-text-muted">({{ group.items.length }})</span>
        </div>
        <div class="space-y-1.5">
          <CharacterTooltip
            v-for="signup in group.items"
            :key="signup.id"
            :character="signup.character"
            position="left"
          >
            <div
              class="flex items-center gap-3 px-3 py-2 rounded-lg bg-bg-tertiary/60 hover:bg-bg-tertiary transition-colors cursor-default w-full"
            >
              <!-- Class icon -->
              <img
                v-if="signup.character?.class_name"
                :src="getClassIcon(signup.character.class_name)"
                :alt="signup.character.class_name"
                class="w-7 h-7 rounded border border-border-default flex-shrink-0"
              />
              <div class="w-7 h-7 rounded bg-bg-secondary flex-shrink-0" v-else />

              <!-- Name + badges -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-medium text-text-primary truncate">
                    {{ signup.character?.name ?? 'Unknown' }}
                  </span>
                  <span v-if="charLevel(signup)" class="text-[10px] text-text-muted">
                    Lv{{ charLevel(signup) }}
                  </span>
                </div>
                <div class="flex items-center gap-1.5 mt-0.5 flex-wrap">
                  <ClassBadge v-if="signup.character?.class_name" :class-name="signup.character.class_name" />
                  <RoleBadge v-if="signup.chosen_role" :role="signup.chosen_role" />
                  <SpecBadge v-if="signup.chosen_spec" :spec="signup.chosen_spec" />
                  <!-- Professions inline -->
                  <span
                    v-for="prof in charProfessions(signup)"
                    :key="prof.name"
                    class="text-[10px] px-1.5 py-0.5 bg-[#1c2333] border border-[#2a3450] rounded text-text-muted"
                  >
                    {{ prof.name }} {{ prof.skill }}
                  </span>
                </div>
              </div>

              <!-- Achievement points -->
              <span
                v-if="charAchievements(signup)"
                class="text-[10px] text-amber-400 flex-shrink-0"
                title="Achievement Points"
              >
                🏆 {{ charAchievements(signup) }}
              </span>

              <!-- Note -->
              <WowTooltip v-if="signup.note" :text="signup.note" position="left">
                <svg class="w-4 h-4 text-text-muted flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"/>
                </svg>
              </WowTooltip>
            </div>
          </CharacterTooltip>
        </div>
      </div>
    </template>
  </WowCard>
</template>

<script setup>
import { computed } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import ClassBadge from '@/components/common/ClassBadge.vue'
import RoleBadge from '@/components/common/RoleBadge.vue'
import SpecBadge from '@/components/common/SpecBadge.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import WowTooltip from '@/components/common/WowTooltip.vue'
import CharacterTooltip from '@/components/common/CharacterTooltip.vue'
import { useWowIcons } from '@/composables/useWowIcons'

const props = defineProps({
  signups: { type: Array, default: () => [] }
})

const { getClassIcon } = useWowIcons()

const STATUS_ORDER = ['going', 'tentative', 'late', 'bench', 'declined']

const groups = computed(() =>
  STATUS_ORDER.map(status => ({
    status,
    items: props.signups.filter(s => s.status === status)
  }))
)

function charLevel(signup) {
  return signup.character?.metadata?.level ?? null
}

function charProfessions(signup) {
  return (signup.character?.metadata?.professions ?? []).slice(0, 2)
}

function charAchievements(signup) {
  return signup.character?.metadata?.achievement_points ?? null
}
</script>
