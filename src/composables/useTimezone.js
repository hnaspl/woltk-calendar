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
   * Returns "guild_time" or "guild_time (your time: user_time)" if different.
   */
  function formatDualTime(isoString, options = {}) {
    const gTime = formatGuildTime(isoString, options)
    if (guildTimezone.value === userTimezone.value) return gTime
    const uTime = formatUserTime(isoString, options)
    if (gTime === uTime) return gTime
    return `${gTime} (your time: ${uTime})`
  }

  /**
   * Format a UTC ISO string as date-only in the given timezone (no time component).
   */
  function formatDateInTz(isoString, tz, options = {}) {
    if (!isoString) return '—'
    try {
      const date = new Date(isoString)
      if (isNaN(date.getTime())) return '—'
      const defaults = {
        year: 'numeric', month: 'short', day: '2-digit',
        timeZone: tz,
      }
      return date.toLocaleDateString('en-GB', { ...defaults, ...options })
    } catch {
      return isoString
    }
  }

  /**
   * Format date-only in guild timezone.
   */
  function formatGuildDate(isoString, options = {}) {
    return formatDateInTz(isoString, guildTimezone.value, options)
  }

  /**
   * Format date-only in user timezone.
   */
  function formatUserDate(isoString, options = {}) {
    return formatDateInTz(isoString, userTimezone.value, options)
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

  /**
   * Convert a naive datetime-local string (e.g. "2026-03-15T00:00") interpreted
   * as guild timezone into a UTC ISO string for the backend.
   *
   * The HTML datetime-local input produces values like "2026-03-15T19:30" without
   * any timezone offset.  We treat that value as being in the guild's timezone and
   * compute the correct UTC equivalent so the backend stores the right instant.
   */
  function guildLocalToUtc(localStr) {
    if (!localStr) return localStr
    // Build a Date in the guild timezone by computing the UTC offset for that moment.
    // 1. Parse the naive string as a rough UTC guess
    const naive = new Date(localStr + 'Z')               // treat as UTC temporarily
    // 2. Format that instant in the guild tz to get the wall-clock parts
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: guildTimezone.value,
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
    }).formatToParts(naive)
    const get = (type) => {
      const p = parts.find(p => p.type === type)
      return p ? parseInt(p.value, 10) : 0
    }
    // 3. Reconstruct a UTC Date from those parts (this is what UTC would show if the wall-clock were UTC)
    const guildAsUtc = Date.UTC(get('year'), get('month') - 1, get('day'), get('hour'), get('minute'), get('second'))
    // 4. The offset is the difference between the UTC instant and its guild-local representation
    const offsetMs = guildAsUtc - naive.getTime()
    // 5. Apply the offset to the original naive value to get the true UTC instant
    const utcDate = new Date(naive.getTime() - offsetMs)
    return utcDate.toISOString()
  }

  /**
   * Convert a UTC ISO string to a datetime-local value in the guild timezone,
   * suitable for populating an HTML datetime-local input.
   */
  function utcToGuildLocal(isoString) {
    if (!isoString) return ''
    const date = new Date(isoString)
    if (isNaN(date.getTime())) return ''
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: guildTimezone.value,
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hour12: false,
    }).formatToParts(date)
    const get = (type) => parts.find(p => p.type === type)?.value ?? '00'
    // en-CA formats as YYYY-MM-DD; hour may return "24" at midnight in some locales
    let hour = get('hour')
    if (hour === '24') hour = '00'
    return `${get('year')}-${get('month')}-${get('day')}T${hour}:${get('minute')}`
  }

  const guildTzAbbrev = computed(() => tzAbbrev(guildTimezone.value))
  const userTzAbbrev = computed(() => tzAbbrev(userTimezone.value))

  return {
    guildTimezone,
    userTimezone,
    guildTzAbbrev,
    userTzAbbrev,
    formatInTz,
    formatDateInTz,
    formatGuildTime,
    formatUserTime,
    formatDualTime,
    formatGuildDate,
    formatUserDate,
    tzAbbrev,
    guildLocalToUtc,
    utcToGuildLocal,
  }
}
