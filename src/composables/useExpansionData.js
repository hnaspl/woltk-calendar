/**
 * Composable providing expansion-aware class/spec/raid data
 * with graceful fallback to hardcoded constants (§8.3).
 */
import { computed } from 'vue'
import { useExpansionStore } from '@/stores/expansion'
import { WOW_CLASSES, CLASS_SPECS, RAID_TYPES, CLASS_ROLES, ROLE_OPTIONS } from '@/constants'

export function useExpansionData() {
  const store = useExpansionStore()

  // Classes: from expansion store if loaded, otherwise hardcoded
  const wowClasses = computed(() => {
    if (store.classes.length) {
      return store.classes.map(c => c.name)
    }
    return WOW_CLASSES
  })

  // Specs: from expansion store if loaded, otherwise hardcoded
  const classSpecs = computed(() => {
    if (store.classes.length) {
      const map = {}
      for (const cls of store.classes) {
        map[cls.name] = (cls.specs || []).map(s => s.name)
      }
      return map
    }
    return CLASS_SPECS
  })

  // Class roles: derived from expansion specs if loaded
  // Group spec roles by class -> unique role list
  const classRoles = computed(() => {
    if (store.classes.length) {
      const map = {}
      for (const cls of store.classes) {
        const roles = new Set()
        for (const spec of (cls.specs || [])) {
          // Map spec.role to the full role names used in CLASS_ROLES
          // spec.role values: "tank", "healer", "melee_dps", "range_dps"
          if (spec.role === 'tank') {
            roles.add('main_tank')
            roles.add('off_tank')
          } else {
            roles.add(spec.role)
          }
        }
        map[cls.name] = [...roles]
      }
      return map
    }
    return CLASS_ROLES
  })

  // Raid types: from expansion raids if loaded
  const raidTypes = computed(() => {
    if (store.raids.length) {
      return store.raids.map(r => ({ value: r.code, label: r.name }))
    }
    return RAID_TYPES
  })

  // Roles: from expansion roles if loaded
  const roleOptions = computed(() => {
    if (store.roles.length) {
      return store.roles.map(r => ({ value: r.name, label: r.display_name }))
    }
    return ROLE_OPTIONS
  })

  return {
    wowClasses,
    classSpecs,
    classRoles,
    raidTypes,
    roleOptions,
    expansionStore: store,
  }
}
