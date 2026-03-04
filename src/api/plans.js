/**
 * Plans API module — communicates with /api/v2/admin/plans endpoints.
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v2',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.response.use(
  res => res.data,
  err => {
    if (err.response) {
      if (typeof err.response.data !== 'object' || err.response.data === null) {
        err.response.data = { error: `Server error (${err.response.status})`, message: `Server error (${err.response.status})` }
      } else {
        if (err.response.data.error && !err.response.data.message) {
          err.response.data.message = err.response.data.error
        }
      }
    }
    return Promise.reject(err)
  }
)

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
