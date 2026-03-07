/**
 * Guild Realms API module — communicates with /guilds/:guildId/realms endpoints.
 */
import api from '@/api'

export const getGuildRealms = (guildId) =>
  api.get(`/guilds/${guildId}/realms`)

export const addGuildRealm = (guildId, data) =>
  api.post(`/guilds/${guildId}/realms`, data)

export const updateGuildRealm = (guildId, realmId, data) =>
  api.put(`/guilds/${guildId}/realms/${realmId}`, data)

export const removeGuildRealm = (guildId, realmId) =>
  api.delete(`/guilds/${guildId}/realms/${realmId}`)
