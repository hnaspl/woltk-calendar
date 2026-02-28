import api from './index'

export const getSignups = (guildId, eventId) =>
  api.get(`/guilds/${guildId}/events/${eventId}/signups`)

export const createSignup = (guildId, eventId, payload) =>
  api.post(`/guilds/${guildId}/events/${eventId}/signups`, payload)

export const updateSignup = (guildId, eventId, signupId, payload) =>
  api.put(`/guilds/${guildId}/events/${eventId}/signups/${signupId}`, payload)

export const deleteSignup = (guildId, eventId, signupId) =>
  api.delete(`/guilds/${guildId}/events/${eventId}/signups/${signupId}`)
