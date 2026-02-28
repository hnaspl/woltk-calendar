import api from './index'

export const getEvents = (guildId, params = {}) =>
  api.get(`/guilds/${guildId}/events`, { params })

export const getEvent = (guildId, eventId) =>
  api.get(`/guilds/${guildId}/events/${eventId}`)

export const createEvent = (guildId, payload) =>
  api.post(`/guilds/${guildId}/events`, payload)

export const updateEvent = (guildId, eventId, payload) =>
  api.put(`/guilds/${guildId}/events/${eventId}`, payload)

export const deleteEvent = (guildId, eventId) =>
  api.delete(`/guilds/${guildId}/events/${eventId}`)

export const lockEvent = (guildId, eventId) =>
  api.post(`/guilds/${guildId}/events/${eventId}/lock`)

export const unlockEvent = (guildId, eventId) =>
  api.post(`/guilds/${guildId}/events/${eventId}/unlock`)

export const completeEvent = (guildId, eventId) =>
  api.post(`/guilds/${guildId}/events/${eventId}/complete`)

export const cancelEvent = (guildId, eventId) =>
  api.post(`/guilds/${guildId}/events/${eventId}/cancel`)
