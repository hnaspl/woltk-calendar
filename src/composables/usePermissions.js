import { computed, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'
import api from '@/api'

export function usePermissions() {
  const authStore = useAuthStore()
  const guildStore = useGuildStore()

  const currentUser = computed(() => authStore.user)
  const currentGuild = computed(() => guildStore.currentGuild)

  /** The current user's membership record in the current guild */
  const membership = computed(() => {
    if (!currentUser.value || !currentGuild.value) return null
    const members = guildStore.members
    return members.find(m => m.user_id === currentUser.value.id) ?? null
  })

  const role = computed(() => membership.value?.role ?? null)

  const isMember = computed(() => !!membership.value)

  /** Dynamic permissions fetched from the backend */
  const dynamicPermissions = ref([])
  const permissionsLoaded = ref(false)

  /** Fetch dynamic permissions for the current guild */
  async function fetchPermissions() {
    if (!currentGuild.value) {
      dynamicPermissions.value = []
      permissionsLoaded.value = false
      return
    }
    try {
      const data = await api.get(`/roles/my-permissions/${currentGuild.value.id}`)
      dynamicPermissions.value = data.permissions || []
      permissionsLoaded.value = true
    } catch {
      dynamicPermissions.value = []
      permissionsLoaded.value = false
    }
  }

  // Auto-fetch when guild changes (only when user is authenticated)
  watch(
    () => [currentGuild.value?.id, currentUser.value?.id],
    () => {
      if (currentGuild.value && currentUser.value) {
        fetchPermissions()
      }
    },
    { immediate: true }
  )

  /**
   * Check if current user has a specific permission.
   * Uses dynamically fetched permissions from the backend.
   * Site admins (is_admin flag) bypass all checks.
   */
  function can(permission) {
    if (currentUser.value?.is_admin === true) return true
    return dynamicPermissions.value.includes(permission)
  }

  // ── Tenant-level permission helpers ──
  let _tenantStore = null
  try {
    const { useTenantStore } = require('@/stores/tenant')
    _tenantStore = useTenantStore()
  } catch {
    // Tenant store not yet initialized
  }

  const tenantRole = computed(() => _tenantStore?.activeTenant?.my_role ?? null)
  const isTenantOwner = computed(() => tenantRole.value === 'owner')
  const isTenantAdmin = computed(() => ['owner', 'admin'].includes(tenantRole.value))

  /**
   * Check tenant-level permissions.
   * @param {'create_guild'|'invite_member'|'manage_settings'|'manage_members'} action
   */
  function canTenant(action) {
    if (currentUser.value?.is_admin === true) return true
    switch (action) {
      case 'create_guild': return isTenantAdmin.value && !(_tenantStore?.atGuildLimit)
      case 'invite_member': return isTenantAdmin.value
      case 'manage_settings': return isTenantOwner.value
      case 'manage_members': return isTenantAdmin.value
      default: return false
    }
  }

  return {
    membership, role, isMember,
    can, dynamicPermissions, permissionsLoaded, fetchPermissions,
    tenantRole, isTenantOwner, isTenantAdmin, canTenant,
  }
}
