<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6">
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
        <h1 class="wow-heading text-xl sm:text-2xl">{{ t('attendance.title') }}</h1>
        <div class="flex items-center gap-3">
          <select
            v-model="period"
            class="bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
          >
            <option value="30">{{ t('common.time.last30Days') }}</option>
            <option value="60">{{ t('common.time.last60Days') }}</option>
            <option value="90">{{ t('common.time.last90Days') }}</option>
            <option value="all">{{ t('common.time.allTime') }}</option>
          </select>
        </div>
      </div>

      <div v-if="loading" class="space-y-4">
        <div class="h-24 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
        <div class="h-64 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      </div>

      <div v-else-if="error" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">
        {{ error }}
      </div>

      <template v-else>
        <AttendanceSummary :records="records" />
        <AttendanceTable :records="records" :events="events" />
      </template>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import AttendanceSummary from '@/components/attendance/AttendanceSummary.vue'
import AttendanceTable from '@/components/attendance/AttendanceTable.vue'
import { useGuildStore } from '@/stores/guild'
import { useAuthStore } from '@/stores/auth'
import * as attendanceApi from '@/api/attendance'
import * as eventsApi from '@/api/events'
import { useI18n } from 'vue-i18n'

const guildStore = useGuildStore()
const authStore = useAuthStore()
const { t } = useI18n()

const loading = ref(true)
const error = ref(null)
const period = ref('30')
const records = ref([])
const events = ref([])

onMounted(() => fetchData())
watch(period, fetchData)

async function fetchData() {
  loading.value = true
  error.value = null
  if (!guildStore.currentGuild) await guildStore.fetchGuilds()
  const guildId = guildStore.currentGuild?.id
  if (!guildId) { loading.value = false; return }

  try {
    const params = period.value !== 'all' ? { days: period.value } : {}
    // Only fetch current user's attendance records
    params.user_id = authStore.user?.id
    const [recs, evs] = await Promise.all([
      attendanceApi.getAttendance(guildId, params),
      eventsApi.getEvents(guildId)
    ])
    records.value = recs
    events.value = evs
  } catch (err) {
    error.value = err?.response?.data?.message ?? t('attendance.failedToLoad')
  } finally {
    loading.value = false
  }
}
</script>
