import api from './index'

export const getGuilds = () => api.get('/guilds')

export const getAllGuilds = () => api.get('/guilds/all')

export const getGuild = (id) => api.get(`/guilds/${id}`)

export const createGuild = (payload) => api.post('/guilds', payload)

export const updateGuild = (id, payload) => api.put(`/guilds/${id}`, payload)

export const joinGuild = (guildId) => api.post(`/guilds/${guildId}/join`)

export const getGuildMembers = (guildId) => api.get(`/guilds/${guildId}/members`)

export const getAvailableUsers = (guildId, q = '') =>
  api.get(`/guilds/${guildId}/available-users`, { params: { q } })

export const addMember = (guildId, userId, role = 'member') =>
  api.post(`/guilds/${guildId}/members`, { user_id: userId, role })

export const updateMemberRole = (guildId, userId, role) =>
  api.put(`/guilds/${guildId}/members/${userId}`, { role })

export const removeMember = (guildId, userId) =>
  api.delete(`/guilds/${guildId}/members/${userId}`)

export const getMemberCharacters = (guildId, userId) =>
  api.get(`/guilds/${guildId}/members/${userId}/characters`)

export const getWarmaneRoster = (guildId) =>
  api.get(`/guilds/${guildId}/warmane-roster`)

export const transferOwnership = (guildId, userId) =>
  api.post(`/guilds/${guildId}/transfer-ownership`, { user_id: userId })

// Admin-only endpoints
export const adminGetAllGuilds = () => api.get('/guilds/admin/all')

export const adminGetGuildMembers = (guildId) => api.get(`/guilds/admin/${guildId}/members`)

export const adminUpdateMemberRole = (guildId, userId, role) =>
  api.put(`/guilds/admin/${guildId}/members/${userId}`, { role })

export const adminRemoveMember = (guildId, userId) =>
  api.delete(`/guilds/admin/${guildId}/members/${userId}`)

export const adminTransferOwnership = (guildId, userId) =>
  api.post(`/guilds/admin/${guildId}/transfer-ownership`, { user_id: userId })

export const adminDeleteGuild = (guildId) =>
  api.delete(`/guilds/admin/${guildId}`)

export const adminSendNotification = (guildId, userId, message) =>
  api.post(`/guilds/admin/${guildId}/notify/${userId}`, { message })
