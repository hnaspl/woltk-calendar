<template>
  <div class="px-4 py-3 border-b border-[#2a3450]">
    <label class="text-xs text-text-muted uppercase tracking-wider mb-1 block">{{ t('tenant.workspace') }}</label>
    <select
      :value="tenantStore.activeTenantId ?? ''"
      class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-2 py-1.5 focus:border-border-gold outline-none"
      @change="onTenantChange"
    >
      <option v-if="!tenantStore.tenants.length" value="">{{ t('tenant.noWorkspaces') }}</option>
      <option
        v-for="t in tenantStore.tenants"
        :key="t.id"
        :value="t.id"
      >{{ t.name }}</option>
    </select>
    <div class="mt-1.5 flex items-center gap-2">
      <RouterLink
        v-if="isOwnerOrAdmin"
        to="/tenant/settings"
        class="text-[10px] text-text-muted hover:text-accent-gold transition-colors"
      >{{ t('tenant.settings') }}</RouterLink>
      <RouterLink
        v-if="isOwnerOrAdmin"
        to="/tenant/invites"
        class="text-[10px] text-text-muted hover:text-accent-gold transition-colors"
      >{{ t('tenant.invites') }}</RouterLink>
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
