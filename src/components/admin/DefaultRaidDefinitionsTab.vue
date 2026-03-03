<template>
  <div class="space-y-6">
    <WowCard>
      <div class="flex items-center justify-between mb-4">
        <h2 class="wow-heading text-base">{{ t('admin.raidDefinitions.title', { count: definitions.length }) }}</h2>
        <WowButton @click="openCreateModal">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          {{ t('admin.raidDefinitions.newDefinition') }}
        </WowButton>
      </div>

      <div v-if="loading" class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-bg-tertiary border-b border-border-default">
              <th class="hidden sm:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.users.id') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.raidDefinitions.name') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.raidDefinitions.code') }}</th>
              <th class="hidden md:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.raidDefinitions.raidSize') }}</th>
              <th class="hidden md:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.raidDefinitions.duration') }}</th>
              <th class="hidden lg:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.raidDefinitions.modes') }}</th>
              <th class="text-right px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.labels.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-default">
            <tr v-for="d in definitions" :key="d.id" class="hover:bg-bg-tertiary/50 transition-colors">
              <td class="hidden sm:table-cell px-4 py-2.5 text-text-muted">{{ d.id }}</td>
              <td class="px-4 py-2.5">
                <div class="text-text-primary font-medium">{{ d.name }}</div>
                <div class="text-xs text-text-muted">{{ d.expansion }}</div>
              </td>
              <td class="px-4 py-2.5 text-text-muted font-mono text-xs">{{ d.code }}</td>
              <td class="hidden md:table-cell px-4 py-2.5 text-text-muted">{{ d.default_raid_size }}</td>
              <td class="hidden md:table-cell px-4 py-2.5 text-text-muted">{{ d.default_duration_minutes }}m</td>
              <td class="hidden lg:table-cell px-4 py-2.5">
                <div class="flex gap-1 flex-wrap">
                  <span v-if="d.supports_10" class="text-[10px] px-1.5 py-0.5 rounded bg-blue-900/50 text-blue-300 border border-blue-600">10</span>
                  <span v-if="d.supports_25" class="text-[10px] px-1.5 py-0.5 rounded bg-green-900/50 text-green-300 border border-green-600">25</span>
                  <span v-if="d.supports_heroic" class="text-[10px] px-1.5 py-0.5 rounded bg-orange-900/50 text-orange-300 border border-orange-600">HC</span>
                </div>
              </td>
              <td class="px-4 py-2.5 text-right">
                <div class="flex gap-1 justify-end">
                  <WowButton variant="secondary" class="text-xs py-1 px-2" @click="openEditModal(d)">{{ t('common.buttons.edit') }}</WowButton>
                  <WowButton variant="danger" class="text-xs py-1 px-2" @click="confirmDelete(d)">{{ t('common.buttons.delete') }}</WowButton>
                </div>
              </td>
            </tr>
            <tr v-if="!definitions.length">
              <td colspan="7" class="px-4 py-8 text-center text-text-muted">{{ t('admin.raidDefinitions.noDefinitions') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </WowCard>

    <!-- Create / Edit Modal -->
    <WowModal v-model="showEditModal" :title="editingDef ? t('admin.raidDefinitions.editDefinition') : t('admin.raidDefinitions.newDefinition')" size="lg">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="text-xs text-text-muted block mb-1">{{ t('admin.raidDefinitions.name') }}</label>
          <input v-model="form.name" type="text" class="w-full bg-bg-secondary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-accent-gold focus:outline-none" />
        </div>
        <div>
          <label class="text-xs text-text-muted block mb-1">{{ t('admin.raidDefinitions.code') }}</label>
          <input v-model="form.code" type="text" class="w-full bg-bg-secondary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-accent-gold focus:outline-none font-mono" />
        </div>
        <div>
          <label class="text-xs text-text-muted block mb-1">{{ t('admin.raidDefinitions.raidSize') }}</label>
          <input v-model.number="form.default_raid_size" type="number" min="1" max="40" class="w-full bg-bg-secondary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-accent-gold focus:outline-none" />
        </div>
        <div>
          <label class="text-xs text-text-muted block mb-1">{{ t('admin.raidDefinitions.duration') }}</label>
          <input v-model.number="form.default_duration_minutes" type="number" min="1" class="w-full bg-bg-secondary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-accent-gold focus:outline-none" />
        </div>
        <div class="sm:col-span-2 flex gap-4">
          <label class="inline-flex items-center gap-2 text-sm text-text-muted cursor-pointer">
            <input v-model="form.supports_10" type="checkbox" class="accent-accent-gold" /> 10-man
          </label>
          <label class="inline-flex items-center gap-2 text-sm text-text-muted cursor-pointer">
            <input v-model="form.supports_25" type="checkbox" class="accent-accent-gold" /> 25-man
          </label>
          <label class="inline-flex items-center gap-2 text-sm text-text-muted cursor-pointer">
            <input v-model="form.supports_heroic" type="checkbox" class="accent-accent-gold" /> Heroic
          </label>
        </div>
        <div class="sm:col-span-2">
          <label class="text-xs text-text-muted block mb-1">{{ t('admin.raidDefinitions.notes') }}</label>
          <textarea v-model="form.notes" rows="2" class="w-full bg-bg-secondary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-accent-gold focus:outline-none" />
        </div>
      </div>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <WowButton variant="secondary" @click="showEditModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="primary" :disabled="!form.name" @click="saveDefinition">{{ t('common.buttons.save') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Delete Confirmation -->
    <WowModal v-model="showDeleteModal" :title="t('admin.raidDefinitions.deleteDefinition')" size="sm">
      <p class="text-text-muted text-sm">
        {{ t('admin.raidDefinitions.deleteConfirm', { name: deleteTarget?.name }) }}
      </p>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <WowButton variant="secondary" @click="showDeleteModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="danger" @click="doDelete">{{ t('common.buttons.delete') }}</WowButton>
        </div>
      </template>
    </WowModal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import { useUiStore } from '@/stores/ui'
import * as rdApi from '@/api/raidDefinitions'

const { t } = useI18n()
const uiStore = useUiStore()

const definitions = ref([])
const loading = ref(true)
const error = ref(null)

const showEditModal = ref(false)
const editingDef = ref(null)
const form = ref(defaultForm())

const showDeleteModal = ref(false)
const deleteTarget = ref(null)

function defaultForm() {
  return { name: '', code: '', default_raid_size: 25, default_duration_minutes: 180, supports_10: true, supports_25: true, supports_heroic: false, notes: '' }
}

async function loadDefinitions() {
  loading.value = true
  try {
    definitions.value = await rdApi.adminGetDefaultDefinitions()
  } catch (err) {
    error.value = err?.response?.data?.error ?? t('admin.raidDefinitions.loadError')
  } finally {
    loading.value = false
  }
}

onMounted(loadDefinitions)

function openCreateModal() {
  editingDef.value = null
  form.value = defaultForm()
  showEditModal.value = true
}

function openEditModal(d) {
  editingDef.value = d
  form.value = {
    name: d.name,
    code: d.code,
    default_raid_size: d.default_raid_size,
    default_duration_minutes: d.default_duration_minutes,
    supports_10: d.supports_10,
    supports_25: d.supports_25,
    supports_heroic: d.supports_heroic,
    notes: d.notes || '',
  }
  showEditModal.value = true
}

async function saveDefinition() {
  const size = form.value.default_raid_size
  if (!size || size < 1 || size > 40) {
    uiStore.showToast('Raid size must be between 1 and 40', 'error')
    return
  }
  try {
    if (editingDef.value) {
      await rdApi.adminUpdateDefaultDefinition(editingDef.value.id, form.value)
      uiStore.showToast(t('admin.raidDefinitions.updated'))
    } else {
      await rdApi.adminCreateDefaultDefinition(form.value)
      uiStore.showToast(t('admin.raidDefinitions.created'))
    }
    showEditModal.value = false
    await loadDefinitions()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('admin.raidDefinitions.loadError'), 'error')
  }
}

function confirmDelete(d) {
  deleteTarget.value = d
  showDeleteModal.value = true
}

async function doDelete() {
  try {
    await rdApi.adminDeleteDefaultDefinition(deleteTarget.value.id)
    showDeleteModal.value = false
    uiStore.showToast(t('admin.raidDefinitions.deleted'))
    await loadDefinitions()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('admin.raidDefinitions.loadError'), 'error')
  }
}
</script>
