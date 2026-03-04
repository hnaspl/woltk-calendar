/**
 * Guild Expansions API module — communicates with /guilds/:guildId/expansions endpoints.
 */
import api from '@/api'

export const getGuildExpansions = (guildId) =>
  api.get(`/guilds/${guildId}/expansions`)

export const enableExpansion = (guildId, expansionId) =>
  api.post(`/guilds/${guildId}/expansions`, { expansion_id: expansionId })

export const disableExpansion = (guildId, expansionId) =>
  api.delete(`/guilds/${guildId}/expansions/${expansionId}`)

export const getGuildConstants = (guildId) =>
  api.get(`/guilds/${guildId}/constants`)
