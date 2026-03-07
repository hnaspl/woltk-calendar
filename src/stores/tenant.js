/**
 * Tenant Pinia store — manages tenant state and switching.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as tenantsApi from '@/api/tenants'

export const useTenantStore = defineStore('tenant', () => {
  const tenants = ref([])
  const activeTenantId = ref(null)
  const loading = ref(false)
  const error = ref(null)

  const activeTenant = computed(() =>
    tenants.value.find(t => t.id === activeTenantId.value) || null
  )

  async function fetchTenants() {
    loading.value = true
    error.value = null
    try {
      tenants.value = await tenantsApi.getTenants()
    } catch (err) {
      error.value = err?.response?.data?.message || 'Failed to load tenants'
      tenants.value = []
    } finally {
      loading.value = false
    }
  }

  async function switchTenant(tenantId) {
    loading.value = true
    error.value = null
    try {
      await tenantsApi.setActiveTenant(tenantId)
      activeTenantId.value = tenantId
    } catch (err) {
      error.value = err?.response?.data?.message || 'Failed to switch tenant'
      throw err
    } finally {
      loading.value = false
    }
  }

  function setActiveTenantFromUser(user) {
    if (user?.active_tenant_id) {
      activeTenantId.value = user.active_tenant_id
    } else if (tenants.value.length > 0) {
      activeTenantId.value = tenants.value[0].id
    }
  }

  function $reset() {
    tenants.value = []
    activeTenantId.value = null
    loading.value = false
    error.value = null
  }

  return {
    tenants,
    activeTenantId,
    activeTenant,
    loading,
    error,
    fetchTenants,
    switchTenant,
    setActiveTenantFromUser,
    $reset,
  }
})
