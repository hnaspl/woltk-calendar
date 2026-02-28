import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' }
})

// Response interceptor – unwrap data
api.interceptors.response.use(
  res => res.data,
  err => Promise.reject(err)
)

export default api
