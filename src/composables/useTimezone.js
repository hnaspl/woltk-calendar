import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'

/**
 * Timezone formatting composable.
 * Provides helpers to format UTC dates in guild and user timezones.
 */
export function useTimezone() {
  const authStore = useAuthStore()
  const guildStore = useGuildStore()

  const guildTimezone = computed(() => guildStore.currentGuild?.timezone || 'Europe/Warsaw')
  const userTimezone = computed(() => authStore.user?.timezone || 'Europe/Warsaw')

  /**
   * Format a UTC ISO string into a localized date/time string in the given timezone.
   */
  function formatInTz(isoString, tz, options = {}) {
    if (!isoString) return '—'
    try {
      const date = new Date(isoString)
      if (isNaN(date.getTime())) return '—'
      const defaults = {
        year: 'numeric', month: 'short', day: '2-digit',
        hour: '2-digit', minute: '2-digit', hour12: false,
        timeZone: tz,
      }
      return date.toLocaleString('en-GB', { ...defaults, ...options })
    } catch {
      return isoString
    }
  }

  /**
   * Format a UTC ISO string showing guild timezone time.
   */
  function formatGuildTime(isoString, options = {}) {
    return formatInTz(isoString, guildTimezone.value, options)
  }

  /**
   * Format a UTC ISO string showing user timezone time.
   */
  function formatUserTime(isoString, options = {}) {
    return formatInTz(isoString, userTimezone.value, options)
  }

  /**
   * Format showing both guild time and user time (if different).
   * Returns "guild_time (your time: user_time)" or just "guild_time" if same.
   */
  function formatDualTime(isoString, options = {}) {
    const gTime = formatGuildTime(isoString, options)
    if (guildTimezone.value === userTimezone.value) return gTime
    const uTime = formatUserTime(isoString, options)
    if (gTime === uTime) return gTime
    return `${gTime} (your time: ${uTime})`
  }

  /**
   * Get timezone abbreviation for display (e.g., "CET", "EST").
   */
  function tzAbbrev(tz) {
    try {
      const parts = new Intl.DateTimeFormat('en-US', { timeZone: tz, timeZoneName: 'short' }).formatToParts(new Date())
      const tzPart = parts.find(p => p.type === 'timeZoneName')
      return tzPart?.value || tz
    } catch {
      return tz
    }
  }

  const guildTzAbbrev = computed(() => tzAbbrev(guildTimezone.value))
  const userTzAbbrev = computed(() => tzAbbrev(userTimezone.value))

  return {
    guildTimezone,
    userTimezone,
    guildTzAbbrev,
    userTzAbbrev,
    formatInTz,
    formatGuildTime,
    formatUserTime,
    formatDualTime,
    tzAbbrev,
  }
}
