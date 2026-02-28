import api from './index'

export const getMe = () => api.get('/auth/me')

export const login = (credentials) =>
  api.post('/auth/login', credentials).then(data => {
    if (data?.access_token) localStorage.setItem('access_token', data.access_token)
    return data
  })

export const register = (payload) =>
  api.post('/auth/register', payload).then(data => {
    if (data?.access_token) localStorage.setItem('access_token', data.access_token)
    return data
  })

export const logout = () =>
  api.post('/auth/logout').finally(() => {
    localStorage.removeItem('access_token')
  })

export const changePassword = (payload) => api.post('/auth/change-password', payload)
