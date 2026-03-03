<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="wow-heading text-xl sm:text-2xl">{{ t('admin.globalAdmin.title') }}</h1>
          <p class="text-text-muted text-sm mt-0.5">{{ t('admin.globalAdmin.subtitle') }}</p>
        </div>
        <div class="px-3 py-1.5 rounded-lg bg-bg-tertiary border border-border-default">
          <span class="text-xs text-accent-gold font-medium">{{ t('admin.tabs.globalAdmin') }}</span>
        </div>
      </div>

      <!-- No access message for non-global-admins -->
      <div v-if="!authStore.user?.is_admin" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">
        {{ t('admin.noPermission') }}
      </div>

      <template v-else>
        <!-- Tab navigation -->
        <div class="border-b border-border-default">
          <nav class="flex gap-1 -mb-px overflow-x-auto">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              type="button"
              class="px-3 sm:px-4 py-2 sm:py-2.5 text-sm font-medium whitespace-nowrap transition-colors border-b-2"
              :class="activeTab === tab.id
                ? 'text-accent-gold border-accent-gold'
                : 'text-text-muted border-transparent hover:text-text-primary hover:border-border-default'"
              @click="activeTab = tab.id"
            >
              <span class="flex items-center gap-2">
                <component :is="tab.icon" class="w-4 h-4" />
                {{ tab.label }}
              </span>
            </button>
          </nav>
        </div>

        <!-- Tab content -->
        <KeepAlive>
          <DashboardTab v-if="activeTab === 'dashboard'" />
          <UsersTab v-else-if="activeTab === 'users'" />
          <RolesTab v-else-if="activeTab === 'roles'" />
          <GuildsTab v-else-if="activeTab === 'guilds'" />
          <TenantsTab v-else-if="activeTab === 'tenants'" />
          <DefaultRaidDefinitionsTab v-else-if="activeTab === 'raid-definitions'" />
          <SettingsTab v-else-if="activeTab === 'settings'" />
        </KeepAlive>
      </template>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, h } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import DashboardTab from '@/components/admin/DashboardTab.vue'
import UsersTab from '@/components/admin/UsersTab.vue'
import RolesTab from '@/components/admin/RolesTab.vue'
import GuildsTab from '@/components/admin/GuildsTab.vue'
import TenantsTab from '@/components/admin/TenantsTab.vue'
import DefaultRaidDefinitionsTab from '@/components/admin/DefaultRaidDefinitionsTab.vue'
import SettingsTab from '@/components/admin/SettingsTab.vue'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'

const authStore = useAuthStore()
const { t } = useI18n()

const icons = {
  dashboard: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M4 5a1 1 0 011-1h4a1 1 0 011 1v5a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm10 0a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zm10-2a1 1 0 011-1h4a1 1 0 011 1v6a1 1 0 01-1 1h-4a1 1 0 01-1-1v-6z' })
  ]),
  users: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z' })
  ]),
  roles: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z' })
  ]),
  guilds: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4' })
  ]),
  raidDefs: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M4 6h16M4 10h16M4 14h16M4 18h16' })
  ]),
  tenants: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' })
  ]),
  settings: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' }),
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z' })
  ])
}

const tabs = [
  { id: 'dashboard', label: t('admin.dashboard.title'), icon: icons.dashboard },
  { id: 'users', label: t('admin.users.title', { count: '' }).replace('()', '').trim(), icon: icons.users },
  { id: 'roles', label: t('admin.tabs.roles'), icon: icons.roles },
  { id: 'guilds', label: t('admin.guilds.tabTitle'), icon: icons.guilds },
  { id: 'tenants', label: t('admin.tenants.tabTitle'), icon: icons.tenants },
  { id: 'raid-definitions', label: t('admin.raidDefinitions.tabTitle'), icon: icons.raidDefs },
  { id: 'settings', label: t('admin.system.title'), icon: icons.settings },
]

const activeTab = ref('dashboard')
</script>
