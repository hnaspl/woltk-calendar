/**
 * Tenant API module — communicates with /tenants endpoints.
 */
import api from './index'

// --- Tenant CRUD ---
export const getTenants = () => api.get('/tenants/')
export const getTenant = (id) => api.get(`/tenants/${id}`)
export const updateTenant = (id, data) => api.put(`/tenants/${id}`, data)
export const deleteTenant = (id) => api.delete(`/tenants/${id}`)

// --- Membership ---
export const getTenantMembers = (tenantId) => api.get(`/tenants/${tenantId}/members`)
export const addTenantMember = (tenantId, userId, role = 'member') =>
  api.post(`/tenants/${tenantId}/members`, { user_id: userId, role })
export const updateTenantMember = (tenantId, userId, role) =>
  api.put(`/tenants/${tenantId}/members/${userId}`, { role })
export const removeTenantMember = (tenantId, userId) =>
  api.delete(`/tenants/${tenantId}/members/${userId}`)

// --- Invitations ---
export const getTenantInvitations = (tenantId) => api.get(`/tenants/${tenantId}/invitations`)
export const createTenantInvitation = (tenantId, data) =>
  api.post(`/tenants/${tenantId}/invitations`, data)
export const revokeTenantInvitation = (tenantId, invitationId) =>
  api.delete(`/tenants/${tenantId}/invitations/${invitationId}`)

// --- Accept invite ---
export const acceptInvite = (token) => api.post(`/invite/${token}`)

// --- Active tenant ---
export const getActiveTenant = () => api.get('/auth/active-tenant')
export const setActiveTenant = (tenantId) =>
  api.put('/auth/active-tenant', { tenant_id: tenantId })

// --- Admin ---
export const adminListTenants = () => api.get('/admin/tenants/')
export const adminGetTenant = (id) => api.get(`/admin/tenants/${id}`)
export const adminUpdateTenant = (id, data) => api.put(`/admin/tenants/${id}`, data)
export const adminSuspendTenant = (id) => api.post(`/admin/tenants/${id}/suspend`)
export const adminActivateTenant = (id) => api.post(`/admin/tenants/${id}/activate`)
export const adminDeleteTenant = (id) => api.delete(`/admin/tenants/${id}`)
