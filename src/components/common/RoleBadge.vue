<template>
  <span
    class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold"
    :class="roleClass"
  >
    <img
      :src="iconUrl"
      :alt="role"
      class="w-4 h-4 rounded-sm object-cover flex-shrink-0"
      loading="lazy"
    />
    <span class="capitalize">{{ role }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { useWowIcons } from '@/composables/useWowIcons'

const props = defineProps({
  role: { type: String, required: true }
})

const { getRoleIcon } = useWowIcons()

const iconUrl = computed(() => getRoleIcon(props.role))

const roleClass = computed(() => {
  switch (props.role?.toLowerCase()) {
    case 'tank':   return 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
    case 'healer': return 'bg-green-500/20 text-green-300 border border-green-500/30'
    case 'dps':    return 'bg-red-500/20 text-red-300 border border-red-500/30'
    default:       return 'bg-gray-500/20 text-gray-300 border border-gray-500/30'
  }
})
</script>
