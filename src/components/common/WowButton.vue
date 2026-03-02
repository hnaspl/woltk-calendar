<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    class="inline-flex items-center justify-center gap-2 rounded font-semibold text-sm transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[#0a0e17] disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2"
    :class="variantClass"
    v-bind="$attrs"
  >
    <!-- Loading spinner -->
    <svg
      v-if="loading"
      class="w-4 h-4 animate-spin flex-shrink-0"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
    </svg>
    <slot />
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: v => ['primary', 'secondary', 'danger', 'ghost'].includes(v)
  },
  type: { type: String, default: 'button' },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false }
})

const variantClass = computed(() => {
  switch (props.variant) {
    case 'primary':
      return 'bg-accent-gold text-[#0a0e17] hover:bg-yellow-400 focus:ring-accent-gold'
    case 'secondary':
      return 'bg-bg-tertiary text-text-primary border border-border-default hover:border-border-gold hover:text-accent-gold focus:ring-border-gold'
    case 'danger':
      return 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500'
    case 'ghost':
      return 'bg-transparent text-text-muted hover:text-text-primary hover:bg-bg-tertiary focus:ring-border-default'
    default:
      return 'bg-accent-gold text-[#0a0e17] hover:bg-yellow-400 focus:ring-accent-gold'
  }
})
</script>
