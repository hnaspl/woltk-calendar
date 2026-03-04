/**
 * Guild Expansions API module — communicates with /v2/guilds/:guildId/expansions endpoints.
 */
import api from '@/api'

const v2 = '/v2'

export const getGuildExpansions = (guildId) =>
  api.get(`${v2}/guilds/${guildId}/expansions`)

export const enableExpansion = (guildId, expansionId) =>
  api.post(`${v2}/guilds/${guildId}/expansions`, { expansion_id: expansionId })

export const disableExpansion = (guildId, expansionId) =>
  api.delete(`${v2}/guilds/${guildId}/expansions/${expansionId}`)

export const getGuildConstants = (guildId) =>
  api.get(`${v2}/guilds/${guildId}/constants`)
