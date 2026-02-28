import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'

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

  function can(permission) {
    switch (permission) {
      case 'manage_guild':       return isAdmin.value
      case 'manage_events':      return isOfficer.value
      case 'manage_lineup':      return isOfficer.value
      case 'manage_members':     return isOfficer.value
      case 'view_attendance':    return isMember.value
      case 'record_attendance':  return isOfficer.value
      case 'sign_up':            return isMember.value
      default:                   return false
    }
  }

  return { membership, role, isSiteAdmin, isGuildAdmin, isAdmin, isOfficer, isMember, can }
}
