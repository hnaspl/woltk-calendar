import api from './index'

export const getUsers = () => api.get('/admin/users')

export const updateUser = (userId, data) => api.put(`/admin/users/${userId}`, data)

export const deleteUser = (userId) => api.delete(`/admin/users/${userId}`)

export const triggerSync = () => api.post('/admin/sync-characters')

export const getSystemSettings = () => api.get('/admin/settings/system')

export const updateSystemSettings = (data) => api.put('/admin/settings/system', data)

export const testSmtp = () => api.post('/admin/settings/smtp-test')

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

// ── Tenant feature management ──
export const getTenantFeatures = (tenantId) => api.get(`/admin/tenants/${tenantId}/features`)
export const updateTenantFeatures = (tenantId, features) => api.put(`/admin/tenants/${tenantId}/features`, features)

// ── Translation management ──
export const getTranslationStats = () => api.get('/admin/translations/')
export const getTranslations = (locale, section) => {
  const params = section ? `?section=${encodeURIComponent(section)}` : ''
  return api.get(`/admin/translations/${locale}${params}`)
}
export const getTranslationSections = (locale) => api.get(`/admin/translations/${locale}/sections`)
export const getMissingTranslations = () => api.get('/admin/translations/missing')
export const getTranslationOverrides = (locale) => {
  const params = locale ? `?locale=${encodeURIComponent(locale)}` : ''
  return api.get(`/admin/translations/overrides${params}`)
}
export const updateTranslation = (locale, key, value) =>
  api.put(`/admin/translations/${locale}`, { key, value })
export const updateTranslationsBulk = (locale, translations) =>
  api.put(`/admin/translations/${locale}/bulk`, { translations })
export const deleteTranslationOverride = (locale, key) =>
  api.delete(`/admin/translations/${locale}/${key}`)
