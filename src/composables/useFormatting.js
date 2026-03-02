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

  return {
    formatDate,
  }
}
