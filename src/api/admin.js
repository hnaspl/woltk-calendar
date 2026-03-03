import api from './index'

export const getUsers = () => api.get('/admin/users')

export const updateUser = (userId, data) => api.put(`/admin/users/${userId}`, data)

export const deleteUser = (userId) => api.delete(`/admin/users/${userId}`)

export const triggerSync = () => api.post('/admin/sync-characters')

export const getSystemSettings = () => api.get('/admin/settings/system')

export const updateSystemSettings = (data) => api.put('/admin/settings/system', data)

export const getDiscordSettings = () => api.get('/admin/settings/discord')

export const updateDiscordSettings = (data) => api.put('/admin/settings/discord', data)

export const getDashboard = () => api.get('/admin/dashboard')
