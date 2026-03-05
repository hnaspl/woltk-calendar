/**
 * Armory lookup API module — generic character/guild lookup through the
 * armory provider system.  Works with any server's armory URL.
 */
import api from './index'

export const lookupCharacter = (realm, name, guildId = null) => {
  const params = guildId ? { guild_id: guildId } : {}
  return api.get(`/armory-lookup/character/${encodeURIComponent(realm)}/${encodeURIComponent(name)}`, { params })
}

export const lookupGuild = (realm, guildName, guildId = null) => {
  const params = guildId ? { guild_id: guildId } : {}
  return api.get(`/armory-lookup/guild/${encodeURIComponent(realm)}/${encodeURIComponent(guildName)}`, { params })
}

export const syncCharacter = (characterId) =>
  api.post('/armory-lookup/sync-character', { character_id: characterId })

export const discoverRealms = (armoryUrl) =>
  api.post('/armory-lookup/discover-realms', { armory_url: armoryUrl })

export const searchGuild = (armoryUrl, guildName, realmHints = []) =>
  api.post('/armory-lookup/search-guild', { armory_url: armoryUrl, guild_name: guildName, realm_hints: realmHints })
