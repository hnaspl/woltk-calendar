<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="wow-heading text-xl sm:text-2xl">{{ t('admin.guildAdmin.title') }}</h1>
          <p class="text-text-muted text-sm mt-0.5">
            {{ guildStore.currentGuild?.name ? `${t('admin.managing')} ${guildStore.currentGuild.name}` : t('admin.guildAdmin.subtitle') }}
          </p>
        </div>
        <div v-if="permissions.role.value" class="px-3 py-1.5 rounded-lg bg-bg-tertiary border border-border-default">
          <span class="text-xs text-text-muted">{{ t('admin.yourRole') }} </span>
          <span class="text-xs text-accent-gold font-medium">{{ currentRoleDisplay }}</span>
        </div>
      </div>

      <!-- Loading state while permissions are being fetched -->
      <div v-if="!permissions.permissionsLoaded.value && !authStore.user?.is_admin" class="p-4 rounded-lg bg-bg-tertiary border border-border-default text-text-muted flex items-center gap-3">
        <div class="w-5 h-5 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin" />
        {{ t('admin.loading') }}
      </div>

      <!-- No permissions message -->
      <div v-else-if="!hasAnyAdminPermission" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">
        {{ t('admin.noPermission') }}
      </div>

      <template v-else>
        <!-- Tab navigation -->
        <div class="border-b border-border-default">
          <nav class="flex gap-1 -mb-px overflow-x-auto">
            <button
              v-for="tab in visibleTabs"
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
          <MembersTab v-if="activeTab === 'members'" />
          <RolesTab v-else-if="activeTab === 'roles'" mode="guild" />
          <GuildSettingsTab v-else-if="activeTab === 'guild'" />
        </KeepAlive>
      </template>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, computed, h, watch, onMounted } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import MembersTab from '@/components/admin/MembersTab.vue'
import RolesTab from '@/components/admin/RolesTab.vue'
import GuildSettingsTab from '@/components/admin/GuildSettingsTab.vue'
import { useGuildStore } from '@/stores/guild'
import { useAuthStore } from '@/stores/auth'
import { usePermissions } from '@/composables/usePermissions'
import api from '@/api'
import { useI18n } from 'vue-i18n'

const guildStore = useGuildStore()
const authStore = useAuthStore()
const permissions = usePermissions()
const { t } = useI18n()

const allRoles = ref([])

// Fetch roles for display name
async function fetchRoles() {
  try {
    allRoles.value = await api.get('/roles')
  } catch {
    allRoles.value = []
  }
}

onMounted(fetchRoles)

const currentRoleDisplay = computed(() => {
  const roleName = permissions.role.value
  if (!roleName) return t('admin.tabs.globalAdmin')
  const roleDef = allRoles.value.find(r => r.name === roleName)
  return roleDef?.display_name ?? roleName
})

// Tab icons
const icons = {
  members: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z' })
  ]),
  roles: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z' })
  ]),
  guild: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' }),
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z' })
  ])
}

// Tab definitions with permission requirements (guild-scoped only)
const allTabs = [
  { id: 'members', label: t('common.labels.members'), icon: icons.members, permission: 'update_member_roles' },
  { id: 'roles', label: t('admin.tabs.roles'), icon: icons.roles, permission: 'manage_roles' },
  { id: 'guild', label: t('admin.tabs.guildSettings'), icon: icons.guild, permission: 'update_guild_settings' },
]

const visibleTabs = computed(() =>
  allTabs.filter(tab => permissions.can(tab.permission))
)

const hasAnyAdminPermission = computed(() => visibleTabs.value.length > 0)

const activeTab = ref('')

// Set default active tab to first visible tab
watch(visibleTabs, (tabs) => {
  if (tabs.length > 0 && !tabs.find(t => t.id === activeTab.value)) {
    activeTab.value = tabs[0].id
  }
}, { immediate: true })
</script>
