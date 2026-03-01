import { ref } from 'vue'
import * as adminApi from '@/api/admin'

const settings = ref({ wowhead_tooltips: 'true' })
const loaded = ref(false)
let fetchPromise = null

export function useSystemSettings() {
  async function fetchSettings() {
    if (loaded.value) return
    if (fetchPromise) return fetchPromise
    fetchPromise = adminApi.getSystemSettings()
      .then(data => {
        settings.value = data
        loaded.value = true
      })
      .catch(() => {
        // defaults are fine
        loaded.value = true
      })
      .finally(() => { fetchPromise = null })
    return fetchPromise
  }

  function wowheadEnabled() {
    return settings.value.wowhead_tooltips !== 'false'
  }

  async function updateSettings(data) {
    const updated = await adminApi.updateSystemSettings(data)
    settings.value = updated
    return updated
  }

  return { settings, loaded, fetchSettings, wowheadEnabled, updateSettings }
}
