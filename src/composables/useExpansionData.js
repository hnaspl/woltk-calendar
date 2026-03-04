/**
 * Composable providing expansion-aware class/spec/raid data
 * from the expansion store (§8.3).
 */
import { computed } from 'vue'
import { useExpansionStore } from '@/stores/expansion'
import { ROLE_OPTIONS } from '@/constants'

export function useExpansionData() {
  const store = useExpansionStore()

  const wowClasses = computed(() => store.classes.map(c => c.name))

  const classSpecs = computed(() => {
    const map = {}
    for (const cls of store.classes) {
      map[cls.name] = (cls.specs || []).map(s => s.name)
    }
    return map
  })

  const classRoles = computed(() => {
    const map = {}
    for (const cls of store.classes) {
      const roles = new Set()
      for (const spec of (cls.specs || [])) {
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
  })

  const raidTypes = computed(() =>
    store.raids.map(r => ({ value: r.code, label: r.name }))
  )

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
