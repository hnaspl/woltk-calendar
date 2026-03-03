import api from './index'

export function getProviders() { return api.get('/armory/providers').then(r => r.data) }
export function getConfigs() { return api.get('/armory/configs').then(r => r.data) }
export function createConfig(data) { return api.post('/armory/configs', data).then(r => r.data) }
export function updateConfig(id, data) { return api.put(`/armory/configs/${id}`, data).then(r => r.data) }
export function deleteConfig(id) { return api.delete(`/armory/configs/${id}`).then(r => r.data) }
export function setDefaultConfig(id) { return api.put(`/armory/configs/${id}/default`).then(r => r.data) }
