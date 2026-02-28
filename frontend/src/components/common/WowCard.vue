<template>
  <div
    class="rounded-lg border border-[#2a3450] bg-[#141926]"
    :class="[
      gold ? 'border-[#c9a930] shadow-gold' : '',
      padded ? 'p-4 md:p-6' : '',
      className
    ]"
  >
    <slot />
  </div>
</template>

<script setup>
defineProps({
  gold: { type: Boolean, default: false },
  padded: { type: Boolean, default: true },
  className: { type: String, default: '' }
})
</script>
