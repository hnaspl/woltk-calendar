<template>
  <div class="space-y-6">
    <div v-if="loading" class="space-y-4">
      <div class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
    </div>
    <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>

    <template v-else>
      <!-- ── Platform Overview ────────────────────────────────── -->
      <WowCard>
        <h2 class="wow-heading text-base mb-4">{{ t('admin.dashboard.platformOverview') }}</h2>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          <StatCard icon="👥" :label="t('admin.dashboard.totalUsers')" :value="data.total_users" :sub="`${data.active_users} ${t('admin.dashboard.active')} · ${data.admin_users} ${t('admin.dashboard.admins')}`" />
          <StatCard icon="🏠" :label="t('admin.dashboard.totalTenants')" :value="data.total_tenants ?? 0" :sub="`${data.active_tenants ?? 0} ${t('admin.dashboard.active')}${data.suspended_tenants ? ` · ${data.suspended_tenants} ${t('admin.dashboard.suspended')}` : ''}`" />
          <StatCard icon="🏰" :label="t('admin.dashboard.totalGuilds')" :value="data.total_guilds" />
          <StatCard icon="⚔️" :label="t('admin.dashboard.totalRaids')" :value="data.total_raids" :sub="`${data.upcoming_raids} ${t('admin.dashboard.upcoming')}`" />
          <StatCard icon="🧙" :label="t('admin.dashboard.totalCharacters')" :value="data.total_characters" />
          <StatCard icon="📝" :label="t('admin.dashboard.totalSignups')" :value="data.total_signups" :sub="data.avg_signups_per_event != null ? `~${data.avg_signups_per_event} ${t('admin.dashboard.perEvent')}` : ''" />
          <StatCard icon="⏳" :label="t('admin.dashboard.benchQueue')" :value="data.bench_slots ?? 0" />
          <StatCard icon="💾" :label="t('admin.dashboard.databaseSize')" :value="formattedDbSize" />
        </div>
      </WowCard>

      <!-- ── Growth & Event Pipeline ─────────────────────────── -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Growth -->
        <WowCard>
          <h2 class="wow-heading text-base mb-4">📈 {{ t('admin.dashboard.growth') }}</h2>
          <div class="space-y-3">
            <GrowthRow :label="t('admin.dashboard.newUsers7d')" :value="data.new_users_7d ?? 0" color="text-green-400" />
            <GrowthRow :label="t('admin.dashboard.newUsers30d')" :value="data.new_users_30d ?? 0" color="text-green-300" />
            <GrowthRow :label="t('admin.dashboard.newGuilds7d')" :value="data.new_guilds_7d ?? 0" color="text-blue-400" />
            <GrowthRow :label="t('admin.dashboard.newEvents7d')" :value="data.new_events_7d ?? 0" color="text-purple-400" />
          </div>
        </WowCard>

        <!-- Event pipeline -->
        <WowCard>
          <h2 class="wow-heading text-base mb-4">📅 {{ t('admin.dashboard.eventPipeline') }}</h2>
          <div class="space-y-3">
            <GrowthRow :label="t('admin.dashboard.eventsToday')" :value="data.events_today ?? 0" color="text-accent-gold" />
            <GrowthRow :label="t('admin.dashboard.eventsThisWeek')" :value="data.events_this_week ?? 0" color="text-accent-gold" />
            <GrowthRow :label="t('admin.dashboard.eventsNextWeek')" :value="data.events_next_week ?? 0" color="text-blue-400" />
            <GrowthRow :label="t('admin.dashboard.completedEvents')" :value="data.completed_events ?? 0" color="text-green-400" />
            <GrowthRow :label="t('admin.dashboard.cancelledEvents')" :value="data.cancelled_events ?? 0" color="text-red-400" />
          </div>
        </WowCard>
      </div>

      <!-- ── Queue & Jobs Status ─────────────────────────────── -->
      <WowCard>
        <h2 class="wow-heading text-base mb-4">{{ t('admin.dashboard.queueStatus') }}</h2>
        <div class="space-y-4">
          <!-- Job counters -->
          <div class="flex flex-wrap gap-3">
            <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-bg-secondary border border-border-default">
              <span class="inline-block w-2.5 h-2.5 rounded-full" :class="data.pending_jobs > 0 ? 'bg-yellow-400' : 'bg-green-400'" />
              <span class="text-xs text-text-muted">{{ t('admin.dashboard.pendingJobs') }}</span>
              <span class="text-sm font-bold text-text-primary">{{ data.pending_jobs }}</span>
            </div>
            <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-bg-secondary border border-border-default">
              <span class="inline-block w-2.5 h-2.5 rounded-full" :class="data.running_jobs > 0 ? 'bg-blue-400 animate-pulse' : 'bg-gray-500'" />
              <span class="text-xs text-text-muted">{{ t('admin.dashboard.runningJobs') }}</span>
              <span class="text-sm font-bold text-text-primary">{{ data.running_jobs }}</span>
            </div>
            <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-bg-secondary border border-border-default">
              <span class="inline-block w-2.5 h-2.5 rounded-full" :class="data.failed_jobs > 0 ? 'bg-red-400' : 'bg-green-400'" />
              <span class="text-xs text-text-muted">{{ t('admin.dashboard.failedJobs') }}</span>
              <span class="text-sm font-bold text-text-primary">{{ data.failed_jobs }}</span>
            </div>
            <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-bg-secondary border border-border-default">
              <span class="inline-block w-2.5 h-2.5 rounded-full bg-green-400" />
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
                    <span class="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium" :class="jobStatusClass(job.status)">{{ job.status }}</span>
                  </td>
                  <td class="hidden sm:table-cell px-3 py-1.5 text-text-muted">{{ job.attempts }}</td>
                  <td class="hidden md:table-cell px-3 py-1.5 text-text-muted">{{ fmtDate(job.created_at) }}</td>
                  <td class="hidden lg:table-cell px-3 py-1.5 text-red-400 truncate max-w-[200px]" :title="job.last_error">{{ job.last_error || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="text-xs text-text-muted">{{ t('admin.dashboard.noRecentJobs') }}</div>
        </div>
      </WowCard>

      <!-- ── Tenant Breakdown ────────────────────────────────── -->
      <WowCard v-if="data.tenant_breakdown?.length">
        <h2 class="wow-heading text-base mb-4">🏠 {{ t('admin.dashboard.tenantBreakdown') }}</h2>
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="bg-bg-tertiary border-b border-border-default">
                <th class="text-left px-3 py-2 text-text-muted">{{ t('admin.dashboard.tenantName') }}</th>
                <th class="text-left px-3 py-2 text-text-muted">{{ t('admin.dashboard.tenantPlan') }}</th>
                <th class="text-center px-3 py-2 text-text-muted">{{ t('admin.dashboard.totalGuilds') }}</th>
                <th class="text-center px-3 py-2 text-text-muted">{{ t('common.labels.members') }}</th>
                <th class="text-center px-3 py-2 text-text-muted">{{ t('admin.dashboard.events') }}</th>
                <th class="text-center px-3 py-2 text-text-muted">{{ t('common.fields.status') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border-default">
              <tr v-for="tb in data.tenant_breakdown" :key="tb.id" class="hover:bg-bg-tertiary/50">
                <td class="px-3 py-2 text-text-primary font-medium">{{ tb.name }}</td>
                <td class="px-3 py-2">
                  <span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-accent-gold/20 text-accent-gold border border-accent-gold/30">{{ tb.plan }}</span>
                </td>
                <td class="px-3 py-2 text-center text-text-muted">{{ tb.guilds }}</td>
                <td class="px-3 py-2 text-center text-text-muted">{{ tb.members }}</td>
                <td class="px-3 py-2 text-center text-text-muted">{{ tb.events }}</td>
                <td class="px-3 py-2 text-center">
                  <span class="px-1.5 py-0.5 rounded text-[10px] font-medium"
                    :class="tb.is_active ? 'bg-green-900/50 text-green-300 border border-green-600' : 'bg-red-900/50 text-red-300 border border-red-600'">
                    {{ tb.is_active ? t('admin.dashboard.active') : t('admin.dashboard.suspended') }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </WowCard>

      <!-- ── Recent Activity ─────────────────────────────────── -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Recent registrations -->
        <WowCard>
          <h2 class="wow-heading text-base mb-4">👤 {{ t('admin.dashboard.recentRegistrations') }}</h2>
          <div v-if="!data.recent_registrations?.length" class="text-xs text-text-muted py-4 text-center">{{ t('admin.dashboard.noRecentRegistrations') }}</div>
          <div v-else class="space-y-2">
            <div v-for="u in data.recent_registrations" :key="u.id"
                 class="flex items-center gap-3 px-3 py-2 rounded-lg bg-bg-secondary border border-border-default">
              <div class="w-7 h-7 rounded-full bg-bg-tertiary border border-border-default flex items-center justify-center text-[10px] text-accent-gold font-bold uppercase flex-shrink-0">
                {{ u.username?.[0] ?? '?' }}
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm text-text-primary font-medium truncate">{{ u.username }}</div>
                <div class="text-[10px] text-text-muted">{{ fmtDate(u.created_at) }}</div>
              </div>
              <span v-if="u.is_admin" class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-accent-gold/20 text-accent-gold border border-accent-gold/30">{{ t('admin.dashboard.admins') }}</span>
            </div>
          </div>
        </WowCard>

        <!-- Upcoming events -->
        <WowCard>
          <h2 class="wow-heading text-base mb-4">📅 {{ t('admin.dashboard.upcomingEventList') }}</h2>
          <div v-if="!data.upcoming_event_list?.length" class="text-xs text-text-muted py-4 text-center">{{ t('admin.dashboard.noUpcomingEvents') }}</div>
          <div v-else class="space-y-2">
            <div v-for="ev in data.upcoming_event_list" :key="ev.id"
                 class="flex items-center gap-3 px-3 py-2 rounded-lg bg-bg-secondary border border-border-default">
              <div class="flex-1 min-w-0">
                <div class="text-sm text-text-primary font-medium truncate">{{ ev.title }}</div>
                <div class="text-[10px] text-text-muted">{{ ev.guild_name }} · {{ fmtDate(ev.starts_at) }}</div>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <span class="text-[10px] text-text-muted">{{ ev.raid_size }}-man</span>
                <span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-bg-tertiary text-text-muted border border-border-default">{{ ev.signups }} {{ t('admin.dashboard.signups') }}</span>
              </div>
            </div>
          </div>
        </WowCard>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, h, defineComponent } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import { getDashboard } from '@/api/admin'

const { t, locale } = useI18n()

// ── Inline sub-components ───────────────────────────────────────
const StatCard = defineComponent({
  props: { icon: String, label: String, value: [String, Number], sub: String },
  setup(props) {
    return () => h('div', { class: 'p-4 rounded-lg bg-bg-secondary border border-border-default' }, [
      h('div', { class: 'text-lg mb-1' }, props.icon),
      h('div', { class: 'text-[10px] text-text-muted uppercase tracking-wider' }, props.label),
      h('div', { class: 'text-2xl font-bold text-accent-gold mt-1' }, String(props.value ?? 0)),
      props.sub ? h('div', { class: 'text-[10px] text-text-muted mt-1.5' }, props.sub) : null,
    ])
  }
})

const GrowthRow = defineComponent({
  props: { label: String, value: [String, Number], color: String },
  setup(props) {
    return () => h('div', { class: 'flex items-center justify-between p-3 rounded-lg bg-bg-secondary border border-border-default' }, [
      h('span', { class: 'text-xs text-text-muted' }, props.label),
      h('span', { class: `text-sm font-bold ${props.color || 'text-text-primary'}` }, String(props.value ?? 0)),
    ])
  }
})

// ── Data ────────────────────────────────────────────────────────
const loading = ref(true)
const error = ref(null)
const data = ref({})

const KB_PER_MB = 1024
const KB_PER_GB = 1024 * 1024

const formattedDbSize = computed(() => {
  const kb = data.value.database_size_kb
  if (!kb) return '—'
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

function fmtDate(iso) {
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
