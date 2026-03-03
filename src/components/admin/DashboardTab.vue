<template>
  <div class="space-y-6">
    <!-- Overview Stats -->
    <WowCard>
      <h2 class="wow-heading text-base mb-4">{{ t('admin.dashboard.title') }}</h2>

      <div v-if="loading" class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>

      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <!-- Total Users -->
        <div class="p-4 rounded-lg bg-bg-secondary border border-border-default">
          <div class="text-lg mb-1">👥</div>
          <div class="text-xs text-text-muted uppercase">{{ t('admin.dashboard.totalUsers') }}</div>
          <div class="text-2xl font-bold text-accent-gold mt-1">{{ data.total_users }}</div>
          <div class="text-xs text-text-muted mt-2 space-y-0.5">
            <div>{{ t('admin.dashboard.activeUsers') }}: {{ data.active_users }}</div>
            <div>{{ t('admin.dashboard.adminUsers') }}: {{ data.admin_users }}</div>
          </div>
        </div>

        <!-- Guilds -->
        <div class="p-4 rounded-lg bg-bg-secondary border border-border-default">
          <div class="text-lg mb-1">🏰</div>
          <div class="text-xs text-text-muted uppercase">{{ t('admin.dashboard.totalGuilds') }}</div>
          <div class="text-2xl font-bold text-accent-gold mt-1">{{ data.total_guilds }}</div>
        </div>

        <!-- Total Raids -->
        <div class="p-4 rounded-lg bg-bg-secondary border border-border-default">
          <div class="text-lg mb-1">⚔️</div>
          <div class="text-xs text-text-muted uppercase">{{ t('admin.dashboard.totalRaids') }}</div>
          <div class="text-2xl font-bold text-accent-gold mt-1">{{ data.total_raids }}</div>
          <div class="text-xs text-text-muted mt-2">
            {{ t('admin.dashboard.upcomingRaids') }}: {{ data.upcoming_raids }}
          </div>
        </div>

        <!-- Characters -->
        <div class="p-4 rounded-lg bg-bg-secondary border border-border-default">
          <div class="text-lg mb-1">🧙</div>
          <div class="text-xs text-text-muted uppercase">{{ t('admin.dashboard.totalCharacters') }}</div>
          <div class="text-2xl font-bold text-accent-gold mt-1">{{ data.total_characters }}</div>
        </div>

        <!-- Signups -->
        <div class="p-4 rounded-lg bg-bg-secondary border border-border-default">
          <div class="text-lg mb-1">📝</div>
          <div class="text-xs text-text-muted uppercase">{{ t('admin.dashboard.totalSignups') }}</div>
          <div class="text-2xl font-bold text-accent-gold mt-1">{{ data.total_signups }}</div>
        </div>

        <!-- Database Size -->
        <div class="p-4 rounded-lg bg-bg-secondary border border-border-default">
          <div class="text-lg mb-1">💾</div>
          <div class="text-xs text-text-muted uppercase">{{ t('admin.dashboard.databaseSize') }}</div>
          <div class="text-2xl font-bold text-accent-gold mt-1">{{ formattedDbSize }}</div>
        </div>
      </div>
    </WowCard>

    <!-- System Health -->
    <WowCard>
      <h2 class="wow-heading text-base mb-4">{{ t('admin.dashboard.systemHealth') }}</h2>

      <div v-if="loading" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />

      <div v-else-if="!error" class="space-y-4">
        <!-- Job Queue -->
        <div class="flex flex-wrap gap-4">
          <div class="flex items-center gap-2 px-3 py-2 rounded bg-bg-secondary border border-border-default">
            <span
              class="inline-block w-2 h-2 rounded-full"
              :class="data.pending_jobs > 0 ? 'bg-yellow-400' : 'bg-green-400'"
            />
            <span class="text-xs text-text-muted">{{ t('admin.dashboard.pendingJobs') }}</span>
            <span class="text-sm font-bold text-text-primary">{{ data.pending_jobs }}</span>
          </div>
          <div class="flex items-center gap-2 px-3 py-2 rounded bg-bg-secondary border border-border-default">
            <span
              class="inline-block w-2 h-2 rounded-full"
              :class="data.failed_jobs > 0 ? 'bg-red-400' : 'bg-green-400'"
            />
            <span class="text-xs text-text-muted">{{ t('admin.dashboard.failedJobs') }}</span>
            <span class="text-sm font-bold text-text-primary">{{ data.failed_jobs }}</span>
          </div>
        </div>

        <!-- Database -->
        <div class="flex items-center gap-2 px-3 py-2 rounded bg-bg-secondary border border-border-default w-fit">
          <span class="text-sm">💾</span>
          <span class="text-xs text-text-muted">{{ t('admin.dashboard.databaseSize') }}</span>
          <span class="text-sm font-bold text-text-primary">{{ formattedDbSize }}</span>
        </div>
      </div>
    </WowCard>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import { getDashboard } from '@/api/admin'

const { t } = useI18n()

const loading = ref(true)
const error = ref(null)
const data = ref({
  total_users: 0,
  active_users: 0,
  admin_users: 0,
  total_guilds: 0,
  total_raids: 0,
  upcoming_raids: 0,
  total_characters: 0,
  total_signups: 0,
  pending_jobs: 0,
  failed_jobs: 0,
  database_size_kb: 0,
})

const KB_PER_MB = 1024
const KB_PER_GB = 1024 * 1024

const formattedDbSize = computed(() => {
  const kb = data.value.database_size_kb
  if (kb >= KB_PER_GB) return `${(kb / KB_PER_GB).toFixed(1)} GB`
  if (kb >= KB_PER_MB) return `${(kb / KB_PER_MB).toFixed(1)} MB`
  return `${kb} KB`
})

onMounted(async () => {
  loading.value = true
  try {
    data.value = await getDashboard()
  } catch {
    error.value = t('admin.dashboard.loadError')
  } finally {
    loading.value = false
  }
})
</script>
