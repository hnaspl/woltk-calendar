<template>
  <WowCard>
    <h3 class="wow-heading text-base mb-4">{{ t('composition.title') }}</h3>

    <div v-if="total === 0" class="text-center py-4 text-text-muted text-sm">
      {{ t('composition.noPlayers') }}
    </div>

    <div v-else class="space-y-3 sm:space-y-4">
      <div v-for="role in roleSummary" :key="role.name">
        <div class="flex items-center justify-between mb-1.5">
          <div class="flex items-center gap-2">
            <RoleBadge :role="role.name" />
            <span class="text-sm text-text-primary font-medium">{{ role.count }}</span>
            <span class="text-xs text-text-muted">/ {{ role.target }}</span>
          </div>
          <span
            class="text-xs font-semibold"
            :class="role.count >= role.target ? 'text-green-400' : 'text-yellow-400'"
          >
            {{ role.count >= role.target ? '✓ ' + t('composition.full') : t('composition.needed', { count: role.target - role.count }) }}
          </span>
        </div>
        <!-- Progress bar -->
        <div class="w-full h-2 bg-bg-tertiary rounded-full overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-500"
            :class="role.barClass"
            :style="{ width: `${Math.min(100, (role.count / Math.max(role.target, 1)) * 100)}%` }"
          />
        </div>
      </div>

      <hr class="gold-divider" />

      <div class="flex items-center justify-between text-sm">
        <span class="text-text-muted">{{ t('composition.totalAssigned') }}</span>
        <span class="text-text-primary font-bold">{{ total }} / {{ maxSize ?? '?' }}</span>
      </div>
    </div>
  </WowCard>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import RoleBadge from '@/components/common/RoleBadge.vue'

const { t } = useI18n()

const props = defineProps({
  lineupCounts: { type: Object, default: null },
  maxSize: { type: Number, default: null },
  // Slot targets from the raid definition
  meleeDpsSlots:  { type: Number, default: 2 },
  mainTankSlots:  { type: Number, default: 1 },
  offTankSlots:   { type: Number, default: 1 },
  healerSlots:    { type: Number, default: 5 },
  rangeDpsSlots:  { type: Number, default: 18 }
})

function countRole(role) {
  return props.lineupCounts?.[role] ?? 0
}

const total = computed(() =>
  countRole('main_tank') + countRole('off_tank') + countRole('melee_dps') + countRole('healer') + countRole('range_dps')
)

const roleSummary = computed(() => [
  {
    name: 'main_tank',
    count: countRole('main_tank'),
    target: props.mainTankSlots,
    barClass: 'bg-blue-300'
  },
  {
    name: 'off_tank',
    count: countRole('off_tank'),
    target: props.offTankSlots,
    barClass: 'bg-cyan-400'
  },
  {
    name: 'melee_dps',
    count: countRole('melee_dps'),
    target: props.meleeDpsSlots,
    barClass: 'bg-blue-400'
  },
  {
    name: 'healer',
    count: countRole('healer'),
    target: props.healerSlots,
    barClass: 'bg-green-400'
  },
  {
    name: 'range_dps',
    count: countRole('range_dps'),
    target: props.rangeDpsSlots,
    barClass: 'bg-red-400'
  }
].filter(r => r.target > 0))
</script>
