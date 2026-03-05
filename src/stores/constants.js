/**
 * Pinia store for shared application constants.
 *
 * Acts as the frontend's single source of truth for data that lives
 * in the backend (`app/constants.py`, `app/enums.py`).  On app init
 * the store fetches from `GET /api/v2/meta/constants` and replaces
 * the static defaults with the authoritative backend values.
 *
 * Realm data is dynamic — provided by armory providers via the plugin
 * system.  There are no hardcoded realm lists.  Use
 * `providerRealms` (keyed by provider name) for realm suggestions, or
 * guild-scoped realm APIs for per-guild realm management.
 *
 * Components can use this store reactively:
 *   const cs = useConstantsStore()
 *   cs.providerRealms   // { armory: ["Realm1", ...] }
 *
 * Static imports from `@/constants` remain available for places that
 * need constants at import/module-evaluation time (e.g. route guards).
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as metaApi from '@/api/meta'

// Static defaults (identical to src/constants.js).
// These are used until the API fetch resolves.
import {
  ROLE_OPTIONS as _ROLES,
  EVENT_STATUSES as _STATUSES,
  ATTENDANCE_OUTCOMES as _OUTCOMES,
} from '@/constants'

export const useConstantsStore = defineStore('constants', () => {
  // ---------------------------------------------------------------------------
  // State – initialised with static defaults
  // ---------------------------------------------------------------------------
  const wowClasses = ref([])
  const raidTypes = ref([])
  const roles = ref([..._ROLES])
  const eventStatuses = ref([..._STATUSES])
  const attendanceOutcomes = ref([..._OUTCOMES])
  const classSpecs = ref({})
  const classRoles = ref({})
  const roleSlots = ref({})
  const expansions = ref([])

  // Provider-based realm suggestions (dynamic, not hardcoded).
  // Keyed by provider name, e.g. { armory: ["Realm1", ...] }
  const providerRealms = ref({})

  const loaded = ref(false)
  const loading = ref(false)
  const error = ref(null)

  // ---------------------------------------------------------------------------
  // Derived
  // ---------------------------------------------------------------------------
  const roleLabelMap = computed(() =>
    Object.fromEntries(roles.value.map(r => [r.value, r.label]))
  )

  /** Flat list of all realm suggestions across all providers. */
  const allRealms = computed(() => {
    const all = []
    for (const realms of Object.values(providerRealms.value)) {
      for (const r of realms) {
        if (!all.includes(r)) all.push(r)
      }
    }
    return all
  })

  /** Expansion slug → display name map, derived from API data. */
  const expansionLabelMap = computed(() =>
    Object.fromEntries(expansions.value.map(e => [e.slug, e.name]))
  )

  /** Expansion slugs ordered by sort_order descending (latest first). */
  const expansionSlugsDesc = computed(() =>
    [...expansions.value].sort((a, b) => b.sort_order - a.sort_order).map(e => e.slug)
  )

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------
  async function fetchConstants() {
    if (loaded.value || loading.value) return
    loading.value = true
    error.value = null
    try {
      const data = await metaApi.getConstants()
      wowClasses.value = data.wow_classes
      raidTypes.value = data.raid_types.map(r => ({ value: r.code, label: r.name }))
      roles.value = data.roles
      eventStatuses.value = data.event_statuses
      attendanceOutcomes.value = data.attendance_outcomes
      classSpecs.value = data.class_specs
      classRoles.value = data.class_roles
      roleSlots.value = data.role_slots
      if (data.provider_realms) {
        providerRealms.value = data.provider_realms
      }
      if (data.expansions) {
        expansions.value = data.expansions
      }
      loaded.value = true
    } catch (err) {
      error.value = err?.response?.data?.message || 'Failed to load constants'
    } finally {
      loading.value = false
    }
  }

  return {
    // state
    wowClasses,
    raidTypes,
    roles,
    eventStatuses,
    attendanceOutcomes,
    classSpecs,
    classRoles,
    roleSlots,
    providerRealms,
    expansions,
    loaded,
    loading,
    error,
    // derived
    roleLabelMap,
    allRealms,
    expansionLabelMap,
    expansionSlugsDesc,
    // actions
    fetchConstants,
  }
})
