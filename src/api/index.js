import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' }
})

// Request interceptor – inject X-Tenant-Id header from tenant store
api.interceptors.request.use(config => {
  // Lazy import to avoid circular dependency at module load time
  try {
    const { useTenantStore } = require('@/stores/tenant')
    const tenantStore = useTenantStore()
    if (tenantStore.activeTenantId) {
      config.headers['X-Tenant-Id'] = tenantStore.activeTenantId
    }
  } catch {
    // Store not yet initialized — skip header
  }
  return config
})

// Response interceptor – unwrap data
api.interceptors.response.use(
  res => res.data,
  err => {
    // Ensure err.response.data is always an object with a message field,
    // even when the backend returns HTML (e.g. Flask debug pages).
    if (err.response) {
      if (typeof err.response.data !== 'object' || err.response.data === null) {
        err.response.data = { error: `Server error (${err.response.status})`, message: `Server error (${err.response.status})` }
      } else {
        // Normalize: backend returns {"error": "..."} but frontend expects .message
        if (err.response.data.error && !err.response.data.message) {
          err.response.data.message = err.response.data.error
        }
      }
    }
    return Promise.reject(err)
  }
)

export default api
