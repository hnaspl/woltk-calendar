import api from './index'

export const getUsers = () => api.get('/admin/users')

export const updateUser = (userId, data) => api.put(`/admin/users/${userId}`, data)

export const deleteUser = (userId) => api.delete(`/admin/users/${userId}`)

export const triggerSync = () => api.post('/admin/sync-characters')

export const getSystemSettings = () => api.get('/admin/settings/system')

export const updateSystemSettings = (data) => api.put('/admin/settings/system', data)

export const getDiscordSettings = () => api.get('/admin/settings/discord')

export const updateDiscordSettings = (data) => api.put('/admin/settings/discord', data)

export const getDashboard = () => api.get('/admin/dashboard')

export const setUserGuildLimit = (userId, maxGuilds) =>
  api.put(`/admin/users/${userId}/guild-limit`, { max_guilds: maxGuilds })

export const getGuildFeatures = (guildId) =>
  api.get(`/admin/guilds/${guildId}/features`)

export const updateGuildFeatures = (guildId, features) =>
  api.put(`/admin/guilds/${guildId}/features`, features)

// ── Tenant admin endpoints ──
export const getAdminTenants = () => api.get('/admin/tenants')
export const getAdminTenant = (id) => api.get(`/admin/tenants/${id}`)
export const updateAdminTenant = (id, data) => api.put(`/admin/tenants/${id}`, data)
export const suspendTenant = (id) => api.post(`/admin/tenants/${id}/suspend`)
export const activateTenant = (id) => api.post(`/admin/tenants/${id}/activate`)
export const deleteAdminTenant = (id) => api.delete(`/admin/tenants/${id}`)
export const updateTenantLimits = (id, data) => api.put(`/admin/tenants/${id}/limits`, data)
