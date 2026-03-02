import api from './index'

// Roles CRUD
export const getRoles = () => api.get('/roles')

export const getRole = (roleId) => api.get(`/roles/${roleId}`)

export const createRole = (data) => api.post('/roles', data)

export const updateRole = (roleId, data) => api.put(`/roles/${roleId}`, data)

export const deleteRole = (roleId) => api.delete(`/roles/${roleId}`)

// Permissions listing
export const getPermissions = () => api.get('/roles/permissions')

// Grant rules
export const getGrantRules = () => api.get('/roles/grant-rules')

export const createGrantRule = (data) => api.post('/roles/grant-rules', data)

export const deleteGrantRule = (ruleId) => api.delete(`/roles/grant-rules/${ruleId}`)
