import api from './index'

export const listPlugins = () =>
  api.get('/plugins/')

export const getPlugin = (key) =>
  api.get(`/plugins/${encodeURIComponent(key)}`)

export const getPluginConfig = (key) =>
  api.get(`/plugins/${encodeURIComponent(key)}/config`)
