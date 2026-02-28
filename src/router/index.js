import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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
    path: '/guild/settings',
    name: 'guild-settings',
    component: () => import('@/views/GuildSettingsView.vue'),
    meta: { requiresAuth: true }
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

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  // If we haven't checked auth yet, try fetching the current user
  if (!authStore.user && !authStore.loading) {
    try {
      await authStore.fetchMe()
    } catch {
      // ignore – will redirect below
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
