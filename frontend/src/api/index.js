import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' }
})

// Response interceptor – unwrap data
api.interceptors.response.use(
  res => res.data,
  err => {
    // Normalize backend error: backend returns {"error": "..."} but
    // frontend catch blocks expect err.response.data.message
    if (err.response?.data?.error && !err.response.data.message) {
      err.response.data.message = err.response.data.error
    }
    return Promise.reject(err)
  }
)

export default api
