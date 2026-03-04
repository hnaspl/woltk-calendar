import api from './index'

export const listPlugins = () =>
  api.get('/v2/plugins/').then(r => r.data)

export const getPlugin = (key) =>
  api.get(`/v2/plugins/${encodeURIComponent(key)}`).then(r => r.data)

export const getPluginConfig = (key) =>
  api.get(`/v2/plugins/${encodeURIComponent(key)}/config`).then(r => r.data)
