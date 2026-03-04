/**
 * Expansions API module — communicates with /v2/meta/expansions endpoints.
 */
import api from '@/api'

// Public endpoints
export const listExpansions = () => api.get('/v2/meta/expansions')
export const getClasses = (slug) => api.get(`/v2/meta/expansions/${slug}/classes`)
export const getSpecs = (slug) => api.get(`/v2/meta/expansions/${slug}/specs`)
export const getClassSpecs = (slug, className) => api.get(`/v2/meta/expansions/${slug}/classes/${encodeURIComponent(className)}/specs`)
export const getRaids = (slug) => api.get(`/v2/meta/expansions/${slug}/raids`)
export const getRoles = (slug) => api.get(`/v2/meta/expansions/${slug}/roles`)
export const getDefaultExpansion = () => api.get('/v2/meta/expansions/default-expansion')

// Admin endpoints
export const createExpansion = (data) => api.post('/v2/meta/expansions', data)
export const updateExpansion = (id, data) => api.put(`/v2/meta/expansions/${id}`, data)
export const deleteExpansion = (id) => api.delete(`/v2/meta/expansions/${id}`)
export const setDefaultExpansion = (slug) => api.put('/v2/meta/expansions/default-expansion', { slug })
export const addRaid = (expansionId, data) => api.post(`/v2/meta/expansions/${expansionId}/raids`, data)
export const updateRaid = (raidId, data) => api.put(`/v2/meta/expansions/raids/${raidId}`, data)
export const deleteRaid = (raidId) => api.delete(`/v2/meta/expansions/raids/${raidId}`)

// Class CRUD
export const addClass = (expansionId, data) => api.post(`/v2/meta/expansions/${expansionId}/classes`, data)
export const updateClass = (classId, data) => api.put(`/v2/meta/expansions/classes/${classId}`, data)
export const deleteClass = (classId) => api.delete(`/v2/meta/expansions/classes/${classId}`)

// Spec CRUD
export const addSpec = (classId, data) => api.post(`/v2/meta/expansions/classes/${classId}/specs`, data)
export const updateSpec = (specId, data) => api.put(`/v2/meta/expansions/specs/${specId}`, data)
export const deleteSpec = (specId) => api.delete(`/v2/meta/expansions/specs/${specId}`)
