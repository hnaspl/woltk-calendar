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
          <SystemTab v-if="activeTab === 'system'" />
          <RolesTab v-else-if="activeTab === 'roles'" />
          <GuildsTab v-else-if="activeTab === 'guilds'" />
        </KeepAlive>
      </template>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, h } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import SystemTab from '@/components/admin/SystemTab.vue'
import RolesTab from '@/components/admin/RolesTab.vue'
import GuildsTab from '@/components/admin/GuildsTab.vue'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'

const authStore = useAuthStore()
const { t } = useI18n()

const icons = {
  system: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01' })
  ]),
  roles: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z' })
  ]),
  guilds: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4' })
  ])
}

const tabs = [
  { id: 'system', label: t('common.labels.system'), icon: icons.system },
  { id: 'roles', label: t('admin.tabs.roles'), icon: icons.roles },
  { id: 'guilds', label: t('admin.guilds.tabTitle'), icon: icons.guilds },
]

const activeTab = ref('system')
</script>
