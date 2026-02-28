import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

export function useAuth() {
  const authStore = useAuthStore()
  const router = useRouter()

  const isAuthenticated = computed(() => !!authStore.user)
  const currentUser = computed(() => authStore.user)
  const isLoading = computed(() => authStore.loading)
  const authError = computed(() => authStore.error)

  async function login(email, password) {
    await authStore.login(email, password)
    const redirect = router.currentRoute.value.query.redirect || '/dashboard'
    router.push(redirect)
  }

  async function register(username, email, password) {
    await authStore.register(username, email, password)
    router.push('/dashboard')
  }

  async function logout() {
    await authStore.logout()
    router.push('/login')
  }

  return { isAuthenticated, currentUser, isLoading, authError, login, register, logout }
}
