<template>
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
    <WowCard v-for="stat in stats" :key="stat.label" class="text-center">
      <div class="text-2xl font-bold" :class="stat.color">{{ stat.value }}</div>
      <div class="text-xs text-text-muted mt-1">{{ stat.label }}</div>
    </WowCard>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import WowCard from '@/components/common/WowCard.vue'

const props = defineProps({
  records: { type: Array, default: () => [] },
  events:  { type: Array, default: () => [] }
})

const stats = computed(() => {
  const total = props.events.length
  const attended = props.records.filter(r => r.attended).length
  const rate = total > 0 ? Math.round((attended / total) * 100) : 0

  const presentCount   = props.records.filter(r => r.attended).length
  const absentCount    = props.records.filter(r => !r.attended).length
  const benchCount     = props.records.filter(r => r.bench).length

  return [
    { label: 'Total Raids',       value: total,        color: 'text-accent-blue' },
    { label: 'Attended',          value: presentCount, color: 'text-green-400' },
    { label: 'Absent',            value: absentCount,  color: 'text-red-400' },
    { label: 'Attendance Rate',   value: `${rate}%`,   color: rate >= 75 ? 'text-green-400' : rate >= 50 ? 'text-yellow-400' : 'text-red-400' }
  ]
})
</script>
