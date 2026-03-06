<template>
  <div v-if="tenantStore.tenants.length > 0" class="px-4 py-3 border-b border-[#2a3450]">
    <label class="text-xs text-text-muted uppercase tracking-wider mb-1 block">{{ t('tenant.workspace') }}</label>
    <select
      :value="tenantStore.activeTenantId ?? ''"
      class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-2 py-1.5 focus:border-border-gold outline-none"
      @change="onTenantChange"
    >
      <option
        v-for="t in tenantStore.tenants"
        :key="t.id"
        :value="t.id"
      >{{ t.name }}</option>
    </select>
    <div v-if="isOwnerOrAdmin" class="mt-2 flex items-center gap-2">
      <RouterLink
        to="/tenant/settings"
        class="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 text-xs font-medium text-text-muted bg-bg-tertiary border border-border-default rounded hover:border-border-gold hover:text-accent-gold transition-colors"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        {{ t('tenant.settings') }}
      </RouterLink>
      <RouterLink
        to="/tenant/invites"
        class="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 text-xs font-medium text-text-muted bg-bg-tertiary border border-border-default rounded hover:border-border-gold hover:text-accent-gold transition-colors"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        </svg>
        {{ t('tenant.invites') }}
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useTenantStore } from '@/stores/tenant'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'

const { t } = useI18n()
const tenantStore = useTenantStore()
const authStore = useAuthStore()
const guildStore = useGuildStore()

const isOwnerOrAdmin = computed(() => {
  const activeTenant = tenantStore.activeTenant
  if (!activeTenant || !authStore.user) return false
  return activeTenant.owner_id === authStore.user.id || authStore.user.is_admin
})

async function onTenantChange(e) {
  const id = Number(e.target.value)
  if (!id) return
  try {
    await tenantStore.switchTenant(id)
    // Reload guilds for the new tenant context
    await guildStore.fetchGuilds()
  } catch {
    // error is handled by the store
  }
}
</script>
