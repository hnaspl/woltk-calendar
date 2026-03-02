import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'
import { useConstantsStore } from '@/stores/constants'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/calendar',
    name: 'calendar',
    component: () => import('@/views/CalendarView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/raids/:id',
    name: 'raid-detail',
    component: () => import('@/views/RaidDetailView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/characters',
    name: 'characters',
    component: () => import('@/views/CharacterManagerView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/attendance',
    name: 'attendance',
    component: () => import('@/views/AttendanceView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('@/views/UserProfileView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('@/views/AdminPanelView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/roles',
    redirect: '/admin'
  },
  {
    path: '/guild/settings',
    redirect: '/admin'
  },
  {
    path: '/guild/raid-definitions',
    name: 'raid-definitions',
    component: () => import('@/views/RaidDefinitionsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/guild/templates',
    name: 'templates',
    component: () => import('@/views/TemplatesView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/guild/series',
    name: 'series',
    component: () => import('@/views/SeriesView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

// One-time flag: ensures session restore happens exactly once on app start.
let _authChecked = false

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  // First navigation (page load / refresh): always restore session from cookie
  if (!_authChecked) {
    _authChecked = true
    try {
      // Fetch constants (public) in parallel with session restore
      const constantsStore = useConstantsStore()
      const authPromise = authStore.fetchMe()
      constantsStore.fetchConstants()  // fire-and-forget, non-blocking
      await authPromise
      // Bootstrap guild store so currentGuild & members are available for permissions
      if (authStore.user) {
        const guildStore = useGuildStore()
        await guildStore.fetchGuilds()
      }
    } catch {
      // Not authenticated – proceed to redirect logic below
    }
  }

  // Redirect authenticated users away from login/register
  if (authStore.user && to.meta.requiresAuth === false) {
    return { name: 'dashboard' }
  }

  // Redirect unauthenticated users away from protected pages
  if (!authStore.user && to.meta.requiresAuth) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  return true
})

export default router
