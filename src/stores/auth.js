import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as authApi from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Deduplication: reuse the in-flight promise so concurrent callers
  // (router guard + App.vue onMounted) share a single API request.
  let _fetchPromise = null

  /** Helper to bootstrap tenant context after auth. */
  function _bootstrapTenant(userData) {
    try {
      const { useTenantStore } = require('@/stores/tenant')
      const tenantStore = useTenantStore()
      if (userData?.active_tenant_id) {
        tenantStore.activeTenantId = userData.active_tenant_id
      }
      tenantStore.fetchTenants()
    } catch {
      // Tenant store not yet initialized — skip
    }
  }

  /** Helper to clear tenant context on logout. */
  function _resetTenant() {
    try {
      const { useTenantStore } = require('@/stores/tenant')
      const tenantStore = useTenantStore()
      tenantStore.$reset()
    } catch {
      // Tenant store not yet initialized — skip
    }
  }

  async function fetchMe() {
    if (_fetchPromise) return _fetchPromise

    loading.value = true
    error.value = null

    _fetchPromise = authApi.getMe()
      .then(data => {
        user.value = data
        _bootstrapTenant(data)
        return data
      })
      .catch(err => { user.value = null; throw err })
      .finally(() => { loading.value = false; _fetchPromise = null })

    return _fetchPromise
  }

  async function login(email, password, remember = true) {
    loading.value = true
    error.value = null
    try {
      const data = await authApi.login({ email, password, remember })
      user.value = data.user ?? data
      _bootstrapTenant(user.value)
    } catch (err) {
      error.value = err?.response?.data?.message || 'Login failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function register(username, email, password) {
    loading.value = true
    error.value = null
    try {
      const data = await authApi.register({ username, email, password })
      user.value = data.user ?? data
      _bootstrapTenant(user.value)
    } catch (err) {
      error.value = err?.response?.data?.message || 'Registration failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    loading.value = true
    try {
      await authApi.logout()
    } finally {
      user.value = null
      _resetTenant()
      loading.value = false
    }
  }

  return { user, loading, error, fetchMe, login, register, logout }
})
