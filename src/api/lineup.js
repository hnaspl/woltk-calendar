import api from './index'

export const getLineup = (guildId, eventId) =>
  api.get(`/guilds/${guildId}/events/${eventId}/lineup`)

export const saveLineup = (guildId, eventId, payload) =>
  api.put(`/guilds/${guildId}/events/${eventId}/lineup`, payload)

export const addLineupSlot = (guildId, eventId, payload) =>
  api.post(`/guilds/${guildId}/events/${eventId}/lineup`, payload)

export const removeLineupSlot = (guildId, eventId, slotId) =>
  api.delete(`/guilds/${guildId}/events/${eventId}/lineup/${slotId}`)

export const confirmLineup = (guildId, eventId) =>
  api.post(`/guilds/${guildId}/events/${eventId}/lineup/confirm`)

export const reorderBench = (guildId, eventId, orderedSignupIds) =>
  api.put(`/guilds/${guildId}/events/${eventId}/lineup/bench-reorder`, {
    ordered_signup_ids: orderedSignupIds,
  })
