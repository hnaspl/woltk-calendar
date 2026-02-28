<template>
  <AppShell>
    <div class="p-4 md:p-6 space-y-6">
      <div class="flex items-center justify-between">
        <h1 class="wow-heading text-2xl">Attendance</h1>
        <div class="flex items-center gap-3">
          <select
            v-model="period"
            class="bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
          >
            <option value="30">Last 30 days</option>
            <option value="60">Last 60 days</option>
            <option value="90">Last 90 days</option>
            <option value="all">All time</option>
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
        <AttendanceSummary :records="records" :events="events" />
        <AttendanceTable :records="records" :events="events" :signups="signups" />
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
import * as attendanceApi from '@/api/attendance'
import * as eventsApi from '@/api/events'

const guildStore = useGuildStore()

const loading = ref(true)
const error = ref(null)
const period = ref('30')
const records = ref([])
const events = ref([])
const signups = ref([])

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
    const [recs, evs] = await Promise.all([
      attendanceApi.getAttendance(guildId, params),
      eventsApi.getEvents(guildId, { status: 'completed', ...params })
    ])
    records.value = recs
    events.value = evs
  } catch (err) {
    error.value = err?.response?.data?.message ?? 'Failed to load attendance data'
  } finally {
    loading.value = false
  }
}
</script>
