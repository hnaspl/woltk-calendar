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

  const role = computed(() => membership.value?.role ?? 'member')

  /** True if user is a site-wide admin (is_admin flag on user model) */
  const isSiteAdmin = computed(() => currentUser.value?.is_admin === true)

  /** True if user is a guild admin for the current guild */
  const isGuildAdmin = computed(() => role.value === 'guild_admin')

  /** True if user is a site admin OR guild admin */
  const isAdmin = computed(() => isSiteAdmin.value || isGuildAdmin.value)

  const isOfficer = computed(() =>
    isAdmin.value || role.value === 'officer'
  )

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

  // Auto-fetch when guild changes
  watch(
    () => currentGuild.value?.id,
    () => { fetchPermissions() },
    { immediate: true }
  )

  function can(permission) {
    // Site admin bypasses all checks
    if (isSiteAdmin.value) return true

    // Use dynamic permissions if loaded
    if (permissionsLoaded.value) {
      return dynamicPermissions.value.includes(permission)
    }

    // Fallback to hardcoded logic if dynamic permissions haven't loaded
    switch (permission) {
      case 'manage_guild':
      case 'manage_roles':
      case 'update_guild_settings':
      case 'delete_guild':
        return isAdmin.value
      case 'manage_events':
      case 'create_events':
      case 'edit_events':
      case 'delete_events':
      case 'lock_signups':
      case 'cancel_events':
      case 'duplicate_events':
      case 'manage_lineup':
      case 'update_lineup':
      case 'confirm_lineup':
      case 'reorder_bench':
      case 'manage_members':
      case 'add_members':
      case 'remove_members':
      case 'update_member_roles':
      case 'manage_signups':
      case 'ban_characters':
      case 'unban_characters':
      case 'request_replacement':
      case 'view_member_characters':
      case 'record_attendance':
      case 'manage_raid_definitions':
      case 'manage_templates':
      case 'manage_series':
        return isOfficer.value
      case 'view_attendance':
      case 'view_events':
      case 'view_guild':
      case 'view_notifications':
      case 'sign_up':
      case 'delete_own_signup':
      case 'decline_own_signup':
      case 'manage_own_characters':
        return isMember.value
      default:
        return false
    }
  }

  return {
    membership, role, isSiteAdmin, isGuildAdmin, isAdmin, isOfficer, isMember,
    can, dynamicPermissions, permissionsLoaded, fetchPermissions,
  }
}
