<template>
  <span
    class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border"
    :class="statusClass"
  >
    <span class="w-1.5 h-1.5 rounded-full" :class="dotClass" />
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true }
})

const statusMap = {
  draft:      { label: 'Draft',      cls: 'text-gray-300 bg-gray-500/10 border-gray-500/30',     dot: 'bg-gray-400' },
  open:       { label: 'Open',       cls: 'text-green-300 bg-green-500/10 border-green-500/30',  dot: 'bg-green-400' },
  locked:     { label: 'Locked',     cls: 'text-yellow-300 bg-yellow-500/10 border-yellow-500/30', dot: 'bg-yellow-400' },
  completed:  { label: 'Completed',  cls: 'text-blue-300 bg-blue-500/10 border-blue-500/30',     dot: 'bg-blue-400' },
  cancelled:  { label: 'Cancelled',  cls: 'text-red-300 bg-red-500/10 border-red-500/30',        dot: 'bg-red-400' },
}

const resolved = computed(() => statusMap[props.status?.toLowerCase()] ?? {
  label: props.status,
  cls: 'text-gray-300 bg-gray-500/10 border-gray-500/30',
  dot: 'bg-gray-400'
})

const label = computed(() => resolved.value.label)
const statusClass = computed(() => resolved.value.cls)
const dotClass = computed(() => resolved.value.dot)
</script>
