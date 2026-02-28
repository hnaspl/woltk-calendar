<template>
  <header class="flex items-center justify-between h-14 px-4 bg-[#0d111d] border-b border-[#2a3450] flex-shrink-0">
    <!-- Left: Hamburger (mobile) + Guild name -->
    <div class="flex items-center gap-3">
      <button
        type="button"
        class="lg:hidden p-1.5 rounded text-text-muted hover:text-text-primary hover:bg-bg-tertiary transition-colors"
        @click="uiStore.toggleSidebar()"
        aria-label="Toggle sidebar"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
        </svg>
      </button>

      <div>
        <h1 class="text-sm font-bold text-accent-gold font-wow leading-tight">
          {{ guildStore.currentGuild?.name ?? 'No Guild' }}
        </h1>
        <p class="text-xs text-text-muted leading-tight">{{ guildStore.currentGuild?.realm ?? '' }}</p>
      </div>
    </div>

    <!-- Right: notifications + profile -->
    <div class="flex items-center gap-2">
      <!-- Notifications bell -->
      <button
        type="button"
        class="relative p-2 rounded text-text-muted hover:text-text-primary hover:bg-bg-tertiary transition-colors"
        aria-label="Notifications"
        @click="notifOpen = !notifOpen"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
        </svg>
        <span
          v-if="unreadCount > 0"
          class="absolute top-1 right-1 w-2 h-2 rounded-full bg-red-500"
        />
      </button>

      <!-- Profile dropdown trigger -->
      <div class="relative">
        <button
          type="button"
          class="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-bg-tertiary transition-colors"
          @click="profileOpen = !profileOpen"
        >
          <div class="w-7 h-7 rounded-full bg-bg-tertiary border border-border-default flex items-center justify-center text-xs text-accent-gold font-bold uppercase">
            {{ userInitial }}
          </div>
          <span class="hidden sm:block text-sm text-text-primary">{{ authStore.user?.username ?? '' }}</span>
          <svg class="w-4 h-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
          </svg>
        </button>

        <!-- Profile dropdown -->
        <Transition name="fade">
          <div
            v-if="profileOpen"
            class="absolute right-0 top-full mt-1 w-48 bg-[#141926] border border-[#2a3450] rounded-lg shadow-xl z-30 overflow-hidden"
            v-click-outside="() => profileOpen = false"
          >
            <RouterLink
              to="/characters"
              class="flex items-center gap-2 px-4 py-2.5 text-sm text-text-primary hover:bg-bg-tertiary transition-colors"
              @click="profileOpen = false"
            >
              <svg class="w-4 h-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
              </svg>
              My Characters
            </RouterLink>
            <hr class="border-[#2a3450]" />
            <button
              type="button"
              class="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-400 hover:bg-bg-tertiary transition-colors"
              @click="handleLogout"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
              </svg>
              Sign Out
            </button>
          </div>
        </Transition>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'
import { useUiStore } from '@/stores/ui'

const authStore = useAuthStore()
const guildStore = useGuildStore()
const uiStore = useUiStore()
const router = useRouter()

const profileOpen = ref(false)
const notifOpen = ref(false)
const unreadCount = ref(0)

const userInitial = computed(() => authStore.user?.username?.[0]?.toUpperCase() ?? '?')

async function handleLogout() {
  profileOpen.value = false
  await authStore.logout()
  router.push('/login')
}

// Simple click-outside directive
const vClickOutside = {
  mounted(el, binding) {
    el.__clickOutside__ = (event) => {
      if (!el.contains(event.target)) binding.value(event)
    }
    document.addEventListener('click', el.__clickOutside__, true)
  },
  unmounted(el) {
    document.removeEventListener('click', el.__clickOutside__, true)
  }
}
</script>
