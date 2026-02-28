import api from './index'

export const getCharacters = (guildId) => api.get(`/guilds/${guildId}/characters`)

export const getMyCharacters = (guildId) => api.get(`/guilds/${guildId}/characters/me`)

export const createCharacter = (guildId, payload) =>
  api.post(`/guilds/${guildId}/characters`, payload)

export const updateCharacter = (guildId, charId, payload) =>
  api.put(`/guilds/${guildId}/characters/${charId}`, payload)

export const archiveCharacter = (guildId, charId) =>
  api.delete(`/guilds/${guildId}/characters/${charId}`)

export const setMainCharacter = (guildId, charId) =>
  api.post(`/guilds/${guildId}/characters/${charId}/set-main`)
