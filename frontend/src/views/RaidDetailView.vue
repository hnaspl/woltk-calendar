<template>
  <AppShell>
    <div class="p-4 md:p-6 space-y-6">
      <!-- Loading state -->
      <div v-if="loading" class="space-y-4">
        <div class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
        <div class="h-64 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      </div>

      <!-- Error -->
      <div v-else-if="error" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">
        {{ error }}
      </div>

      <template v-else-if="event">
        <!-- Event header -->
        <WowCard :gold="true">
          <div class="flex flex-col sm:flex-row items-start gap-4">
            <img
              :src="getRaidIcon(event.raid_type)"
              :alt="event.raid_type"
              class="w-20 h-20 rounded-lg border border-border-gold shadow-gold flex-shrink-0"
            />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap mb-2">
                <h1 class="wow-heading text-xl">{{ event.title }}</h1>
                <RaidSizeBadge v-if="event.size" :size="event.size" />
                <StatusBadge :status="event.status ?? 'open'" />
                <LockBadge :locked="event.is_locked" />
              </div>

              <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-text-muted">
                <span>📅 {{ formatDateTime(event.start_time ?? event.date) }}</span>
                <span v-if="event.end_time">→ {{ formatDateTime(event.end_time) }}</span>
                <RealmBadge v-if="event.realm" :realm="event.realm" />
              </div>

              <p v-if="event.description" class="mt-3 text-sm text-text-muted">
                {{ event.description }}
              </p>
            </div>

            <!-- Officer actions -->
            <div v-if="permissions.isOfficer.value" class="flex flex-wrap gap-2 flex-shrink-0">
              <WowButton variant="secondary" @click="toggleLock">
                {{ event.is_locked ? 'Unlock' : 'Lock' }}
              </WowButton>
              <WowButton variant="secondary" @click="doDuplicate">Duplicate</WowButton>
              <WowButton v-if="event.status !== 'completed'" variant="primary" @click="markComplete">
                Mark Done
              </WowButton>
              <WowButton variant="danger" @click="confirmCancel = true">Cancel Event</WowButton>
            </div>
          </div>
        </WowCard>

        <!-- Main content grid -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- Left column: signup form + composition -->
          <div class="space-y-6">
            <SignupForm
              v-if="event.status === 'open'"
              :event-id="event.id"
              :guild-id="guildId"
              :existing-signup="mySignup"
              @signed-up="onSignedUp"
              @updated="onSignupUpdated"
            />
            <CompositionSummary
              :signups="signups"
              :max-size="event.size"
              :tank-slots="event.tank_slots ?? 2"
              :healer-slots="event.healer_slots ?? 5"
              :dps-slots="event.dps_slots ?? 18"
            />
          </div>

          <!-- Right columns: signup list + lineup -->
          <div class="lg:col-span-2 space-y-6">
            <SignupList :signups="signups" />

            <LineupBoard
              v-if="permissions.isOfficer.value"
              :signups="signups"
              :event-id="event.id"
              :guild-id="guildId"
              :tank-slots="event.tank_slots ?? 2"
              :healer-slots="event.healer_slots ?? 5"
              :dps-slots="event.dps_slots ?? 18"
              @saved="uiStore.showToast('Lineup saved!', 'success')"
            />
          </div>
        </div>
      </template>
    </div>

    <!-- Cancel confirmation modal -->
    <WowModal v-model="confirmCancel" title="Cancel Event" size="sm">
      <p class="text-text-muted mb-4">Are you sure you want to cancel this event? This cannot be undone.</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="confirmCancel = false">Nevermind</WowButton>
          <WowButton variant="danger" :loading="actionLoading" @click="cancelEvent">Cancel Event</WowButton>
        </div>
      </template>
    </WowModal>
  </AppShell>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import RaidSizeBadge from '@/components/common/RaidSizeBadge.vue'
