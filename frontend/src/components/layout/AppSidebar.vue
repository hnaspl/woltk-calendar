<template>
  <aside class="flex-col w-64 bg-[#0d111d] border-r border-[#2a3450] h-screen overflow-y-auto">
    <!-- Logo / Guild branding -->
    <div class="flex items-center gap-3 px-5 py-5 border-b border-[#2a3450]">
      <img
        :src="logoIcon"
        alt="WoW Calendar"
        class="w-9 h-9 rounded border border-border-gold"
      />
      <div>
        <div class="text-sm font-bold text-accent-gold font-wow leading-tight">Raid Calendar</div>
        <div class="text-xs text-text-muted">WotLK Warmane</div>
      </div>
    </div>

    <!-- Guild Switcher -->
    <div class="px-4 py-3 border-b border-[#2a3450]">
      <label class="text-xs text-text-muted uppercase tracking-wider mb-1 block">Guild</label>
      <select
        :value="guildStore.currentGuild?.id ?? ''"
        class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-2 py-1.5 focus:border-border-gold outline-none"
        @change="onGuildChange"
      >
        <option v-if="!guildStore.guilds.length" value="">No guilds</option>
        <option
          v-for="g in guildStore.guilds"
          :key="g.id"
          :value="g.id"
        >{{ g.name }}</option>
      </select>
    </div>

    <!-- Navigation links -->
    <nav class="flex-1 px-3 py-4 space-y-0.5">
      <template v-for="group in navGroups" :key="group.label">
        <div class="text-xs text-text-muted uppercase tracking-wider px-2 py-2 mt-2">{{ group.label }}</div>
        <RouterLink
          v-for="item in group.items"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-text-muted transition-colors hover:text-text-primary hover:bg-bg-tertiary"
          active-class="bg-bg-tertiary text-accent-gold border-l-2 border-accent-gold"
          @click="uiStore.closeSidebar()"
        >
          <component :is="item.icon" class="w-4 h-4 flex-shrink-0" />
          {{ item.label }}
        </RouterLink>
      </template>
    </nav>

    <!-- User info at bottom -->
    <div class="px-4 py-4 border-t border-[#2a3450]">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-full bg-bg-tertiary border border-border-default flex items-center justify-center text-xs text-accent-gold font-bold uppercase">
          {{ userInitial }}
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-sm text-text-primary truncate">{{ authStore.user?.username ?? 'Unknown' }}</div>
          <div class="text-xs text-text-muted truncate">{{ authStore.user?.email ?? '' }}</div>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed, h } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'
import { useUiStore } from '@/stores/ui'
import { useWowIcons } from '@/composables/useWowIcons'

const { getRaidIcon } = useWowIcons()
const logoIcon = getRaidIcon('icc')

const authStore = useAuthStore()
const guildStore = useGuildStore()
const uiStore = useUiStore()

const userInitial = computed(() => authStore.user?.username?.[0]?.toUpperCase() ?? '?')

// Simple SVG icon components using render functions
const icons = {
  dashboard: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' })
  ]),
  calendar: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' })
  ]),
  chars: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' })
  ]),
  attendance: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4' })
  ]),
  settings: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' }),
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z' })
  ]),
  raids: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' })
  ]),
  templates: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z' })
  ])
}

const navGroups = computed(() => [
  {
    label: 'Overview',
    items: [
      { label: 'Dashboard', to: '/dashboard', icon: icons.dashboard },
      { label: 'Calendar', to: '/calendar', icon: icons.calendar },
      { label: 'Characters', to: '/characters', icon: icons.chars },
      { label: 'Attendance', to: '/attendance', icon: icons.attendance }
    ]
  },
  {
    label: 'Guild',
    items: [
      { label: 'Settings', to: '/guild/settings', icon: icons.settings },
      { label: 'Raid Definitions', to: '/guild/raid-definitions', icon: icons.raids },
      { label: 'Templates', to: '/guild/templates', icon: icons.templates }
    ]
  }
])

function onGuildChange(e) {
  const id = e.target.value
  const guild = guildStore.guilds.find(g => String(g.id) === String(id))
  if (guild) guildStore.setCurrentGuild(guild)
}
</script>
