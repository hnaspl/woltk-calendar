<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
      <h2 class="wow-heading text-base">{{ t('admin.raidDefinitions.title', { count: definitions.length }) }}</h2>
      <WowButton @click="openCreateModal">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        {{ t('admin.raidDefinitions.newDefinition') }}
      </WowButton>
    </div>

    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div v-for="i in 4" :key="i" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
    </div>
    <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>
    <div v-else-if="definitions.length === 0" class="text-center py-12 text-text-muted">
      {{ t('admin.raidDefinitions.noDefinitions') }}
    </div>
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
      <WowCard v-for="d in definitions" :key="d.id">
        <div class="flex items-start gap-3 mb-3">
          <img :src="getRaidIcon(d.raid_type)" :alt="d.raid_type" class="w-10 h-10 sm:w-12 sm:h-12 rounded border border-border-default flex-shrink-0" />
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="font-bold text-text-primary truncate">{{ d.name }}</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-accent-gold/15 text-accent-gold border border-accent-gold/40">{{ t('raidDefinitions.default') }}</span>
            </div>
            <div class="flex items-center gap-1.5 mt-1">
              <RaidSizeBadge v-if="d.size" :size="d.size" />
            </div>
          </div>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 text-center text-xs mb-4">
          <div class="bg-blue-600/10 rounded p-1.5">
            <div class="text-blue-200 font-bold">{{ d.main_tank_slots ?? 1 }}</div>
            <div class="text-text-muted">Main Tank</div>
          </div>
          <div class="bg-cyan-500/10 rounded p-1.5">
            <div class="text-cyan-300 font-bold">{{ d.off_tank_slots ?? 1 }}</div>
            <div class="text-text-muted">Off Tank</div>
          </div>
          <div class="bg-blue-500/10 rounded p-1.5">
            <div class="text-blue-300 font-bold">{{ d.melee_dps_slots ?? 0 }}</div>
            <div class="text-text-muted">Melee DPS</div>
          </div>
          <div class="bg-green-500/10 rounded p-1.5">
            <div class="text-green-300 font-bold">{{ d.healer_slots ?? 5 }}</div>
            <div class="text-text-muted">Heal</div>
          </div>
          <div class="bg-red-500/10 rounded p-1.5">
            <div class="text-red-300 font-bold">{{ d.range_dps_slots ?? 18 }}</div>
            <div class="text-text-muted">Range DPS</div>
          </div>
        </div>
        <div class="flex flex-wrap gap-1.5 sm:gap-2">
          <WowButton variant="secondary" class="flex-1 text-xs py-1.5" @click="openEditModal(d)">{{ t('common.buttons.edit') }}</WowButton>
          <WowButton variant="danger" class="text-xs py-1.5 px-3" @click="confirmDelete(d)">✕</WowButton>
        </div>
      </WowCard>
    </div>

    <!-- Create / Edit Modal -->
    <WowModal v-model="showEditModal" :title="editingDef ? t('admin.raidDefinitions.editDefinition') : t('admin.raidDefinitions.newDefinition')" size="lg">
      <form @submit.prevent="saveDefinition" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('raidDefinitions.nameRequired') }}</label>
            <input v-model="form.name" required :placeholder="t('raidDefinitions.namePlaceholder')" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('raidDefinitions.raidType') }}</label>
            <select v-model="form.raid_type" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="">{{ t('common.fields.select') }}</option>
              <option v-for="r in raidTypes" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('raidDefinitions.sizeRequired') }}</label>
            <select v-model.number="form.size" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="">{{ t('common.fields.select') }}</option>
              <option :value="10">{{ t('calendar.tenMan') }}</option>
              <option :value="25">{{ t('calendar.twentyFiveMan') }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('raidDefinitions.defaultDuration') }}</label>
            <input v-model.number="form.default_duration_minutes" type="number" min="30" max="720" step="15" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-2">{{ t('raidDefinitions.slotAllocation') }}</label>
          <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            <div>
              <label class="block text-xs text-text-muted mb-1">Main Tank</label>
              <input v-model.number="form.main_tank_slots" type="number" min="0" max="5" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">Off Tank</label>
              <input v-model.number="form.off_tank_slots" type="number" min="0" max="5" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">Melee DPS</label>
              <input v-model.number="form.melee_dps_slots" type="number" min="0" max="10" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('raidDefinitions.healers') }}</label>
              <input v-model.number="form.healer_slots" type="number" min="1" max="15" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">Range DPS</label>
              <input v-model.number="form.range_dps_slots" type="number" min="1" max="30" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
            </div>
          </div>
        </div>
        <div v-if="formError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ formError }}</div>
      </form>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <WowButton variant="secondary" @click="showEditModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="primary" :disabled="!form.name || !form.raid_type || !form.size" :loading="saving" @click="saveDefinition">{{ editingDef ? t('common.buttons.save') : t('common.buttons.create') }}</WowButton>
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
          <WowButton variant="danger" :loading="saving" @click="doDelete">{{ t('common.buttons.delete') }}</WowButton>
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
import RaidSizeBadge from '@/components/common/RaidSizeBadge.vue'
import { useUiStore } from '@/stores/ui'
import { useWowIcons } from '@/composables/useWowIcons'
import { RAID_TYPES } from '@/constants'
import * as rdApi from '@/api/raidDefinitions'

