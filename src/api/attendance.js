import api from './index'

export const getAttendance = (guildId, params = {}) =>
  api.get(`/guilds/${guildId}/attendance`, { params })

export const getCharacterAttendance = (guildId, charId, params = {}) =>
  api.get(`/guilds/${guildId}/attendance/characters/${charId}`, { params })

export const recordAttendance = (guildId, eventId, payload) =>
  api.post(`/guilds/${guildId}/events/${eventId}/attendance`, payload)

export const updateAttendanceRecord = (guildId, eventId, recordId, payload) =>
  api.put(`/guilds/${guildId}/events/${eventId}/attendance/${recordId}`, payload)
