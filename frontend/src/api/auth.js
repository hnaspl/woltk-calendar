import api from './index'

export const getMe = () => api.get('/auth/me')

export const login = (credentials) => api.post('/auth/login', credentials)

export const register = (payload) => api.post('/auth/register', payload)

export const logout = () => api.post('/auth/logout')

export const changePassword = (payload) => api.post('/auth/change-password', payload)
