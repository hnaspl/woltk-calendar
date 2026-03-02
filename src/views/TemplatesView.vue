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
          <h1 class="wow-heading text-xl sm:text-2xl">{{ t('templates.title') }}</h1>
          <p class="text-text-muted text-sm mt-0.5">{{ t('templates.subtitle') }}</p>
        </div>
        <WowButton @click="openAddModal">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          {{ t('templates.newTemplate') }}
        </WowButton>
      </div>

      <div v-if="loading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="h-20 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      </div>
      <div v-else-if="noGuild" class="p-4 rounded-lg bg-blue-900/30 border border-blue-600 text-blue-300">
        {{ t('templates.noGuild') }}
      </div>
      <div v-else-if="error" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">{{ error }}</div>
      <div v-else-if="templates.length === 0" class="text-center py-12 text-text-muted">
        {{ t('templates.noTemplates') }}
      </div>
      <div v-else class="space-y-3">
        <WowCard v-for="tpl in templates" :key="tpl.id">
          <div class="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4">
            <div class="w-12 h-12 rounded border border-border-default bg-bg-tertiary flex items-center justify-center text-xl flex-shrink-0">📋</div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-bold text-text-primary">{{ tpl.name }}</span>
                <RaidSizeBadge v-if="tpl.raid_size" :size="tpl.raid_size" />
                <span v-if="tpl.difficulty === 'heroic'" class="text-xs px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-300 border border-orange-600">Heroic</span>
              </div>
              <div class="text-xs text-text-muted mt-1">{{ tpl.default_instructions ?? t('templates.noInstructions') }}</div>
            </div>
            <div class="flex items-center gap-2 flex-wrap">
              <WowButton v-if="hasMultipleGuilds" variant="secondary" class="text-xs py-1.5" @click="openCopyModal(tpl)">
                📋 {{ t('common.buttons.copy') }}
              </WowButton>
              <WowButton variant="secondary" class="text-xs py-1.5" @click="openApply(tpl)">
                {{ t('common.buttons.apply') }}
              </WowButton>
              <WowButton variant="secondary" class="text-xs py-1.5" @click="openEditModal(tpl)">
                {{ t('common.buttons.edit') }}
              </WowButton>
              <WowButton variant="danger" class="text-xs py-1.5 px-2" @click="confirmDelete(tpl)">✕</WowButton>
            </div>
          </div>
        </WowCard>
      </div>
      </template>
    </div>

    <!-- Add/Edit template modal -->
    <WowModal v-model="showModal" :title="editing ? t('templates.editTemplate') : t('templates.newTemplateTitle')" size="md">
      <form @submit.prevent="saveTemplate" class="space-y-4">
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('templates.templateName') }}</label>
          <input v-model="form.name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('templates.raidDefinition') }}</label>
          <select v-model.number="form.raid_definition_id" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option value="">{{ t('templates.selectRaid') }}</option>
            <option v-for="d in raidDefinitions" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
          <p v-if="raidDefinitions.length === 0" class="text-xs text-text-muted mt-1">{{ t('templates.noRaidDefs') }}</p>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('templates.raidSize') }}</label>
            <select v-model.number="form.raid_size" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option :value="10">{{ t('calendar.tenMan') }}</option>
              <option :value="25">{{ t('calendar.twentyFiveMan') }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('calendar.difficulty') }}</label>
            <select v-model="form.difficulty" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="normal">{{ t('calendar.normal') }}</option>
              <option value="heroic">{{ t('calendar.heroic') }}</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('calendar.instructions') }}</label>
          <textarea v-model="form.default_instructions" rows="2" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none resize-none" />
        </div>
        <div v-if="formError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ formError }}</div>
        <!-- Multi-guild creation -->
        <div v-if="!editing && otherGuilds.length > 0" class="p-3 rounded bg-bg-tertiary border border-border-default">
          <label class="flex items-center gap-2 cursor-pointer">
            <input v-model="applyToOtherGuilds" type="checkbox" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
            <span class="text-sm text-text-primary">{{ t('common.copy.copyToOther') }}</span>
          </label>
          <div v-if="applyToOtherGuilds" class="mt-2 space-y-1 pl-6">
            <label class="flex items-center gap-2 cursor-pointer mb-1">
              <input type="checkbox" :checked="allOtherGuildsSelected" @change="toggleAllOtherGuilds" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
              <span class="text-xs text-accent-gold font-semibold">{{ t('common.copy.copyToAll') }}</span>
            </label>
            <label v-for="g in otherGuilds" :key="g.id" class="flex items-center gap-2 cursor-pointer">
              <input v-model="selectedGuildIds" :value="g.id" type="checkbox" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
              <span class="text-xs text-text-muted">{{ g.name }} <span class="text-text-muted/60">({{ g.realm_name }})</span></span>
            </label>
          </div>
        </div>
      </form>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton :loading="saving" @click="saveTemplate">{{ editing ? t('common.buttons.save') : t('common.buttons.create') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Copy to Guild modal -->
    <WowModal v-model="showCopyModal" :title="t('templates.copyTemplateToGuilds')" size="sm">
      <p class="text-text-muted text-sm mb-3">Copy <strong class="text-text-primary">{{ copySource?.name }}</strong> to selected guilds:</p>
      <div class="space-y-1">
        <label class="flex items-center gap-2 cursor-pointer mb-1">
          <input type="checkbox" :checked="allCopyGuildsSelected" @change="toggleAllCopyGuilds" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
          <span class="text-xs text-accent-gold font-semibold">{{ t('common.copy.copyToAll') }}</span>
        </label>
        <label v-for="g in otherGuilds" :key="g.id" class="flex items-center gap-2 cursor-pointer">
          <input v-model="copyGuildIds" :value="g.id" type="checkbox" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
          <span class="text-xs text-text-muted">{{ g.name }} <span class="text-text-muted/60">({{ g.realm_name }})</span></span>
        </label>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showCopyModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton :loading="saving" @click="doCopy" :disabled="copyGuildIds.length === 0">{{ t('common.buttons.copy') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Confirmation modal for no guilds selected -->
    <WowModal v-model="showNoGuildConfirm" :title="t('common.copy.noAdditionalGuilds')" size="sm">
      <p class="text-text-muted text-sm">{{ t('common.copy.onlyCreatedIn') }} <strong class="text-text-primary">{{ currentGuildLabel }}</strong>. {{ t('common.copy.goBackQuestion') }}</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="goBackToForm">{{ t('common.buttons.goBack') }}</WowButton>
          <WowButton @click="confirmSaveCurrentOnly">{{ t('common.buttons.continue') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Apply template modal -->
    <WowModal v-model="showApply" :title="t('templates.applyTemplate')" size="sm">
      <div class="space-y-4">
        <p class="text-text-muted text-sm">Schedule a new event from template <strong class="text-text-primary">{{ applyTarget?.name }}</strong>.</p>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('calendar.startDateTime') }}</label>
          <input v-model="applyDate" type="datetime-local" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showApply = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton :loading="saving" @click="doApply">{{ t('common.buttons.schedule') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Delete confirmation -->
    <WowModal v-model="showDeleteConfirm" :title="t('templates.deleteTemplate')" size="sm">
      <p class="text-text-muted">{{ t('templates.deleteTemplateConfirm') }} <strong class="text-text-primary">{{ deleteTarget?.name }}</strong>?</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showDeleteConfirm = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="danger" :loading="saving" @click="doDelete">{{ t('common.buttons.delete') }}</WowButton>
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
import { useGuildStore } from '@/stores/guild'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { usePermissions } from '@/composables/usePermissions'
import { useTimezone } from '@/composables/useTimezone'
import * as templatesApi from '@/api/templates'
import * as raidDefsApi from '@/api/raidDefinitions'
import { useI18n } from 'vue-i18n'

const guildStore = useGuildStore()
const authStore = useAuthStore()
const uiStore = useUiStore()
const permissions = usePermissions()
const tzHelper = useTimezone()
const { t } = useI18n()

const hasViewAccess = computed(() => permissions.can('create_events') || permissions.can('manage_templates'))
const hasMultipleGuilds = computed(() => guildStore.guilds.length > 1)

const templates = ref([])
const raidDefinitions = ref([])
const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const noGuild = ref(false)
const formError = ref(null)
const showModal = ref(false)
const showApply = ref(false)
const showDeleteConfirm = ref(false)
const showCopyModal = ref(false)
const showNoGuildConfirm = ref(false)
const editing = ref(null)
const applyTarget = ref(null)
const deleteTarget = ref(null)
const copySource = ref(null)
const applyDate = ref('')

const form = reactive({ name: '', raid_definition_id: '', raid_size: 25, difficulty: 'normal', default_instructions: '' })
const applyToOtherGuilds = ref(false)
const selectedGuildIds = ref([])
const copyGuildIds = ref([])

const otherGuilds = computed(() =>
  guildStore.guilds.filter(g => g.id !== guildStore.currentGuild?.id)
)

const currentGuildLabel = computed(() => {
  const g = guildStore.currentGuild
  return g ? `${g.name} (${g.realm_name})` : ''
})

const allOtherGuildsSelected = computed(() =>
  otherGuilds.value.length > 0 && otherGuilds.value.every(g => selectedGuildIds.value.includes(g.id))
)

const allCopyGuildsSelected = computed(() =>
  otherGuilds.value.length > 0 && otherGuilds.value.every(g => copyGuildIds.value.includes(g.id))
)

function toggleAllOtherGuilds(e) {
  selectedGuildIds.value = e.target.checked ? otherGuilds.value.map(g => g.id) : []
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
    const [tpls, defs] = await Promise.all([
      templatesApi.getTemplates(guildStore.currentGuild.id),
      raidDefsApi.getRaidDefinitions(guildStore.currentGuild.id)
    ])
    if (version === loadVersion && isActive) {
      templates.value = tpls
      raidDefinitions.value = defs
    }
  } catch {
    if (version === loadVersion && isActive) error.value = t('templates.failedToLoad')
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

function openAddModal() {
  editing.value = null
  Object.assign(form, { name: '', raid_definition_id: '', raid_size: 25, difficulty: 'normal', default_instructions: '' })
  applyToOtherGuilds.value = false
  selectedGuildIds.value = []
  formError.value = null; showModal.value = true
}

function openEditModal(tpl) {
  editing.value = tpl
  Object.assign(form, { name: tpl.name, raid_definition_id: tpl.raid_definition_id ?? '', raid_size: tpl.raid_size ?? 25, difficulty: tpl.difficulty ?? 'normal', default_instructions: tpl.default_instructions ?? '' })
  formError.value = null; showModal.value = true
}

function openApply(tpl) { applyTarget.value = tpl; applyDate.value = ''; showApply.value = true }
function confirmDelete(tpl) { deleteTarget.value = tpl; showDeleteConfirm.value = true }

function openCopyModal(tpl) {
  copySource.value = tpl
  copyGuildIds.value = []
  showCopyModal.value = true
}

async function saveTemplate() {
  formError.value = null
  if (!form.name || !form.raid_definition_id) { formError.value = t('templates.toasts.nameRaidDefRequired'); return }

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
  saving.value = true
  const payload = {
    name: form.name,
    raid_definition_id: form.raid_definition_id,
    raid_size: form.raid_size,
    difficulty: form.difficulty,
    default_instructions: form.default_instructions || undefined
  }
  try {
    if (editing.value) {
      const updated = await templatesApi.updateTemplate(guildStore.currentGuild.id, editing.value.id, payload)
      const idx = templates.value.findIndex(t => t.id === editing.value.id)
      if (idx !== -1) templates.value[idx] = updated
    } else {
      templates.value.push(await templatesApi.createTemplate(guildStore.currentGuild.id, payload))
      // Also create in other selected guilds
      if (applyToOtherGuilds.value && selectedGuildIds.value.length > 0) {
        let failed = 0
        for (const guildId of selectedGuildIds.value) {
          try { await templatesApi.createTemplate(guildId, payload) } catch { failed++ }
        }
        if (failed > 0) uiStore.showToast(t('common.copy.failedToCreateInGuilds', { count: failed }), 'warning')
      }
    }
    showModal.value = false
    const guildLabel = currentGuildLabel.value
    uiStore.showToast(editing.value ? t('templates.toasts.templateUpdated') : t('templates.toasts.templateCreated', { guild: guildLabel }), 'success')
  } catch (err) {
    formError.value = err?.response?.data?.message ?? 'Failed to save'
  } finally { saving.value = false }
}

async function doApply() {
  if (!applyDate.value) return
  saving.value = true
  try {
    await templatesApi.applyTemplate(guildStore.currentGuild.id, applyTarget.value.id, { start_time: tzHelper.guildLocalToUtc(applyDate.value) })
    showApply.value = false
    uiStore.showToast(t('templates.eventScheduled'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.message ?? t('templates.toasts.failedToApply'), 'error')
  } finally { saving.value = false }
}

async function doDelete() {
  saving.value = true
  try {
    await templatesApi.deleteTemplate(guildStore.currentGuild.id, deleteTarget.value.id)
    templates.value = templates.value.filter(t => t.id !== deleteTarget.value.id)
    showDeleteConfirm.value = false
    uiStore.showToast(t('templates.templateDeleted'), 'success')
  } catch { uiStore.showToast(t('templates.failedToDelete'), 'error') }
  finally { saving.value = false }
}

async function doCopy() {
  if (copyGuildIds.value.length === 0) return
  saving.value = true
  let succeeded = 0, failed = 0
  for (const guildId of copyGuildIds.value) {
    try {
      await templatesApi.copyTemplate(guildId, copySource.value.id)
      succeeded++
    } catch { failed++ }
  }
  showCopyModal.value = false
  if (failed > 0) {
    uiStore.showToast(t('common.copy.copiedWithFailures', { succeeded, failed }), 'warning')
  } else {
    uiStore.showToast(t('common.copy.copiedSuccess', { name: copySource.value.name, count: succeeded }), 'success')
  }
  saving.value = false
}
</script>
