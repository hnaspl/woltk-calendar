import api from './index'

export const getGuilds = () => api.get('/guilds')

export const getAllGuilds = () => api.get('/guilds/all')

export const getGuild = (id) => api.get(`/guilds/${id}`)

export const createGuild = (payload) => api.post('/guilds', payload)

export const updateGuild = (id, payload) => api.put(`/guilds/${id}`, payload)

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

export const getArmoryRoster = (guildId) =>
  api.get(`/guilds/${guildId}/armory-roster`)

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

// Guild admin — notifications
export const sendGuildNotification = (guildId, userId, message) =>
  api.post(`/guilds/${guildId}/notify/${userId}`, { message })

export const sendGuildNotificationAll = (guildId, message) =>
  api.post(`/guilds/${guildId}/notify-all`, { message })

// Guild admin — ban/unban
export const banGuildMember = (guildId, userId) =>
  api.post(`/guilds/${guildId}/ban/${userId}`)

export const unbanGuildMember = (guildId, userId) =>
  api.post(`/guilds/${guildId}/unban/${userId}`)

// ---------------------------------------------------------------------------
// Guild invitations
// ---------------------------------------------------------------------------

export const getGuildInvitations = (guildId) =>
  api.get(`/guilds/${guildId}/invitations`)

export const createGuildInvitation = (guildId, payload) =>
  api.post(`/guilds/${guildId}/invitations`, payload)

export const revokeGuildInvitation = (guildId, invitationId) =>
  api.delete(`/guilds/${guildId}/invitations/${invitationId}`)

export const acceptGuildInvite = (token) =>
  api.post(`/guild-invite/${token}`)

// ---------------------------------------------------------------------------
// Guild applications
// ---------------------------------------------------------------------------

export const getGuildApplications = (guildId) =>
  api.get(`/guilds/${guildId}/applications`)

export const approveApplication = (guildId, userId) =>
  api.post(`/guilds/${guildId}/applications/${userId}/approve`)

export const declineApplication = (guildId, userId) =>
  api.post(`/guilds/${guildId}/applications/${userId}/decline`)

// ---------------------------------------------------------------------------
// Guild visibility
// ---------------------------------------------------------------------------

export const updateGuildVisibility = (guildId, visibility) =>
  api.put(`/guilds/${guildId}/visibility`, { visibility })

// ---------------------------------------------------------------------------
// Class-role matrix
// ---------------------------------------------------------------------------

export const getClassRoleMatrix = (guildId) =>
  api.get(`/guilds/${guildId}/class-role-matrix`)

export const setClassRoleOverrides = (guildId, className, roles) =>
  api.put(`/guilds/${guildId}/class-role-matrix/${className}`, { roles })

export const resetClassRoleOverrides = (guildId, className) =>
  api.delete(`/guilds/${guildId}/class-role-matrix/${className}`)

export const resetClassRoleMatrix = (guildId) =>
  api.delete(`/guilds/${guildId}/class-role-matrix`)
