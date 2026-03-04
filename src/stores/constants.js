/**
 * Pinia store for shared application constants.
 *
 * Acts as the frontend's single source of truth for data that lives
 * in the backend (`app/constants.py`, `app/enums.py`).  On app init
 * the store fetches from `GET /api/v1/meta/constants` and replaces
 * the static defaults with the authoritative backend values.
 *
 * Components can use this store reactively:
 *   const cs = useConstantsStore()
 *   cs.warmaneRealms   // reactive ref
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
  WARMANE_REALMS as _REALMS,
  ROLE_OPTIONS as _ROLES,
  EVENT_STATUSES as _STATUSES,
  ATTENDANCE_OUTCOMES as _OUTCOMES,
} from '@/constants'

export const useConstantsStore = defineStore('constants', () => {
  // ---------------------------------------------------------------------------
  // State – initialised with static defaults
  // ---------------------------------------------------------------------------
  const warmaneRealms = ref([..._REALMS])
  const wowClasses = ref([])
  const raidTypes = ref([])
  const roles = ref([..._ROLES])
  const eventStatuses = ref([..._STATUSES])
  const attendanceOutcomes = ref([..._OUTCOMES])
  const classSpecs = ref({})
  const classRoles = ref({})
  const roleSlots = ref({})

  const loaded = ref(false)
  const loading = ref(false)
  const error = ref(null)

  // ---------------------------------------------------------------------------
  // Derived
  // ---------------------------------------------------------------------------
  const roleLabelMap = computed(() =>
    Object.fromEntries(roles.value.map(r => [r.value, r.label]))
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
      warmaneRealms.value = data.warmane_realms
      wowClasses.value = data.wow_classes
      raidTypes.value = data.raid_types.map(r => ({ value: r.code, label: r.name }))
      roles.value = data.roles
      eventStatuses.value = data.event_statuses
      attendanceOutcomes.value = data.attendance_outcomes
      classSpecs.value = data.class_specs
      classRoles.value = data.class_roles
      roleSlots.value = data.role_slots
      loaded.value = true
    } catch (err) {
      error.value = err?.response?.data?.message || 'Failed to load constants'
    } finally {
      loading.value = false
    }
  }

  return {
    // state
    warmaneRealms,
    wowClasses,
    raidTypes,
    roles,
    eventStatuses,
    attendanceOutcomes,
    classSpecs,
    classRoles,
    roleSlots,
    loaded,
    loading,
    error,
    // derived
    roleLabelMap,
    // actions
    fetchConstants,
  }
})