import RealmBadge from '@/components/common/RealmBadge.vue'
import LockBadge from '@/components/common/LockBadge.vue'
import SignupForm from '@/components/raids/SignupForm.vue'
import SignupList from '@/components/raids/SignupList.vue'
import CompositionSummary from '@/components/raids/CompositionSummary.vue'
import LineupBoard from '@/components/raids/LineupBoard.vue'
import { useGuildStore } from '@/stores/guild'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { usePermissions } from '@/composables/usePermissions'
import { useWowIcons } from '@/composables/useWowIcons'
import * as eventsApi from '@/api/events'
import * as signupsApi from '@/api/signups'

const route = useRoute()
const router = useRouter()
const guildStore = useGuildStore()
const authStore = useAuthStore()
const uiStore = useUiStore()
const permissions = usePermissions()
const { getRaidIcon } = useWowIcons()

const event = ref(null)
const signups = ref([])
const loading = ref(true)
const error = ref(null)
const actionLoading = ref(false)
const confirmCancel = ref(false)

const guildId = computed(() => guildStore.currentGuild?.id)

const mySignup = computed(() => {
  if (!authStore.user) return null
  return signups.value.find(s => s.user_id === authStore.user.id) ?? null
})

onMounted(async () => {
  loading.value = true
  error.value = null
  try {
    if (!guildStore.currentGuild) await guildStore.fetchGuilds()
    const [ev, su] = await Promise.all([
      eventsApi.getEvent(guildId.value, route.params.id),
      signupsApi.getSignups(guildId.value, route.params.id)
    ])
    event.value = ev
    signups.value = su
  } catch (err) {
    error.value = err?.response?.data?.message ?? 'Failed to load raid details'
  } finally {
    loading.value = false
  }
})

async function toggleLock() {
  if (!event.value) return
  actionLoading.value = true
  try {
    if (event.value.is_locked) {
      await eventsApi.unlockEvent(guildId.value, event.value.id)
      event.value.is_locked = false
    } else {
      await eventsApi.lockEvent(guildId.value, event.value.id)
      event.value.is_locked = true
    }
    uiStore.showToast(`Event ${event.value.is_locked ? 'locked' : 'unlocked'}`, 'success')
  } catch (err) {
    uiStore.showToast('Action failed', 'error')
  } finally {
    actionLoading.value = false
  }
}

async function markComplete() {
  actionLoading.value = true
  try {
    await eventsApi.completeEvent(guildId.value, event.value.id)
    event.value.status = 'completed'
    uiStore.showToast('Event marked as completed!', 'success')
  } catch {
    uiStore.showToast('Failed to complete event', 'error')
  } finally {
    actionLoading.value = false
  }
}

async function cancelEvent() {
  actionLoading.value = true
  try {
    await eventsApi.cancelEvent(guildId.value, event.value.id)
    event.value.status = 'cancelled'
    confirmCancel.value = false
    uiStore.showToast('Event cancelled', 'warning')
  } catch {
    uiStore.showToast('Failed to cancel event', 'error')
  } finally {
    actionLoading.value = false
  }
}

async function doDuplicate() {
  actionLoading.value = true
  try {
    const newEvent = await eventsApi.duplicateEvent(guildId.value, event.value.id)
    uiStore.showToast('Event duplicated! Redirecting…', 'success')
    router.push({ name: 'raid-detail', params: { id: newEvent.id } })
  } catch {
    uiStore.showToast('Failed to duplicate event', 'error')
  } finally {
    actionLoading.value = false
  }
}

function onSignedUp(signup) {
  signups.value.push(signup)
  uiStore.showToast('Signed up successfully!', 'success')
}

function onSignupUpdated(updated) {
  const idx = signups.value.findIndex(s => s.id === updated.id)
  if (idx !== -1) signups.value[idx] = updated
  uiStore.showToast('Signup updated!', 'success')
}

function formatDateTime(d) {
  if (!d) return '?'
  return new Date(d).toLocaleString('en-GB', {
    weekday: 'long', day: '2-digit', month: 'long',
    year: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}
</script>
