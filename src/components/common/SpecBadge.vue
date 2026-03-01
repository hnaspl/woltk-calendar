<template>
  <span
    class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-[#1c2333] border border-[#2a3450] text-text-muted"
  >
    <img
      v-if="iconUrl"
      :src="iconUrl"
      :alt="spec"
      class="w-4 h-4 rounded-sm object-cover flex-shrink-0"
      loading="lazy"
    />
    <span class="capitalize">{{ spec }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { useWowIcons } from '@/composables/useWowIcons'

const props = defineProps({
  spec: { type: String, required: true },
  className: { type: String, default: '' }
})

const { getSpecIcon } = useWowIcons()
const iconUrl = computed(() => getSpecIcon(props.spec, props.className))
</script>
