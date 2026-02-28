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
        >{{ g.name }} ({{ g.realm_name }})</option>
      </select>
      <button
        type="button"
        class="mt-2 w-full flex items-center justify-center gap-1 text-xs text-accent-gold hover:text-yellow-300 transition-colors py-1"
        @click="showCreateGuild = true"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Create Guild
      </button>
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

  <!-- Create Guild Modal -->
  <Teleport to="body">
    <div v-if="showCreateGuild" class="fixed inset-0 z-[100] flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60" @click="showCreateGuild = false" />
      <div class="relative bg-bg-secondary border border-border-default rounded-lg shadow-xl w-full max-w-md mx-4 p-6 z-10">
        <h3 class="wow-heading text-lg mb-4">Create Guild</h3>
        <form @submit.prevent="doCreateGuild" class="space-y-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">Guild Name *</label>
            <input v-model="newGuild.name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" placeholder="My Guild" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Realm *</label>
            <select v-model="newGuild.realm_name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="">Select realm…</option>
              <option v-for="r in WARMANE_REALMS" :key="r" :value="r">{{ r }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Faction</label>
            <select v-model="newGuild.faction" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="">Select faction…</option>
              <option value="Alliance">Alliance</option>
              <option value="Horde">Horde</option>
            </select>
          </div>
          <div v-if="createGuildError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ createGuildError }}</div>
          <div class="flex justify-end gap-3">
            <button type="button" class="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors" @click="showCreateGuild = false">Cancel</button>
            <button type="submit" :disabled="creatingGuild" class="px-4 py-2 text-sm bg-accent-gold/20 text-accent-gold border border-accent-gold/50 rounded hover:bg-accent-gold/30 transition-colors disabled:opacity-50">
              {{ creatingGuild ? 'Creating…' : 'Create Guild' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, h, ref, reactive } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'
import { useUiStore } from '@/stores/ui'
import { useWowIcons } from '@/composables/useWowIcons'
import { WARMANE_REALMS } from '@/constants'
import * as guildsApi from '@/api/guilds'

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
  ]),
  profile: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z' })
  ]),
  admin: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z' })
  ])
}

const navGroups = computed(() => {
  const groups = [
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
    },
    {
      label: 'Account',
      items: [
        { label: 'Profile', to: '/profile', icon: icons.profile }
      ]
    }
  ]
  if (authStore.user?.is_admin) {
    groups.push({
      label: 'Administration',
      items: [
        { label: 'Admin Panel', to: '/admin', icon: icons.admin }
      ]
    })
  }
  return groups
})

function onGuildChange(e) {
  const id = e.target.value
  const guild = guildStore.guilds.find(g => String(g.id) === String(id))
  if (guild) guildStore.setCurrentGuild(guild)
}

// Create Guild
const showCreateGuild = ref(false)
const creatingGuild = ref(false)
const createGuildError = ref(null)
const newGuild = reactive({ name: '', realm_name: '', faction: '' })

async function doCreateGuild() {
  createGuildError.value = null
  creatingGuild.value = true
  try {
    const guild = await guildsApi.createGuild({
      name: newGuild.name,
      realm_name: newGuild.realm_name,
      faction: newGuild.faction || null,
    })
    await guildStore.fetchGuilds()
    guildStore.setCurrentGuild(guild)
    showCreateGuild.value = false
    newGuild.name = ''
    newGuild.realm_name = ''
    newGuild.faction = ''
    uiStore.showToast('Guild created!', 'success')
  } catch (err) {
    createGuildError.value = err?.response?.data?.message ?? 'Failed to create guild'
  } finally {
    creatingGuild.value = false
  }
}
</script>
