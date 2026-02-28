import api from './index'

export const getRaidDefinitions = (guildId) =>
  api.get(`/guilds/${guildId}/raid-definitions`)

export const getRaidDefinition = (guildId, defId) =>
  api.get(`/guilds/${guildId}/raid-definitions/${defId}`)

export const createRaidDefinition = (guildId, payload) =>
  api.post(`/guilds/${guildId}/raid-definitions`, payload)

export const updateRaidDefinition = (guildId, defId, payload) =>
  api.put(`/guilds/${guildId}/raid-definitions/${defId}`, payload)

export const deleteRaidDefinition = (guildId, defId) =>
  api.delete(`/guilds/${guildId}/raid-definitions/${defId}`)
