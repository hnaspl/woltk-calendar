<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        :aria-label="title"
        aria-modal="true"
      >
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/70 backdrop-blur-sm"
          @click="onBackdropClick"
        />

        <!-- Panel -->
        <div
          class="relative z-10 w-full max-h-[90vh] overflow-y-auto rounded-xl border border-[#2a3450] bg-[#141926] shadow-2xl"
          :class="widthClass"
        >
          <!-- Header -->
          <div class="flex items-center justify-between border-b border-[#2a3450] px-6 py-4">
            <h2 class="wow-heading text-lg">{{ title }}</h2>
            <button
              type="button"
              class="p-1 rounded text-text-muted hover:text-text-primary hover:bg-bg-tertiary transition-colors"
              @click="emit('update:modelValue', false)"
              aria-label="Close modal"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div class="px-6 py-4">
            <slot />
          </div>

          <!-- Footer -->
          <div v-if="$slots.footer" class="border-t border-[#2a3450] px-6 py-4">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  title: { type: String, default: '' },
  size: { type: String, default: 'md', validator: v => ['sm', 'md', 'lg', 'xl'].includes(v) },
  closeOnBackdrop: { type: Boolean, default: true }
})

const emit = defineEmits(['update:modelValue'])

const widthClass = computed(() => ({
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl'
}[props.size]))

function onBackdropClick() {
  if (props.closeOnBackdrop) emit('update:modelValue', false)
}
</script>
