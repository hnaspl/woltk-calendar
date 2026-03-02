import api from './index'

export const getNotifications = (params = {}) =>
  api.get('/notifications', { params })

export const markRead = (notifId) =>
  api.put(`/notifications/${notifId}/read`)

export const markAllRead = () =>
  api.post('/notifications/read-all')

export const deleteNotification = (notifId) =>
  api.delete(`/notifications/${notifId}`)

export const deleteAllNotifications = () =>
  api.delete('/notifications')

export const getUnreadCount = () =>
  api.get('/notifications/unread-count')
