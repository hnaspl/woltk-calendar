import api from './index'

export const getUsers = () => api.get('/admin/users')

export const updateUser = (userId, data) => api.put(`/admin/users/${userId}`, data)

export const deleteUser = (userId) => api.delete(`/admin/users/${userId}`)

export const getAutosyncSettings = () => api.get('/admin/settings/autosync')

export const updateAutosyncSettings = (data) => api.put('/admin/settings/autosync', data)

export const triggerSync = () => api.post('/admin/sync-characters')
