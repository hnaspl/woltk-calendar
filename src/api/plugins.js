import api from './index'

export const listPlugins = () =>
  api.get('/plugins/').then(r => r.data)

export const getPlugin = (key) =>
  api.get(`/plugins/${encodeURIComponent(key)}`).then(r => r.data)

export const getPluginConfig = (key) =>
  api.get(`/plugins/${encodeURIComponent(key)}/config`).then(r => r.data)
