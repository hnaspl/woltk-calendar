import api from './index'

export const getUsers = () => api.get('/admin/users')

export const updateUser = (userId, data) => api.put(`/admin/users/${userId}`, data)

export const deleteUser = (userId) => api.delete(`/admin/users/${userId}`)
