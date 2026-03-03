import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import * as eventsApi from '@/api/events'
import { useGuildStore } from '@/stores/guild'

export const useCalendarStore = defineStore('calendar', () => {
  const events = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Watch for tenant switches — clear calendar data
  try {
    const { useTenantStore } = require('@/stores/tenant')
    const tenantStore = useTenantStore()
    watch(() => tenantStore.activeTenantId, (newId, oldId) => {
      if (newId !== oldId && oldId !== null) {
        events.value = []
      }
    })
  } catch {
    // Tenant store not yet initialized — skip watcher
  }

  const filters = ref({
    raidType: '',
    size: '',
    status: '',
    showAllGuilds: false
  })

  const filteredEvents = computed(() => {
    const guildStore = useGuildStore()
    return events.value.filter(ev => {
      if (!filters.value.showAllGuilds && guildStore.currentGuild) {
        if (ev.guild_id !== guildStore.currentGuild.id) return false
      }
      if (filters.value.raidType && ev.raid_type !== filters.value.raidType) return false
      if (filters.value.size && String(ev.raid_size ?? ev.size) !== String(filters.value.size)) return false
      if (filters.value.status && ev.status !== filters.value.status) return false
      return true
    })
  })

  async function fetchEvents(guildId, params = {}) {
    loading.value = true
    error.value = null
    try {
      const data = await eventsApi.getAllEvents({ include_signup_count: true, ...params })
      events.value = data
    } catch (err) {
      error.value = err?.response?.data?.message || 'Failed to load events'
    } finally {
      loading.value = false
    }
  }

  function setFilter(key, value) {
    if (key in filters.value) {
      filters.value[key] = value
    }
  }

  function clearFilters() {
    filters.value = { raidType: '', size: '', status: '', showAllGuilds: false }
  }

  return { events, filteredEvents, filters, loading, error, fetchEvents, setFilter, clearFilters }
})
