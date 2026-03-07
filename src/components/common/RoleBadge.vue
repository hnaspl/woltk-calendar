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
    <span class="capitalize">{{ roleLabel }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { useWowIcons } from '@/composables/useWowIcons'
import { ROLE_LABEL_MAP, ROLE_STYLE_MAP } from '@/constants'

const props = defineProps({
  role: { type: String, required: true }
})

const { getRoleIcon } = useWowIcons()

const iconUrl = computed(() => getRoleIcon(props.role))

const roleLabel = computed(() => ROLE_LABEL_MAP[props.role?.toLowerCase()] ?? props.role)

const roleClass = computed(() => {
  return ROLE_STYLE_MAP[props.role?.toLowerCase()] ?? 'bg-gray-500/20 text-gray-300 border border-gray-500/30'
})
</script>