const { t } = useI18n()
const uiStore = useUiStore()
const { getRaidIcon } = useWowIcons()
const raidTypes = RAID_TYPES

const definitions = ref([])
const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const formError = ref(null)

const showEditModal = ref(false)
const editingDef = ref(null)
const form = ref(defaultForm())

const showDeleteModal = ref(false)
const deleteTarget = ref(null)

function defaultForm() {
  return { name: '', raid_type: '', size: '', default_duration_minutes: 180, main_tank_slots: 1, off_tank_slots: 1, melee_dps_slots: 0, healer_slots: 5, range_dps_slots: 18 }
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
  formError.value = null
  showEditModal.value = true
}

function openEditModal(d) {
  editingDef.value = d
  form.value = {
    name: d.name,
    raid_type: d.raid_type || d.code || '',
    size: d.size || d.default_raid_size,
    default_duration_minutes: d.default_duration_minutes ?? 180,
    main_tank_slots: d.main_tank_slots ?? 1,
    off_tank_slots: d.off_tank_slots ?? 1,
    melee_dps_slots: d.melee_dps_slots ?? 0,
    healer_slots: d.healer_slots ?? 5,
    range_dps_slots: d.range_dps_slots ?? 18,
  }
  formError.value = null
  showEditModal.value = true
}

async function saveDefinition() {
  formError.value = null
  if (!form.value.name || !form.value.raid_type || !form.value.size) {
    formError.value = t('raidDefinitions.toasts.nameTypeSizeRequired')
    return
  }
  const totalSlots = (form.value.main_tank_slots || 0) + (form.value.off_tank_slots || 0) + (form.value.melee_dps_slots || 0) + (form.value.healer_slots || 0) + (form.value.range_dps_slots || 0)
  if (totalSlots > form.value.size) {
    formError.value = t('raidDefinitions.toasts.slotsExceedSize', { total: totalSlots, size: form.value.size })
    return
  }
  saving.value = true
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
  } finally {
    saving.value = false
  }
}

function confirmDelete(d) {
  deleteTarget.value = d
  showDeleteModal.value = true
}

async function doDelete() {
  saving.value = true
  try {
    await rdApi.adminDeleteDefaultDefinition(deleteTarget.value.id)
    showDeleteModal.value = false
    uiStore.showToast(t('admin.raidDefinitions.deleted'))
    await loadDefinitions()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('admin.raidDefinitions.loadError'), 'error')
  } finally {
    saving.value = false
  }
}
</script>
