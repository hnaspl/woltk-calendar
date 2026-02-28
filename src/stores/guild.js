import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as guildsApi from '@/api/guilds'

export const useGuildStore = defineStore('guild', () => {
  const guilds = ref([])
  const allGuilds = ref([])
  const currentGuild = ref(null)
  const members = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchGuilds() {
    loading.value = true
    error.value = null
    try {
      guilds.value = await guildsApi.getGuilds()
      if (!currentGuild.value && guilds.value.length > 0) {
        currentGuild.value = guilds.value[0]
        // Auto-fetch members so permissions are available immediately
        fetchMembers(guilds.value[0].id)
      }
    } catch (err) {
      error.value = err?.response?.data?.message || 'Failed to load guilds'
    } finally {
      loading.value = false
    }
  }

  async function fetchAllGuilds() {
    try {
      allGuilds.value = await guildsApi.getAllGuilds()
    } catch {
      // ignore
    }
  }

  async function fetchGuild(id) {
    loading.value = true
    error.value = null
    try {
      const g = await guildsApi.getGuild(id)
      currentGuild.value = g
      return g
    } catch (err) {
      error.value = err?.response?.data?.message || 'Failed to load guild'
      throw err
    } finally {
      loading.value = false
    }
  }

  function setCurrentGuild(guild) {
    currentGuild.value = guild
    members.value = []
    // Auto-fetch members so permissions are available immediately
    if (guild?.id) {
      fetchMembers(guild.id)
    }
  }

  async function fetchMembers(guildId) {
    loading.value = true
    error.value = null
    try {
      members.value = await guildsApi.getGuildMembers(guildId)
    } catch (err) {
      error.value = err?.response?.data?.message || 'Failed to load members'
    } finally {
      loading.value = false
    }
  }

  return { guilds, allGuilds, currentGuild, members, loading, error, fetchGuilds, fetchAllGuilds, fetchGuild, setCurrentGuild, fetchMembers }
})
