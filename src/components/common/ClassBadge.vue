<template>
  <span
    class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold"
    :style="{ backgroundColor: bgColor, color: textColor, borderColor: bgColor }"
  >
    <img
      v-if="iconUrl"
      :src="iconUrl"
      :alt="className"
      class="w-4 h-4 rounded-sm object-cover flex-shrink-0"
      loading="lazy"
    />
    <span>{{ displayName }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { useWowIcons } from '@/composables/useWowIcons'

const props = defineProps({
  className: { type: String, required: true }
})

const { getClassIcon, getClassColor } = useWowIcons()

const displayName = computed(() => {
  const n = props.className?.replace(/-/g, ' ') ?? ''
  return n.charAt(0).toUpperCase() + n.slice(1)
})

const iconUrl = computed(() => getClassIcon(props.className))

const bgColor = computed(() => getClassColor(props.className) + '28') // 16% opacity bg
const textColor = computed(() => getClassColor(props.className))
</script>
