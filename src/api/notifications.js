import api from './index'

export const getNotifications = (params = {}) =>
  api.get('/notifications', { params })

export const markRead = (notifId) =>
  api.post(`/notifications/${notifId}/read`)

export const markAllRead = () =>
  api.post('/notifications/read-all')

export const deleteNotification = (notifId) =>
  api.delete(`/notifications/${notifId}`)

export const getUnreadCount = () =>
  api.get('/notifications/unread-count')
