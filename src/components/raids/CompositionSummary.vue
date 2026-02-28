<template>
  <WowCard>
    <h3 class="wow-heading text-base mb-4">Composition</h3>

    <div v-if="total === 0" class="text-center py-4 text-text-muted text-sm">
      No players assigned yet.
    </div>

    <div v-else class="space-y-4">
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
            {{ role.count >= role.target ? '✓ Full' : `${role.target - role.count} needed` }}
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
        <span class="text-text-muted">Total assigned</span>
        <span class="text-text-primary font-bold">{{ total }} / {{ maxSize ?? '?' }}</span>
      </div>
    </div>
  </WowCard>
</template>

<script setup>
import { computed } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import RoleBadge from '@/components/common/RoleBadge.vue'

const props = defineProps({
  lineupCounts: { type: Object, default: null },
  maxSize: { type: Number, default: null },
  // Slot targets from the raid definition
  tankSlots:      { type: Number, default: 2 },
  mainTankSlots:  { type: Number, default: 1 },
  offTankSlots:   { type: Number, default: 1 },
  healerSlots:    { type: Number, default: 5 },
  dpsSlots:       { type: Number, default: 18 }
})

function countRole(role) {
  return props.lineupCounts?.[role] ?? 0
}

const total = computed(() =>
  countRole('main_tank') + countRole('off_tank') + countRole('tank') + countRole('healer') + countRole('dps')
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
    name: 'tank',
    count: countRole('tank'),
    target: props.tankSlots,
    barClass: 'bg-blue-400'
  },
  {
    name: 'healer',
    count: countRole('healer'),
    target: props.healerSlots,
    barClass: 'bg-green-400'
  },
  {
    name: 'dps',
    count: countRole('dps'),
    target: props.dpsSlots,
    barClass: 'bg-red-400'
  }
].filter(r => r.target > 0))
</script>
