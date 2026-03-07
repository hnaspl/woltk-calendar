/**
 * Expansions API module — communicates with /meta/expansions endpoints.
 */
import api from '@/api'

// Public endpoints
export const listExpansions = () => api.get('/meta/expansions')
export const getClasses = (slug) => api.get(`/meta/expansions/${slug}/classes`)
export const getSpecs = (slug) => api.get(`/meta/expansions/${slug}/specs`)
export const getClassSpecs = (slug, className) => api.get(`/meta/expansions/${slug}/classes/${encodeURIComponent(className)}/specs`)
export const getRaids = (slug) => api.get(`/meta/expansions/${slug}/raids`)
export const getRoles = (slug) => api.get(`/meta/expansions/${slug}/roles`)
export const getDefaultExpansion = () => api.get('/meta/expansions/default-expansion')

// Admin endpoints
export const createExpansion = (data) => api.post('/meta/expansions', data)
export const updateExpansion = (id, data) => api.put(`/meta/expansions/${id}`, data)
export const deleteExpansion = (id) => api.delete(`/meta/expansions/${id}`)
export const setDefaultExpansion = (slug) => api.put('/meta/expansions/default-expansion', { slug })
export const addRaid = (expansionId, data) => api.post(`/meta/expansions/${expansionId}/raids`, data)
export const updateRaid = (raidId, data) => api.put(`/meta/expansions/raids/${raidId}`, data)
export const deleteRaid = (raidId) => api.delete(`/meta/expansions/raids/${raidId}`)

// Class CRUD
export const addClass = (expansionId, data) => api.post(`/meta/expansions/${expansionId}/classes`, data)
export const updateClass = (classId, data) => api.put(`/meta/expansions/classes/${classId}`, data)
export const deleteClass = (classId) => api.delete(`/meta/expansions/classes/${classId}`)

// Spec CRUD
export const addSpec = (classId, data) => api.post(`/meta/expansions/classes/${classId}/specs`, data)
export const updateSpec = (specId, data) => api.put(`/meta/expansions/specs/${specId}`, data)
export const deleteSpec = (specId) => api.delete(`/meta/expansions/specs/${specId}`)
