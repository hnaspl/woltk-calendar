<template>
  <div class="flex h-screen overflow-hidden bg-bg-primary">
    <!-- Desktop sidebar -->
    <AppSidebar class="hidden lg:flex" />

    <!-- Mobile sidebar overlay -->
    <Transition name="fade">
      <div
        v-if="uiStore.sidebarOpen"
        class="fixed inset-0 z-40 lg:hidden"
      >
        <div class="absolute inset-0 bg-black/60" @click="uiStore.closeSidebar()" />
        <AppSidebar class="relative z-50 flex w-64" />
      </div>
    </Transition>

    <!-- Main content area -->
    <div class="flex flex-col flex-1 min-w-0 overflow-hidden">
      <AppTopBar />

      <!-- Page content -->
      <main class="flex-1 overflow-y-auto pb-16 lg:pb-0">
        <slot />
      </main>
    </div>

    <!-- Mobile bottom nav -->
    <AppBottomNav class="lg:hidden" />

    <!-- Toast notifications -->
    <Transition name="slide-up">
      <div
        v-if="uiStore.toast"
        class="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 lg:bottom-6 lg:left-auto lg:right-6 lg:translate-x-0"
      >
        <div
          class="flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg text-sm font-medium max-w-sm"
          :class="toastClass"
        >
          <span>{{ uiStore.toast.message }}</span>
          <button
            type="button"
            class="ml-2 opacity-70 hover:opacity-100 transition-opacity"
            @click="uiStore.dismissToast()"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppSidebar from './AppSidebar.vue'
import AppTopBar from './AppTopBar.vue'
import AppBottomNav from './AppBottomNav.vue'
import { useUiStore } from '@/stores/ui'

const uiStore = useUiStore()

const toastClass = computed(() => {
  const type = uiStore.toast?.type
  if (type === 'success') return 'bg-green-900/80 border-green-600 text-green-200'
  if (type === 'error')   return 'bg-red-900/80 border-red-600 text-red-200'
  if (type === 'warning') return 'bg-yellow-900/80 border-yellow-600 text-yellow-200'
  return 'bg-bg-secondary border-border-default text-text-primary'
})
</script>

<style scoped>
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.3s ease; }
.slide-up-enter-from, .slide-up-leave-to { transform: translate(-50%, 20px); opacity: 0; }
@media (min-width: 1024px) {
  .slide-up-enter-from, .slide-up-leave-to { transform: translateY(20px); }
}
</style>
