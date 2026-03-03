<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-text-primary">{{ t('admin.tenants.title') }}</h2>
      <span class="text-sm text-text-muted">{{ tenants.length }} {{ t('admin.tenants.total') }}</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-8 text-text-muted">{{ t('common.labels.loading') }}</div>

    <!-- Tenants table -->
    <div v-else class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-text-muted border-b border-border-default">
            <th class="px-3 py-2">{{ t('admin.tenants.name') }}</th>
            <th class="px-3 py-2">{{ t('admin.tenants.owner') }}</th>
            <th class="px-3 py-2">{{ t('admin.tenants.plan') }}</th>
            <th class="px-3 py-2">{{ t('admin.tenants.guilds') }}</th>
            <th class="px-3 py-2">{{ t('admin.tenants.members') }}</th>
            <th class="px-3 py-2">{{ t('admin.tenants.status') }}</th>
            <th class="px-3 py-2">{{ t('admin.tenants.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="tenant in tenants"
            :key="tenant.id"
            class="border-b border-border-default hover:bg-bg-tertiary/30 transition-colors"
          >
            <td class="px-3 py-2">
              <div>
                <div class="text-text-primary font-medium">{{ tenant.name }}</div>
                <div class="text-xs text-text-muted">{{ tenant.slug }}</div>
              </div>
            </td>
            <td class="px-3 py-2 text-text-muted">{{ tenant.owner_id }}</td>
            <td class="px-3 py-2">
              <span class="px-2 py-0.5 rounded text-xs font-medium"
                :class="tenant.plan === 'free' ? 'bg-gray-700 text-gray-300' : 'bg-accent-gold/20 text-accent-gold'"
              >{{ tenant.plan }}</span>
            </td>
            <td class="px-3 py-2 text-text-muted">{{ tenant.guild_count ?? 0 }} / {{ tenant.max_guilds }}</td>
            <td class="px-3 py-2 text-text-muted">{{ tenant.member_count ?? 0 }}</td>
            <td class="px-3 py-2">
              <span
                class="px-2 py-0.5 rounded text-xs font-medium"
                :class="tenant.is_active ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'"
              >{{ tenant.is_active ? t('admin.tenants.active') : t('admin.tenants.suspended') }}</span>
            </td>
            <td class="px-3 py-2">
              <div class="flex gap-1.5">
                <button
                  v-if="tenant.is_active"
                  type="button"
                  class="text-xs text-yellow-400 hover:text-yellow-300 transition-colors"
                  @click="doSuspend(tenant)"
                >{{ t('admin.tenants.suspend') }}</button>
                <button
                  v-else
                  type="button"
                  class="text-xs text-green-400 hover:text-green-300 transition-colors"
                  @click="doActivate(tenant)"
                >{{ t('admin.tenants.activate') }}</button>
                <button
                  type="button"
                  class="text-xs text-red-400 hover:text-red-300 transition-colors"
                  @click="doDelete(tenant)"
                >{{ t('common.buttons.delete') }}</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import * as tenantsApi from '@/api/tenants'

const { t } = useI18n()
const tenants = ref([])
const loading = ref(false)

async function fetchTenants() {
  loading.value = true
  try {
    tenants.value = await tenantsApi.adminListTenants()
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function doSuspend(tenant) {
  if (!confirm(t('admin.tenants.confirmSuspend', { name: tenant.name }))) return
  try {
    await tenantsApi.adminSuspendTenant(tenant.id)
    await fetchTenants()
  } catch {
    // ignore
  }
}

async function doActivate(tenant) {
  try {
    await tenantsApi.adminActivateTenant(tenant.id)
    await fetchTenants()
  } catch {
    // ignore
  }
}

async function doDelete(tenant) {
  if (!confirm(t('admin.tenants.confirmDelete', { name: tenant.name }))) return
  try {
    await tenantsApi.adminDeleteTenant(tenant.id)
    await fetchTenants()
  } catch {
    // ignore
  }
}

onMounted(fetchTenants)
</script>
