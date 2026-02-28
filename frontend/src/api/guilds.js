import api from './index'

export const getGuilds = () => api.get('/guilds')

export const getGuild = (id) => api.get(`/guilds/${id}`)

export const createGuild = (payload) => api.post('/guilds', payload)

export const updateGuild = (id, payload) => api.put(`/guilds/${id}`, payload)

export const getGuildMembers = (guildId) => api.get(`/guilds/${guildId}/members`)

export const updateMemberRole = (guildId, memberId, role) =>
  api.put(`/guilds/${guildId}/members/${memberId}`, { role })

export const removeMember = (guildId, memberId) =>
  api.delete(`/guilds/${guildId}/members/${memberId}`)

export const inviteMember = (guildId, payload) =>
  api.post(`/guilds/${guildId}/invites`, payload)
