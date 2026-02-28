<template>
  <AppShell>
    <div class="p-4 md:p-6 space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="wow-heading text-2xl">Recurring Raids</h1>
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
          <div class="flex items-center gap-4">
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
            <div class="flex items-center gap-2 flex-shrink-0">
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
          <label class="block text-xs text-text-muted mb-1">Realm *</label>
          <select v-model="form.realm_name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option value="">Select realm…</option>
            <option v-for="r in guildRealms" :key="r" :value="r">{{ r }}</option>
          </select>
        </div>
        <div class="grid grid-cols-2 gap-4">
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
        <div class="grid grid-cols-3 gap-4">
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
      </form>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showModal = false">Cancel</WowButton>
          <WowButton :loading="saving" @click="saveSeries">{{ editing ? 'Save' : 'Create' }}</WowButton>
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
import { ref, reactive, computed, onMounted } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import RaidSizeBadge from '@/components/common/RaidSizeBadge.vue'
import RealmBadge from '@/components/common/RealmBadge.vue'
import { useGuildStore } from '@/stores/guild'
import { useUiStore } from '@/stores/ui'
import * as seriesApi from '@/api/series'
import * as templatesApi from '@/api/templates'

const guildStore = useGuildStore()
const uiStore = useUiStore()

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
const editing = ref(null)
const generateTarget = ref(null)
const generateCount = ref(4)
const generateResult = ref(null)
const deleteTarget = ref(null)

const guildRealms = computed(() => {
  const realms = new Set(guildStore.guilds.map(g => g.realm_name).filter(Boolean))
  return [...realms].sort()
})

const form = reactive({
  title: '',
  realm_name: '',
  recurrence_rule: 'weekly',
  start_time_local: '19:00',
  duration_minutes: 180,
  default_raid_size: 25,
  default_difficulty: 'normal',
  template_id: null
})

onMounted(async () => {
  loading.value = true
  if (!guildStore.currentGuild) await guildStore.fetchGuilds()
  if (!guildStore.currentGuild) {
    error.value = null
    noGuild.value = true
    loading.value = false
    return
  }
  try {
    const [seriesData, templatesData] = await Promise.all([
      seriesApi.getSeries(guildStore.currentGuild.id),
      templatesApi.getTemplates(guildStore.currentGuild.id)
    ])
    seriesList.value = seriesData
    templates.value = templatesData
  } catch { error.value = 'Failed to load recurring raids' }
  finally { loading.value = false }
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
  Object.assign(form, {
    title: '', realm_name: guildStore.currentGuild?.realm_name ?? '',
    recurrence_rule: 'weekly', start_time_local: '19:00',
    duration_minutes: 180, default_raid_size: 25, default_difficulty: 'normal',
    template_id: null
  })
  formError.value = null; showModal.value = true
}

function openEditModal(s) {
  editing.value = s
  Object.assign(form, {
    title: s.title, realm_name: s.realm_name ?? '',
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

async function saveSeries() {
  formError.value = null
  if (!form.title || !form.realm_name) { formError.value = 'Title and realm are required'; return }
  saving.value = true
  try {
    if (editing.value) {
      const updated = await seriesApi.updateSeries(guildStore.currentGuild.id, editing.value.id, form)
      const idx = seriesList.value.findIndex(s => s.id === editing.value.id)
      if (idx !== -1) seriesList.value[idx] = updated
    } else {
      seriesList.value.push(await seriesApi.createSeries(guildStore.currentGuild.id, form))
    }
    showModal.value = false
    uiStore.showToast(editing.value ? 'Series updated' : 'Series created', 'success')
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
</script>
