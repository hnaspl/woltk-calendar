import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as authApi from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Deduplication: reuse the in-flight promise so concurrent callers
  // (router guard + App.vue onMounted) share a single API request.
  let _fetchPromise = null

  async function fetchMe() {
    if (_fetchPromise) return _fetchPromise

    loading.value = true
    error.value = null

    _fetchPromise = authApi.getMe()
      .then(data => { user.value = data; return data })
      .catch(err => { user.value = null; throw err })
      .finally(() => { loading.value = false; _fetchPromise = null })

    return _fetchPromise
  }

  async function login(email, password) {
    loading.value = true
    error.value = null
    try {
      const data = await authApi.login({ email, password })
      user.value = data.user ?? data
    } catch (err) {
      error.value = err?.response?.data?.message || 'Login failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function register(username, email, password) {
    loading.value = true
    error.value = null
    try {
      const data = await authApi.register({ username, email, password })
      user.value = data.user ?? data
    } catch (err) {
      error.value = err?.response?.data?.message || 'Registration failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    loading.value = true
    try {
      await authApi.logout()
    } finally {
      user.value = null
      loading.value = false
    }
  }

  return { user, loading, error, fetchMe, login, register, logout }
})
