/**
 * Armory lookup API module — generic character/guild lookup through the
 * armory provider system.  Works with any server's armory URL.
 */
import api from './index'

export const lookupCharacter = (realm, name) =>
  api.get(`/armory-lookup/character/${encodeURIComponent(realm)}/${encodeURIComponent(name)}`)

export const lookupGuild = (realm, guildName) =>
  api.get(`/armory-lookup/guild/${encodeURIComponent(realm)}/${encodeURIComponent(guildName)}`)

export const syncCharacter = (characterId) =>
  api.post('/armory-lookup/sync-character', { character_id: characterId })

export const discoverRealms = (armoryUrl) =>
  api.post('/armory-lookup/discover-realms', { armory_url: armoryUrl })
