import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as eventsApi from '@/api/events'

export const useCalendarStore = defineStore('calendar', () => {
  const events = ref([])
  const loading = ref(false)
  const error = ref(null)

  const filters = ref({
    realm: '',
    raidType: '',
    size: '',
    status: ''
  })

  const filteredEvents = computed(() => {
    return events.value.filter(ev => {
      if (filters.value.realm && (ev.realm_name ?? ev.realm) !== filters.value.realm) return false
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
    filters.value = { realm: '', raidType: '', size: '', status: '' }
  }

  return { events, filteredEvents, filters, loading, error, fetchEvents, setFilter, clearFilters }
})
