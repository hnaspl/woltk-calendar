import api from './index'

export const getMe = () => api.get('/auth/me')

export const login = (credentials) => api.post('/auth/login', credentials)

export const register = (payload) => api.post('/auth/register', payload)

export const logout = () => api.post('/auth/logout')

export const changePassword = (payload) => api.post('/auth/change-password', payload)

export const updateProfile = (payload) => api.put('/auth/profile', payload)

export const getDiscordEnabled = () => api.get('/auth/discord/enabled')

export const activateAccount = (token) => api.post('/auth/activate', { token })

export const forgotPassword = (email) => api.post('/auth/forgot-password', { email })

export const resetPassword = (payload) => api.post('/auth/reset-password', payload)

export const getPasswordPolicy = () => api.get('/auth/password-policy')
