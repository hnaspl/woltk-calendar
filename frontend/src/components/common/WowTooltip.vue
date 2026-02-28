<template>
  <div class="relative inline-flex" @mouseenter="show = true" @mouseleave="show = false">
    <slot />
    <Transition name="fade">
      <div
        v-if="show && text"
        class="absolute z-50 px-2.5 py-1.5 text-xs text-text-primary bg-[#1c2333] border border-[#2a3450] rounded shadow-lg whitespace-nowrap pointer-events-none"
        :class="positionClass"
      >
        {{ text }}
        <!-- Arrow -->
        <span class="absolute w-2 h-2 bg-[#1c2333] border-[#2a3450] rotate-45" :class="arrowClass" />
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  text: { type: String, default: '' },
  position: { type: String, default: 'top', validator: v => ['top', 'bottom', 'left', 'right'].includes(v) }
})

const show = ref(false)

const positionClass = computed(() => ({
  top:    'bottom-full left-1/2 -translate-x-1/2 mb-2',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
  left:   'right-full top-1/2 -translate-y-1/2 mr-2',
  right:  'left-full top-1/2 -translate-y-1/2 ml-2'
}[props.position]))

const arrowClass = computed(() => ({
  top:    'top-full left-1/2 -translate-x-1/2 -mt-1 border-b border-r',
  bottom: 'bottom-full left-1/2 -translate-x-1/2 -mb-1 border-t border-l',
  left:   'left-full top-1/2 -translate-y-1/2 -ml-1 border-t border-r',
  right:  'right-full top-1/2 -translate-y-1/2 -mr-1 border-b border-l'
}[props.position]))
</script>
