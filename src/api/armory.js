import api from './index'

export function getProviders() { return api.get('/armory/providers') }
export function getConfigs() { return api.get('/armory/configs') }
export function createConfig(data) { return api.post('/armory/configs', data) }
export function updateConfig(id, data) { return api.put(`/armory/configs/${id}`, data) }
export function deleteConfig(id) { return api.delete(`/armory/configs/${id}`) }
export function setDefaultConfig(id) { return api.put(`/armory/configs/${id}/default`) }
