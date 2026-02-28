<template>
  <span
    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold border"
    :class="size === 25 ? 'text-yellow-300 bg-yellow-300/10 border-yellow-500/30' : 'text-sky-300 bg-sky-300/10 border-sky-500/30'"
  >
    {{ size }}-man
  </span>
</template>

<script setup>
defineProps({
  size: { type: Number, required: true }
})
</script>
