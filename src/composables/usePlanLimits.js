/**
 * Composable for plan limits enforcement and upgrade prompts.
 *
 * Usage:
 *   const { withinLimit, usageInfo, checkBeforeAction } = usePlanLimits()
 *   await checkBeforeAction('guilds')  // throws if limit exceeded
 */
import { ref } from 'vue'
import * as plansApi from '@/api/plans'

export function usePlanLimits() {
  const usage = ref(null)
  const loadingUsage = ref(false)

  /**
   * Fetch usage stats for a tenant.
   * @param {number} tenantId
   */
  async function fetchUsage(tenantId) {
    loadingUsage.value = true
    try {
      usage.value = await plansApi.getTenantUsage(tenantId)
    } catch {
      usage.value = null
    } finally {
      loadingUsage.value = false
    }
  }

  /**
   * Check if a resource is within plan limits.
   * @param {string} resource - 'guilds' | 'members' | 'events'
   * @returns {{ withinLimit: boolean, current: number, max: number|null }}
   */
  function checkLimit(resource) {
    if (!usage.value) return { withinLimit: true, current: 0, max: null }
    const info = usage.value[resource]
    if (!info) return { withinLimit: true, current: 0, max: null }
    return {
      withinLimit: info.max === null || info.current < info.max,
      current: info.current,
      max: info.max
    }
  }

  /**
   * Returns true if the resource usage is within limits.
   * @param {string} resource
   */
  function withinLimit(resource) {
    return checkLimit(resource).withinLimit
  }

  /**
   * Returns formatted usage info string like "2 / 5".
   * @param {string} resource
   */
  function usageInfo(resource) {
    const { current, max } = checkLimit(resource)
    return `${current} / ${max ?? '∞'}`
  }

  /**
   * Returns true if upgrade prompt should be shown for a resource.
   * @param {string} resource
   */
  function shouldShowUpgrade(resource) {
    return !checkLimit(resource).withinLimit
  }

  return {
    usage,
    loadingUsage,
    fetchUsage,
    checkLimit,
    withinLimit,
    usageInfo,
    shouldShowUpgrade
  }
}
