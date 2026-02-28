import api from './index'

export const getCharacters = (guildId) => api.get('/characters', { params: { guild_id: guildId } })

export const getMyCharacters = (guildId) => api.get('/characters', { params: { guild_id: guildId } })

export const createCharacter = (guildId, payload) =>
  api.post('/characters', { ...payload, guild_id: guildId })

export const updateCharacter = (guildId, charId, payload) =>
  api.put(`/characters/${charId}`, payload)

export const archiveCharacter = (guildId, charId) =>
  api.post(`/characters/${charId}/archive`)

export const deleteCharacter = (guildId, charId) =>
  api.delete(`/characters/${charId}`)

export const setMainCharacter = (guildId, charId) =>
  api.put(`/characters/${charId}`, { is_main: true })
