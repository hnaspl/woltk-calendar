/**
 * Guild Realms API module — communicates with /v2/guilds/:guildId/realms endpoints.
 */
import api from '@/api'

const v2 = '/v2'

export const getGuildRealms = (guildId) =>
  api.get(`${v2}/guilds/${guildId}/realms`)

export const addGuildRealm = (guildId, data) =>
  api.post(`${v2}/guilds/${guildId}/realms`, data)

export const updateGuildRealm = (guildId, realmId, data) =>
  api.put(`${v2}/guilds/${guildId}/realms/${realmId}`, data)

export const removeGuildRealm = (guildId, realmId) =>
  api.delete(`${v2}/guilds/${guildId}/realms/${realmId}`)
