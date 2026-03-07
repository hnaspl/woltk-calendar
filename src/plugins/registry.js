/**
 * Frontend plugin registry.
 *
 * Tracks available plugins fetched from the backend and provides
 * reactive access for components that need to render plugin-specific UI.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as pluginsApi from '@/api/plugins'

export const usePluginStore = defineStore('plugins', () => {
  const plugins = ref([])
  const loaded = ref(false)
  const loading = ref(false)

  const pluginMap = computed(() =>
    Object.fromEntries(plugins.value.map(p => [p.key, p]))
  )

  const pluginKeys = computed(() => plugins.value.map(p => p.key))

  function isRegistered(key) {
    return !!pluginMap.value[key]
  }

  async function fetchPlugins() {
    if (loaded.value || loading.value) return
    loading.value = true
    try {
      const data = await pluginsApi.listPlugins()
      plugins.value = data
      loaded.value = true
    } catch {
      // Silently degrade — plugins are optional
    } finally {
      loading.value = false
    }
  }

  return {
    plugins,
    pluginMap,
    pluginKeys,
    loaded,
    loading,
    isRegistered,
    fetchPlugins,
  }
})
