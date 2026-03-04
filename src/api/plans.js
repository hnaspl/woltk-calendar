/**
 * Plans API module — communicates with /admin/plans endpoints.
 */
import api from './index'

// --- Admin Plan CRUD ---
export const listPlans = () => api.get('/admin/plans/')
export const createPlan = (data) => api.post('/admin/plans/', data)
export const getPlan = (id) => api.get(`/admin/plans/${id}`)
export const updatePlan = (id, data) => api.put(`/admin/plans/${id}`, data)
export const deletePlan = (id) => api.delete(`/admin/plans/${id}`)

// --- Billing operations ---
export const assignPlanToTenant = (tenantId, planId) =>
  api.post('/admin/plans/assign', { tenant_id: tenantId, plan_id: planId })

// --- Tenant usage (delegates to admin_tenants) ---
export const getTenantUsage = (tenantId) => api.get(`/admin/tenants/${tenantId}/usage`)

// --- Public plans (no auth required) ---
export const listActivePlans = () => api.get('/plans/')
