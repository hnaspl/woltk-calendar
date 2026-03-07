import api from './index'

export const getTenantLogs = (tenantId, params = {}) =>
  api.get(`/audit-logs/tenant/${tenantId}`, { params })

export const getGuildLogs = (guildId, params = {}) =>
  api.get(`/audit-logs/guild/${guildId}`, { params })
