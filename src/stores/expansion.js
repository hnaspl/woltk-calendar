/**
 * Expansion Pinia store — manages expansion registry state.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as expansionsApi from '@/api/expansions'

export const useExpansionStore = defineStore('expansion', () => {
  const expansions = ref([])
  const classes = ref([])
  const specs = ref([])
  const raids = ref([])
  const roles = ref([])
  const defaultSlug = ref('wotlk')
  const loading = ref(false)
  const error = ref(null)

  const activeExpansion = computed(() =>
    expansions.value.find(e => e.slug === defaultSlug.value) || expansions.value[0] || null
  )

  async function fetchExpansions(silent = false) {
    if (!silent) loading.value = true
    error.value = null
    try {
      expansions.value = await expansionsApi.listExpansions()
    } catch (err) {
      error.value = err?.response?.data?.message || 'Failed to load expansions'
      expansions.value = []
    } finally {
      if (!silent) loading.value = false
    }
  }

  async function fetchClasses(slug, silent = false) {
    if (!silent) loading.value = true
    error.value = null
    try {
      classes.value = await expansionsApi.getClasses(slug)
    } catch (err) {
      error.value = err?.response?.data?.message || 'Failed to load classes'
      classes.value = []
    } finally {
      if (!silent) loading.value = false
    }
  }

  async function fetchSpecs(slug, silent = false) {
    if (!silent) loading.value = true
    error.value = null
    try {
      specs.value = await expansionsApi.getSpecs(slug)
    } catch (err) {
      error.value = err?.response?.data?.message || 'Failed to load specs'
      specs.value = []
    } finally {
      if (!silent) loading.value = false
    }
  }

  async function fetchRaids(slug, silent = false) {
    if (!silent) loading.value = true
    error.value = null
    try {
      raids.value = await expansionsApi.getRaids(slug)
    } catch (err) {
      error.value = err?.response?.data?.message || 'Failed to load raids'
      raids.value = []
    } finally {
      if (!silent) loading.value = false
    }
  }

  async function fetchRoles(slug, silent = false) {
    if (!silent) loading.value = true
    error.value = null
    try {
      roles.value = await expansionsApi.getRoles(slug)
    } catch (err) {
      error.value = err?.response?.data?.message || 'Failed to load roles'
      roles.value = []
    } finally {
      if (!silent) loading.value = false
    }
  }

  async function fetchDefaultExpansion() {
    try {
      const data = await expansionsApi.getDefaultExpansion()
      defaultSlug.value = data?.slug || 'wotlk'
    } catch {
      // Keep existing default
    }
  }

  async function loadAll() {
    loading.value = true
    error.value = null
    try {
      await fetchExpansions(true)
      await fetchDefaultExpansion()
      const slug = activeExpansion.value?.slug
      if (slug) {
        await Promise.all([
          fetchClasses(slug, true),
          fetchSpecs(slug, true),
          fetchRaids(slug, true),
          fetchRoles(slug, true),
        ])
      }
    } catch (err) {
      error.value = err?.response?.data?.message || 'Failed to load expansion data'
    } finally {
      loading.value = false
    }
  }

  function $reset() {
    expansions.value = []
    classes.value = []
    specs.value = []
    raids.value = []
    roles.value = []
    defaultSlug.value = 'wotlk'
    loading.value = false
    error.value = null
  }

  return {
    expansions,
    classes,
    specs,
    raids,
    roles,
    defaultSlug,
    activeExpansion,
    loading,
    error,
    fetchExpansions,
    fetchClasses,
    fetchSpecs,
    fetchRaids,
    fetchRoles,
    fetchDefaultExpansion,
    loadAll,
    $reset,
  }
})
