<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6">
      <!-- Loading permissions -->
      <div v-if="!permissions.permissionsLoaded.value && !authStore.user?.is_admin" class="p-4 rounded-lg bg-bg-tertiary border border-border-default text-text-muted flex items-center gap-3">
        <div class="w-5 h-5 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin" />
        Loading…
      </div>
      <!-- No permission -->
      <div v-else-if="!hasViewAccess" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">
        You do not have the appropriate permissions to access this page.
      </div>
      <template v-else>
      <div class="flex items-center justify-between">
        <div>
          <h1 class="wow-heading text-xl sm:text-2xl">Recurring Raids</h1>
          <p class="text-text-muted text-sm mt-0.5">Set up weekly or biweekly raid schedules and bulk-generate events</p>
        </div>
        <WowButton @click="openAddModal">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          New Series
        </WowButton>
      </div>

      <div v-if="loading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="h-24 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      </div>
      <div v-else-if="noGuild" class="p-4 rounded-lg bg-blue-900/30 border border-blue-600 text-blue-300">
        You need to create or join a guild first before managing recurring raids. Use the sidebar to create a guild.
      </div>
      <div v-else-if="error" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">{{ error }}</div>
      <div v-else-if="seriesList.length === 0" class="text-center py-12 text-text-muted">
        No recurring raids yet. Create a series to auto-generate weekly or biweekly events.
      </div>
      <div v-else class="space-y-3">
        <WowCard v-for="s in seriesList" :key="s.id">
          <div class="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4">
            <div class="w-12 h-12 rounded border border-border-default bg-bg-tertiary flex items-center justify-center text-xl flex-shrink-0">🔁</div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-bold text-text-primary">{{ s.title }}</span>
                <RaidSizeBadge v-if="s.default_raid_size" :size="s.default_raid_size" />
                <span v-if="s.default_difficulty === 'heroic'" class="text-xs px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-300 border border-orange-600">Heroic</span>
                <span class="text-xs px-1.5 py-0.5 rounded border" :class="s.active ? 'bg-green-500/20 text-green-300 border-green-600' : 'bg-red-500/20 text-red-300 border-red-600'">
                  {{ s.active ? 'Active' : 'Inactive' }}
                </span>
              </div>
              <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-text-muted mt-1">
                <RealmBadge v-if="s.realm_name" :realm="s.realm_name" />
                <span v-if="s.template_id" class="text-accent-gold">📋 {{ templateName(s.template_id) }}</span>
                <span v-if="s.recurrence_rule">📅 {{ formatRecurrence(s.recurrence_rule) }}</span>
                <span v-if="s.start_time_local">🕐 {{ s.start_time_local }}</span>
                <span>⏱ {{ s.duration_minutes }}min</span>
              </div>
            </div>
            <div class="flex items-center gap-2 flex-wrap">
              <WowButton v-if="hasMultipleGuilds" variant="secondary" class="text-xs py-1.5" @click="openCopyModal(s)">
                📋 Copy
              </WowButton>
              <WowButton variant="primary" class="text-xs py-1.5" @click="openGenerate(s)">
                Generate Events
              </WowButton>
              <WowButton variant="secondary" class="text-xs py-1.5" @click="openEditModal(s)">
                Edit
              </WowButton>
              <WowButton variant="danger" class="text-xs py-1.5 px-2" @click="confirmDelete(s)">✕</WowButton>
            </div>
          </div>
        </WowCard>
      </div>
      </template>
    </div>

    <!-- Add/Edit series modal -->
    <WowModal v-model="showModal" :title="editing ? 'Edit Recurring Raid' : 'New Recurring Raid'" size="md">
      <form @submit.prevent="saveSeries" class="space-y-4">
        <div>
          <label class="block text-xs text-text-muted mb-1">Title *</label>
          <input v-model="form.title" required placeholder="e.g. Weekly ICC 25" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div v-if="templates.length > 0">
          <label class="block text-xs text-text-muted mb-1">Template (optional)</label>
          <select v-model="form.template_id" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" @change="onTemplateChange">
            <option :value="null">No template — configure manually</option>
            <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }} ({{ t.raid_size }}-man {{ t.difficulty }})</option>
          </select>
          <span class="text-[10px] text-text-muted">Selecting a template auto-fills size, difficulty &amp; duration</span>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Guild (Realm) *</label>
          <select v-model.number="selectedGuildId" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option v-for="g in guildStore.guilds" :key="g.id" :value="g.id">{{ g.name }} ({{ g.realm_name }})</option>
          </select>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">Recurrence *</label>
            <select v-model="form.recurrence_rule" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="">Select…</option>
              <option value="weekly">Weekly</option>
              <option value="biweekly">Biweekly</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Start Time (server)</label>
            <input v-model="form.start_time_local" type="time" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">Raid Size</label>
            <select v-model.number="form.default_raid_size" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option :value="10">10-man</option>
              <option :value="25">25-man</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Difficulty</label>
            <select v-model="form.default_difficulty" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="normal">Normal</option>
              <option value="heroic">Heroic</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Duration (min)</label>
            <input v-model.number="form.duration_minutes" type="number" min="30" max="600" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
        </div>
        <div v-if="formError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ formError }}</div>
        <!-- Multi-guild creation -->
        <div v-if="!editing && otherGuilds.length > 0" class="p-3 rounded bg-bg-tertiary border border-border-default">
          <label class="flex items-center gap-2 cursor-pointer">
            <input v-model="applyToOtherGuilds" type="checkbox" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
            <span class="text-sm text-text-primary">Also create in my other guilds</span>
          </label>
          <div v-if="applyToOtherGuilds" class="mt-2 space-y-1 pl-6">
            <label class="flex items-center gap-2 cursor-pointer mb-1">
              <input type="checkbox" :checked="allOtherGuildsSelected" @change="toggleAllOtherGuilds" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
              <span class="text-xs text-accent-gold font-semibold">Copy to all</span>
            </label>
            <label v-for="g in copyTargetGuilds" :key="g.id" class="flex items-center gap-2 cursor-pointer">
              <input v-model="selectedGuildIds" :value="g.id" type="checkbox" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
              <span class="text-xs text-text-muted">{{ g.name }} <span class="text-text-muted/60">({{ g.realm_name }})</span></span>
            </label>
          </div>
        </div>
      </form>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showModal = false">Cancel</WowButton>
          <WowButton :loading="saving" @click="saveSeries">{{ editing ? 'Save' : 'Create' }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Copy to Guild modal -->
    <WowModal v-model="showCopyModal" title="Copy Series to Guilds" size="sm">
      <p class="text-text-muted text-sm mb-3">Copy <strong class="text-text-primary">{{ copySource?.title }}</strong> to selected guilds:</p>
      <div class="space-y-1">
        <label class="flex items-center gap-2 cursor-pointer mb-1">
          <input type="checkbox" :checked="allCopyGuildsSelected" @change="toggleAllCopyGuilds" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
          <span class="text-xs text-accent-gold font-semibold">Copy to all</span>
        </label>
        <label v-for="g in otherGuilds" :key="g.id" class="flex items-center gap-2 cursor-pointer">
          <input v-model="copyGuildIds" :value="g.id" type="checkbox" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
          <span class="text-xs text-text-muted">{{ g.name }} <span class="text-text-muted/60">({{ g.realm_name }})</span></span>
        </label>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showCopyModal = false">Cancel</WowButton>
          <WowButton :loading="saving" @click="doCopy" :disabled="copyGuildIds.length === 0">Copy</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Confirmation modal for no guilds selected -->
    <WowModal v-model="showNoGuildConfirm" title="No additional guilds selected" size="sm">
      <p class="text-text-muted text-sm">This series will only be created in <strong class="text-text-primary">{{ selectedGuildLabel }}</strong>. Would you like to go back and select guilds to copy to?</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="goBackToForm">Go Back</WowButton>
          <WowButton @click="confirmSaveCurrentOnly">Continue</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Generate events modal -->
    <WowModal v-model="showGenerate" title="Generate Events" size="sm">
      <div class="space-y-4">
        <p class="text-text-muted text-sm">Generate upcoming events from <strong class="text-text-primary">{{ generateTarget?.title }}</strong>.</p>
        <div>
          <label class="block text-xs text-text-muted mb-1">How many events to create?</label>
          <select v-model.number="generateCount" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option :value="1">1 event</option>
            <option :value="2">2 events</option>
            <option :value="4">4 events</option>
            <option :value="8">8 events</option>
          </select>
        </div>
        <div v-if="generateResult" class="p-3 rounded bg-green-900/30 border border-green-600 text-green-300 text-sm">
          ✅ Created {{ generateResult }} event(s)! Check the calendar.
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showGenerate = false">Close</WowButton>
          <WowButton :loading="saving" @click="doGenerate">Generate</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Delete confirmation -->
    <WowModal v-model="showDeleteConfirm" title="Delete Series" size="sm">
      <p class="text-text-muted">Delete recurring raid <strong class="text-text-primary">{{ deleteTarget?.title }}</strong>? Existing events created from this series won't be affected.</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showDeleteConfirm = false">Cancel</WowButton>
          <WowButton variant="danger" :loading="saving" @click="doDelete">Delete</WowButton>
        </div>
      </template>
    </WowModal>
  </AppShell>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import RaidSizeBadge from '@/components/common/RaidSizeBadge.vue'
import RealmBadge from '@/components/common/RealmBadge.vue'
import { useGuildStore } from '@/stores/guild'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { usePermissions } from '@/composables/usePermissions'
import * as seriesApi from '@/api/series'
import * as templatesApi from '@/api/templates'

const guildStore = useGuildStore()
const authStore = useAuthStore()
const uiStore = useUiStore()
const permissions = usePermissions()

const hasViewAccess = computed(() => permissions.can('create_events') || permissions.can('manage_series'))
const hasMultipleGuilds = computed(() => guildStore.guilds.length > 1)

const seriesList = ref([])
const templates = ref([])
const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const noGuild = ref(false)
const formError = ref(null)
const showModal = ref(false)
const showGenerate = ref(false)
const showDeleteConfirm = ref(false)
const showCopyModal = ref(false)
const showNoGuildConfirm = ref(false)
const editing = ref(null)
const generateTarget = ref(null)
const generateCount = ref(4)
const generateResult = ref(null)
const deleteTarget = ref(null)
const copySource = ref(null)

const selectedGuildId = ref(null)

const form = reactive({
  title: '',
  recurrence_rule: 'weekly',
  start_time_local: '19:00',
  duration_minutes: 180,
  default_raid_size: 25,
  default_difficulty: 'normal',
  template_id: null
})
const applyToOtherGuilds = ref(false)
const selectedGuildIds = ref([])
const copyGuildIds = ref([])

const otherGuilds = computed(() =>
  guildStore.guilds.filter(g => g.id !== guildStore.currentGuild?.id)
)

// For multi-guild creation, exclude the guild already selected as target
const copyTargetGuilds = computed(() =>
  guildStore.guilds.filter(g => g.id !== selectedGuildId.value)
)

const selectedGuildObj = computed(() =>
  guildStore.guilds.find(g => g.id === selectedGuildId.value)
)

const selectedGuildLabel = computed(() => {
  const g = selectedGuildObj.value
  return g ? `${g.name} (${g.realm_name})` : ''
})

const allOtherGuildsSelected = computed(() =>
  copyTargetGuilds.value.length > 0 && copyTargetGuilds.value.every(g => selectedGuildIds.value.includes(g.id))
)

const allCopyGuildsSelected = computed(() =>
  otherGuilds.value.length > 0 && otherGuilds.value.every(g => copyGuildIds.value.includes(g.id))
)

function toggleAllOtherGuilds(e) {
  selectedGuildIds.value = e.target.checked ? copyTargetGuilds.value.map(g => g.id) : []
}

function toggleAllCopyGuilds(e) {
  copyGuildIds.value = e.target.checked ? otherGuilds.value.map(g => g.id) : []
}

let isActive = true
let loadVersion = 0

onUnmounted(() => { isActive = false })

async function loadData() {
  if (!guildStore.currentGuild || !isActive) return
  const version = ++loadVersion
  loading.value = true
  error.value = null
  noGuild.value = false
  try {
    const [seriesData, templatesData] = await Promise.all([
      seriesApi.getSeries(guildStore.currentGuild.id),
      templatesApi.getTemplates(guildStore.currentGuild.id)
    ])
    if (version === loadVersion && isActive) {
      seriesList.value = seriesData
      templates.value = templatesData
    }
  } catch {
    if (version === loadVersion && isActive) error.value = 'Failed to load recurring raids'
  } finally {
    if (version === loadVersion && isActive) loading.value = false
  }
}

onMounted(async () => {
  if (!guildStore.currentGuild) await guildStore.fetchGuilds()
  if (!guildStore.currentGuild) {
    noGuild.value = true
    loading.value = false
    return
  }
  loadData()
})

// Reload when guild changes in sidebar
watch(() => guildStore.currentGuild?.id, (newId, oldId) => {
  if (newId && newId !== oldId) loadData()
})

function formatRecurrence(rule) {
  if (!rule) return ''
  if (rule.toLowerCase().includes('biweekly')) return 'Every 2 weeks'
  if (rule.toLowerCase().includes('weekly')) return 'Every week'
  return rule
}

function onTemplateChange() {
  if (!form.template_id) return
  const tpl = templates.value.find(t => t.id === form.template_id)
  if (tpl) {
    form.default_raid_size = tpl.raid_size ?? form.default_raid_size
    form.default_difficulty = tpl.difficulty ?? form.default_difficulty
    form.duration_minutes = tpl.expected_duration_minutes ?? form.duration_minutes
    if (!form.title && tpl.name) form.title = tpl.name
  }
}

function templateName(tplId) {
  const t = templates.value.find(t => t.id === tplId)
  return t ? t.name : `Template #${tplId}`
}

function openAddModal() {
  editing.value = null
  selectedGuildId.value = guildStore.currentGuild?.id ?? null
  Object.assign(form, {
    title: '',
    recurrence_rule: 'weekly', start_time_local: '19:00',
    duration_minutes: 180, default_raid_size: 25, default_difficulty: 'normal',
    template_id: null
  })
  applyToOtherGuilds.value = false
  selectedGuildIds.value = []
  formError.value = null; showModal.value = true
}

function openEditModal(s) {
  editing.value = s
  selectedGuildId.value = s.guild_id ?? guildStore.currentGuild?.id ?? null
  Object.assign(form, {
    title: s.title,
    recurrence_rule: s.recurrence_rule ?? 'weekly',
    start_time_local: s.start_time_local ?? '19:00',
    duration_minutes: s.duration_minutes ?? 180,
    default_raid_size: s.default_raid_size ?? 25,
    default_difficulty: s.default_difficulty ?? 'normal',
    template_id: s.template_id ?? null
  })
  formError.value = null; showModal.value = true
}

function openGenerate(s) {
  generateTarget.value = s
  generateCount.value = 4
  generateResult.value = null
  showGenerate.value = true
}

function confirmDelete(s) { deleteTarget.value = s; showDeleteConfirm.value = true }

function openCopyModal(s) {
  copySource.value = s
  copyGuildIds.value = []
  showCopyModal.value = true
}

async function saveSeries() {
  formError.value = null
  if (!form.title) { formError.value = 'Title is required'; return }

  // Check if multi-guild is checked but no guilds selected
  if (!editing.value && applyToOtherGuilds.value && selectedGuildIds.value.length === 0) {
    showNoGuildConfirm.value = true
    return
  }

  await doSave()
}

function goBackToForm() {
  showNoGuildConfirm.value = false
}

async function confirmSaveCurrentOnly() {
  showNoGuildConfirm.value = false
  applyToOtherGuilds.value = false
  await doSave()
}

async function doSave() {
  const targetGuildId = selectedGuildId.value || guildStore.currentGuild.id
  const targetGuild = guildStore.guilds.find(g => g.id === targetGuildId)
  if (!targetGuild) { formError.value = 'Please select a guild'; return }
  saving.value = true
  // Derive realm_name from selected guild
  const payload = { ...form, realm_name: targetGuild.realm_name ?? '' }
  try {
    if (editing.value) {
      const updated = await seriesApi.updateSeries(targetGuildId, editing.value.id, payload)
      const idx = seriesList.value.findIndex(s => s.id === editing.value.id)
      if (idx !== -1) seriesList.value[idx] = updated
    } else {
      const created = await seriesApi.createSeries(targetGuildId, payload)
      if (targetGuildId === guildStore.currentGuild?.id) {
        seriesList.value.push(created)
      }
      // Also create in other selected guilds
      if (applyToOtherGuilds.value && selectedGuildIds.value.length > 0) {
        let failed = 0
        for (const guildId of selectedGuildIds.value) {
          const otherGuild = guildStore.guilds.find(g => g.id === guildId)
          const otherPayload = { ...form, realm_name: otherGuild?.realm_name ?? '' }
          try { await seriesApi.createSeries(guildId, otherPayload) } catch { failed++ }
        }
        if (failed > 0) uiStore.showToast(`Failed to create in ${failed} guild(s)`, 'warning')
      }
    }
    showModal.value = false
    const guildLabel = targetGuild ? `${targetGuild.name} (${targetGuild.realm_name})` : ''
    uiStore.showToast(editing.value ? 'Series updated' : `Series created in ${guildLabel}`, 'success')
    // Switch to target guild if different from current (only for single-guild creation, not multi-guild copy)
    if (!editing.value && targetGuildId !== guildStore.currentGuild?.id && !applyToOtherGuilds.value) {
      guildStore.setCurrentGuild(targetGuild)
    }
  } catch (err) {
    formError.value = err?.response?.data?.error ?? err?.response?.data?.message ?? 'Failed to save'
  } finally { saving.value = false }
}

async function doGenerate() {
  if (!generateTarget.value) return
  saving.value = true
  generateResult.value = null
  try {
    const events = await seriesApi.generateEvents(guildStore.currentGuild.id, generateTarget.value.id, { count: generateCount.value })
    generateResult.value = Array.isArray(events) ? events.length : generateCount.value
    uiStore.showToast(`${generateResult.value} event(s) generated!`, 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? err?.response?.data?.message ?? 'Failed to generate events', 'error')
  } finally { saving.value = false }
}

async function doDelete() {
  saving.value = true
  try {
    await seriesApi.deleteSeries(guildStore.currentGuild.id, deleteTarget.value.id)
    seriesList.value = seriesList.value.filter(s => s.id !== deleteTarget.value.id)
    showDeleteConfirm.value = false
    uiStore.showToast('Series deleted', 'success')
  } catch { uiStore.showToast('Failed to delete', 'error') }
  finally { saving.value = false }
}

async function doCopy() {
  if (copyGuildIds.value.length === 0) return
  saving.value = true
  let succeeded = 0, failed = 0
  for (const guildId of copyGuildIds.value) {
    try {
      await seriesApi.copySeries(guildId, copySource.value.id)
      succeeded++
    } catch { failed++ }
  }
  showCopyModal.value = false
  if (failed > 0) {
    uiStore.showToast(`Copied to ${succeeded} guild(s), failed in ${failed}`, 'warning')
  } else {
    uiStore.showToast(`"${copySource.value.title}" copied to ${succeeded} guild(s)`, 'success')
  }
  saving.value = false
}
</script>
