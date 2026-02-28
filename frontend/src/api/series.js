import api from './index'

export const getSeries = (guildId) => api.get(`/guilds/${guildId}/series`)

export const createSeries = (guildId, payload) =>
  api.post(`/guilds/${guildId}/series`, payload)

export const updateSeries = (guildId, seriesId, payload) =>
  api.put(`/guilds/${guildId}/series/${seriesId}`, payload)

export const deleteSeries = (guildId, seriesId) =>
  api.delete(`/guilds/${guildId}/series/${seriesId}`)
