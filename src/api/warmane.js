import api from './index'

export const lookupCharacter = (realm, name) =>
  api.get(`/warmane/character/${encodeURIComponent(realm)}/${encodeURIComponent(name)}`)

export const lookupGuild = (realm, guildName) =>
  api.get(`/warmane/guild/${encodeURIComponent(realm)}/${encodeURIComponent(guildName)}`)

export const syncCharacter = (characterId) =>
  api.post('/warmane/sync-character', { character_id: characterId })
