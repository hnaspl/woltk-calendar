import api from './index'

export const getTemplates = (guildId) => api.get(`/guilds/${guildId}/templates`)

export const getTemplate = (guildId, tplId) =>
  api.get(`/guilds/${guildId}/templates/${tplId}`)

export const createTemplate = (guildId, payload) =>
  api.post(`/guilds/${guildId}/templates`, payload)

export const updateTemplate = (guildId, tplId, payload) =>
  api.put(`/guilds/${guildId}/templates/${tplId}`, payload)

export const deleteTemplate = (guildId, tplId) =>
  api.delete(`/guilds/${guildId}/templates/${tplId}`)

export const applyTemplate = (guildId, tplId, payload) =>
  api.post(`/guilds/${guildId}/templates/${tplId}/apply`, payload)
