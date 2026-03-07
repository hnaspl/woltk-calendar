import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'
import { useTenantStore } from '@/stores/tenant'
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
    path: '/activate',
    name: 'activate',
    component: () => import('@/views/ActivateView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/forgot-password',
    name: 'forgot-password',
    component: () => import('@/views/ForgotPasswordView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/reset-password',
    name: 'reset-password',
    component: () => import('@/views/ResetPasswordView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/setup',
    name: 'setup',
    component: () => import('@/views/SetupWizardView.vue'),
    meta: { requiresAuth: true }
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
    path: '/admin/global',
    name: 'global-admin',
    component: () => import('@/views/GlobalAdminView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/roles',
    redirect: '/admin'
  },
  {
    path: '/tenant/settings',
    name: 'tenant-settings',
    component: () => import('@/views/TenantSettingsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/tenant/invites',
    name: 'tenant-invites',
    component: () => import('@/views/TenantInviteView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/invite/:token',
    name: 'invite-accept',
    component: () => import('@/views/InviteAcceptView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/guild-invite/:token',
    name: 'guild-invite-accept',
    component: () => import('@/views/GuildInviteAcceptView.vue'),
    meta: { requiresAuth: true }
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
    redirect: '/guild/templates'
  },
  {
    path: '/guild/recurring-raids',
    redirect: '/guild/templates'
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
        const tenantStore = useTenantStore()
        // Bootstrap tenant store
        await tenantStore.fetchTenants()
        tenantStore.setActiveTenantFromUser(authStore.user)
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
