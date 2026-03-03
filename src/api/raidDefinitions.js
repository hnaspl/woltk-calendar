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

export const copyRaidDefinition = (guildId, defId) =>
  api.post(`/guilds/${guildId}/raid-definitions/${defId}/copy`)

// Admin-only default raid definition management
export const adminGetDefaultDefinitions = () =>
  api.get('/admin/raid-definitions')

export const adminCreateDefaultDefinition = (payload) =>
  api.post('/admin/raid-definitions', payload)

export const adminUpdateDefaultDefinition = (defId, payload) =>
  api.put(`/admin/raid-definitions/${defId}`, payload)

export const adminDeleteDefaultDefinition = (defId) =>
  api.delete(`/admin/raid-definitions/${defId}`)
