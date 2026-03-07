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

  async function login(email, password, remember = true) {
    await authStore.login(email, password, remember)
    const redirect = router.currentRoute.value.query.redirect || '/dashboard'
    router.push(redirect)
  }

  async function register(username, email, password, createTenant = true) {
    const result = await authStore.register(username, email, password, createTenant)
    // If activation is required, return the result so the component can show the message
    if (result?.activation_required) {
      return result
    }
    // New users → setup wizard; mode depends on whether they created a tenant
    const mode = createTenant ? 'tenant' : 'player'
    router.push({ path: '/setup', query: { mode } })
    return result
  }

  async function logout() {
    await authStore.logout()
    router.push('/login')
  }

  return { isAuthenticated, currentUser, isLoading, authError, login, register, logout }
}
