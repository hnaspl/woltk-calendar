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

    <!-- Queue & Jobs Status -->
    <WowCard>
      <h2 class="wow-heading text-base mb-4">{{ t('admin.dashboard.queueStatus') }}</h2>

      <div v-if="loading" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />

      <div v-else-if="!error" class="space-y-4">
        <!-- Job counters -->
        <div class="flex flex-wrap gap-3">
          <div class="flex items-center gap-2 px-3 py-2 rounded bg-bg-secondary border border-border-default">
            <span class="inline-block w-2 h-2 rounded-full" :class="data.pending_jobs > 0 ? 'bg-yellow-400' : 'bg-green-400'" />
            <span class="text-xs text-text-muted">{{ t('admin.dashboard.pendingJobs') }}</span>
            <span class="text-sm font-bold text-text-primary">{{ data.pending_jobs }}</span>
          </div>
          <div class="flex items-center gap-2 px-3 py-2 rounded bg-bg-secondary border border-border-default">
            <span class="inline-block w-2 h-2 rounded-full" :class="data.running_jobs > 0 ? 'bg-blue-400 animate-pulse' : 'bg-gray-400'" />
            <span class="text-xs text-text-muted">{{ t('admin.dashboard.runningJobs') }}</span>
            <span class="text-sm font-bold text-text-primary">{{ data.running_jobs }}</span>
          </div>
          <div class="flex items-center gap-2 px-3 py-2 rounded bg-bg-secondary border border-border-default">
            <span class="inline-block w-2 h-2 rounded-full" :class="data.failed_jobs > 0 ? 'bg-red-400' : 'bg-green-400'" />
            <span class="text-xs text-text-muted">{{ t('admin.dashboard.failedJobs') }}</span>
            <span class="text-sm font-bold text-text-primary">{{ data.failed_jobs }}</span>
          </div>
          <div class="flex items-center gap-2 px-3 py-2 rounded bg-bg-secondary border border-border-default">
            <span class="inline-block w-2 h-2 rounded-full bg-green-400" />
            <span class="text-xs text-text-muted">{{ t('admin.dashboard.completedJobs') }}</span>
            <span class="text-sm font-bold text-text-primary">{{ data.done_jobs }}</span>
          </div>
        </div>

        <!-- Recent queue items -->
        <div v-if="data.recent_queue && data.recent_queue.length" class="overflow-x-auto">
          <h3 class="text-xs text-text-muted uppercase mb-2">{{ t('admin.dashboard.recentJobs') }}</h3>
          <table class="w-full text-xs">
            <thead>
              <tr class="bg-bg-tertiary border-b border-border-default">
                <th class="text-left px-3 py-1.5 text-text-muted">{{ t('admin.dashboard.jobType') }}</th>
                <th class="text-left px-3 py-1.5 text-text-muted">{{ t('common.fields.status') }}</th>
                <th class="hidden sm:table-cell text-left px-3 py-1.5 text-text-muted">{{ t('admin.dashboard.jobAttempts') }}</th>
                <th class="hidden md:table-cell text-left px-3 py-1.5 text-text-muted">{{ t('admin.dashboard.jobCreated') }}</th>
                <th class="hidden lg:table-cell text-left px-3 py-1.5 text-text-muted">{{ t('admin.dashboard.jobError') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border-default">
              <tr v-for="job in data.recent_queue" :key="job.id" class="hover:bg-bg-tertiary/50">
                <td class="px-3 py-1.5 text-text-primary font-medium">{{ job.type }}</td>
                <td class="px-3 py-1.5">
                  <span
                    class="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium"
                    :class="jobStatusClass(job.status)"
                  >{{ job.status }}</span>
                </td>
                <td class="hidden sm:table-cell px-3 py-1.5 text-text-muted">{{ job.attempts }}</td>
                <td class="hidden md:table-cell px-3 py-1.5 text-text-muted">{{ formatJobDate(job.created_at) }}</td>
                <td class="hidden lg:table-cell px-3 py-1.5 text-red-400 truncate max-w-[200px]" :title="job.last_error">{{ job.last_error || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="text-xs text-text-muted">{{ t('admin.dashboard.noRecentJobs') }}</div>
      </div>
    </WowCard>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import { getDashboard } from '@/api/admin'

const { t, locale } = useI18n()

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
  running_jobs: 0,
  failed_jobs: 0,
  done_jobs: 0,
  recent_queue: [],
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

function jobStatusClass(status) {
  switch (status) {
    case 'queued': return 'bg-yellow-900/50 text-yellow-300 border border-yellow-600'
    case 'running': return 'bg-blue-900/50 text-blue-300 border border-blue-600'
    case 'done': return 'bg-green-900/50 text-green-300 border border-green-600'
    case 'failed': return 'bg-red-900/50 text-red-300 border border-red-600'
    default: return 'bg-bg-tertiary text-text-muted'
  }
}

function formatJobDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(locale.value, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

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
