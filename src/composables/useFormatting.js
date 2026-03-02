import { useTimezone } from '@/composables/useTimezone'

/**
 * Shared date/time formatting composable.
 * Wraps useTimezone() to provide common formatting patterns
 * used across multiple components.
 */
export function useFormatting() {
  const tz = useTimezone()

  /**
   * Format a UTC ISO string as a short guild-timezone date.
   * Output example: "02 Mar 2026"
   * Pass extra Intl options to customise (e.g. { weekday: 'short' }).
   */
  function formatDate(dateString, options = {}) {
    if (!dateString) return '—'
    return tz.formatGuildDate(dateString, { day: '2-digit', month: 'short', year: 'numeric', ...options })
  }

  /**
   * Format a UTC ISO string as a full date+time in guild timezone,
   * with dual-time display (shows user's local time when different).
   * Standard long format: "Mon, 02 Mar 2026, 19:00"
   */
  function formatDateTime(dateString) {
    if (!dateString) return '?'
    return tz.formatDualTime(dateString, {
      weekday: 'short', day: '2-digit', month: 'short',
      year: 'numeric', hour: '2-digit', minute: '2-digit'
    })
  }

  /**
   * Format a UTC ISO string as time-only in guild timezone (24h).
   * Output example: "19:00"
   */
  function formatTimeOnly(dateString) {
    if (!dateString) return '?'
    return tz.formatGuildTime(dateString, {
      hour: '2-digit', minute: '2-digit', hour12: false
    })
  }

  return {
    formatDate,
    formatDateTime,
    formatTimeOnly,
  }
}
