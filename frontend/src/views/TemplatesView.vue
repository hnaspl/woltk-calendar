<template>
  <AppShell>
    <div class="p-4 md:p-6 space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="wow-heading text-2xl">Raid Templates</h1>
          <p class="text-text-muted text-sm mt-0.5">Save recurring raid schedules as templates</p>
        </div>
        <WowButton @click="openAddModal">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          New Template
        </WowButton>
      </div>

      <div v-if="loading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="h-20 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      </div>
      <div v-else-if="error" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">{{ error }}</div>
      <div v-else-if="templates.length === 0" class="text-center py-12 text-text-muted">
        No templates yet. Create a template to quickly schedule recurring raids.
      </div>
      <div v-else class="space-y-3">
        <WowCard v-for="tpl in templates" :key="tpl.id">
          <div class="flex items-center gap-4">
            <img :src="getRaidIcon(tpl.raid_type)" :alt="tpl.raid_type" class="w-12 h-12 rounded border border-border-default flex-shrink-0" />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-bold text-text-primary">{{ tpl.name }}</span>
                <RaidSizeBadge v-if="tpl.size" :size="tpl.size" />
                <RealmBadge v-if="tpl.realm" :realm="tpl.realm" />
              </div>
              <div class="text-xs text-text-muted mt-1">{{ tpl.description ?? 'No description' }}</div>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <WowButton variant="secondary" class="text-xs py-1.5" @click="openApply(tpl)">
                Apply
              </WowButton>
              <WowButton variant="secondary" class="text-xs py-1.5" @click="openEditModal(tpl)">
                Edit
              </WowButton>
              <WowButton variant="danger" class="text-xs py-1.5 px-2" @click="confirmDelete(tpl)">✕</WowButton>
            </div>
          </div>
        </WowCard>
      </div>
    </div>

    <!-- Add/Edit template modal -->
    <WowModal v-model="showModal" :title="editing ? 'Edit Template' : 'New Template'" size="md">
      <form @submit.prevent="saveTemplate" class="space-y-4">
        <div>
          <label class="block text-xs text-text-muted mb-1">Template Name *</label>
          <input v-model="form.name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">Raid Type *</label>
            <select v-model="form.raid_type" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="">Select…</option>
              <option v-for="r in raidTypes" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Size</label>
            <select v-model.number="form.size" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="">Select…</option>
              <option :value="10">10-man</option>
              <option :value="25">25-man</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Realm</label>
          <input v-model="form.realm" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Description</label>
          <textarea v-model="form.description" rows="2" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none resize-none" />
        </div>
        <div v-if="formError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ formError }}</div>
      </form>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showModal = false">Cancel</WowButton>
          <WowButton :loading="saving" @click="saveTemplate">{{ editing ? 'Save' : 'Create' }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Apply template modal -->
    <WowModal v-model="showApply" title="Apply Template" size="sm">
      <div class="space-y-4">
        <p class="text-text-muted text-sm">Schedule a new event from template <strong class="text-text-primary">{{ applyTarget?.name }}</strong>.</p>
        <div>
          <label class="block text-xs text-text-muted mb-1">Event Date & Time *</label>
          <input v-model="applyDate" type="datetime-local" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showApply = false">Cancel</WowButton>
          <WowButton :loading="saving" @click="doApply">Schedule</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Delete confirmation -->
    <WowModal v-model="showDeleteConfirm" title="Delete Template" size="sm">
      <p class="text-text-muted">Delete template <strong class="text-text-primary">{{ deleteTarget?.name }}</strong>?</p>
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
import { ref, reactive, onMounted } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import RaidSizeBadge from '@/components/common/RaidSizeBadge.vue'
import RealmBadge from '@/components/common/RealmBadge.vue'
import { useGuildStore } from '@/stores/guild'
import { useUiStore } from '@/stores/ui'
import { useWowIcons } from '@/composables/useWowIcons'
import * as templatesApi from '@/api/templates'

const guildStore = useGuildStore()
const uiStore = useUiStore()
const { getRaidIcon } = useWowIcons()

const templates = ref([])
const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const formError = ref(null)
const showModal = ref(false)
const showApply = ref(false)
const showDeleteConfirm = ref(false)
const editing = ref(null)
const applyTarget = ref(null)
const deleteTarget = ref(null)
const applyDate = ref('')

const raidTypes = [
  { value: 'naxx', label: 'Naxxramas' }, { value: 'os', label: 'Obsidian Sanctum' },
  { value: 'eoe', label: 'Eye of Eternity' }, { value: 'voa', label: 'Vault of Archavon' },
  { value: 'ulduar', label: 'Ulduar' }, { value: 'toc', label: 'Trial of the Crusader' },
  { value: 'icc', label: 'Icecrown Citadel' }, { value: 'rs', label: 'Ruby Sanctum' }
]

const form = reactive({ name: '', raid_type: '', size: '', realm: '', description: '' })

onMounted(async () => {
  loading.value = true
  if (!guildStore.currentGuild) await guildStore.fetchGuilds()
  try {
    templates.value = await templatesApi.getTemplates(guildStore.currentGuild.id)
  } catch { error.value = 'Failed to load templates' }
  finally { loading.value = false }
})

function openAddModal() {
  editing.value = null
  Object.assign(form, { name: '', raid_type: '', size: '', realm: '', description: '' })
  formError.value = null; showModal.value = true
}

function openEditModal(tpl) {
  editing.value = tpl
  Object.assign(form, { name: tpl.name, raid_type: tpl.raid_type, size: tpl.size ?? '', realm: tpl.realm ?? '', description: tpl.description ?? '' })
  formError.value = null; showModal.value = true
}

function openApply(tpl) { applyTarget.value = tpl; applyDate.value = ''; showApply.value = true }
function confirmDelete(tpl) { deleteTarget.value = tpl; showDeleteConfirm.value = true }

async function saveTemplate() {
  formError.value = null
  if (!form.name || !form.raid_type) { formError.value = 'Name and raid type are required'; return }
  saving.value = true
  try {
    if (editing.value) {
      const updated = await templatesApi.updateTemplate(guildStore.currentGuild.id, editing.value.id, form)
      const idx = templates.value.findIndex(t => t.id === editing.value.id)
      if (idx !== -1) templates.value[idx] = updated
    } else {
      templates.value.push(await templatesApi.createTemplate(guildStore.currentGuild.id, form))
    }
    showModal.value = false
    uiStore.showToast(editing.value ? 'Template updated' : 'Template created', 'success')
  } catch (err) {
    formError.value = err?.response?.data?.message ?? 'Failed to save'
  } finally { saving.value = false }
}

async function doApply() {
  if (!applyDate.value) return
  saving.value = true
  try {
    await templatesApi.applyTemplate(guildStore.currentGuild.id, applyTarget.value.id, { start_time: applyDate.value })
    showApply.value = false
    uiStore.showToast('Event scheduled from template!', 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.message ?? 'Failed to apply template', 'error')
  } finally { saving.value = false }
}

async function doDelete() {
  saving.value = true
  try {
    await templatesApi.deleteTemplate(guildStore.currentGuild.id, deleteTarget.value.id)
    templates.value = templates.value.filter(t => t.id !== deleteTarget.value.id)
    showDeleteConfirm.value = false
    uiStore.showToast('Template deleted', 'success')
  } catch { uiStore.showToast('Failed to delete', 'error') }
  finally { saving.value = false }
}
</script>
