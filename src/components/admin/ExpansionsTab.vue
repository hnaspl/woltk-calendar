<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
      <h2 class="wow-heading text-base">{{ t('admin.expansions.title') }}</h2>
    </div>

    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div v-for="i in 4" :key="i" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
    </div>
    <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>
    <div v-else-if="expansions.length === 0" class="text-center py-12 text-text-muted">
      {{ t('admin.expansions.noExpansions') }}
    </div>
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
      <WowCard
        v-for="exp in expansions"
        :key="exp.id"
        class="cursor-pointer transition-colors"
        :class="selectedExpansion?.id === exp.id ? 'ring-1 ring-accent-gold' : ''"
        @click="selectExpansion(exp)"
      >
        <div class="flex items-start gap-3 mb-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="font-bold text-text-primary truncate">{{ exp.name }}</span>
              <span v-if="exp.is_active" class="text-[10px] px-1.5 py-0.5 rounded bg-green-600/15 text-green-400 border border-green-600/40">{{ t('common.status.active') }}</span>
              <span v-else class="text-[10px] px-1.5 py-0.5 rounded bg-red-600/15 text-red-400 border border-red-600/40">{{ t('common.status.inactive') }}</span>
            </div>
            <div class="flex items-center gap-3 mt-1 text-xs text-text-muted">
              <span>{{ exp.slug }}</span>
              <span>{{ t('admin.raidDefinitions.code') }}: {{ exp.sort_order ?? 0 }}</span>
            </div>
          </div>
        </div>
      </WowCard>
    </div>

    <!-- Raids section for selected expansion -->
    <template v-if="selectedExpansion">
      <div class="border-t border-border-default pt-6 space-y-4">
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
          <h3 class="wow-heading text-base">{{ t('admin.expansions.raids') }} — {{ selectedExpansion.name }}</h3>
          <WowButton @click="openAddRaidModal">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
            </svg>
            {{ t('admin.expansions.addRaid') }}
          </WowButton>
        </div>

        <div v-if="raidsLoading" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div v-for="i in 2" :key="i" class="h-20 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
        </div>
        <div v-else-if="raids.length === 0" class="text-center py-8 text-text-muted text-sm">
          {{ t('admin.expansions.noExpansions') }}
        </div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          <WowCard v-for="raid in raids" :key="raid.id">
            <div class="flex items-start gap-3 mb-3">
              <img :src="getRaidIcon(raid.code)" :alt="raid.name" class="w-10 h-10 rounded border border-border-default flex-shrink-0" />
              <div class="flex-1 min-w-0">
                <span class="font-bold text-text-primary truncate block">{{ raid.name }}</span>
                <div class="flex items-center gap-2 mt-1 text-xs text-text-muted">
                  <span>{{ raid.code }}</span>
                  <RaidSizeBadge v-if="raid.default_raid_size" :size="raid.default_raid_size" />
                  <span v-if="raid.is_heroic" class="text-accent-gold">{{ t('admin.expansions.heroic') }}</span>
                </div>
              </div>
            </div>
            <div class="flex flex-wrap gap-1.5 sm:gap-2">
              <WowButton variant="secondary" class="flex-1 text-xs py-1.5" @click="openEditRaidModal(raid)">{{ t('common.buttons.edit') }}</WowButton>
              <WowButton variant="danger" class="text-xs py-1.5 px-3" @click="confirmDeleteRaid(raid)">✕</WowButton>
            </div>
          </WowCard>
        </div>
      </div>
    </template>

    <!-- Add / Edit Raid Modal -->
    <WowModal v-model="showRaidModal" :title="editingRaid ? t('admin.expansions.editRaid') : t('admin.expansions.addRaid')" size="lg">
      <form @submit.prevent="saveRaid" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('admin.expansions.raidName') }}</label>
            <input v-model="raidForm.name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('admin.expansions.raidCode') }}</label>
            <input v-model="raidForm.code" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('admin.expansions.raidSize') }}</label>
            <select v-model.number="raidForm.default_raid_size" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option :value="10">10</option>
              <option :value="25">25</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('admin.expansions.duration') }}</label>
            <input v-model.number="raidForm.default_duration_minutes" type="number" min="30" max="720" step="15" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div class="flex items-end">
            <label class="flex items-center gap-2 text-sm text-text-primary cursor-pointer">
              <input v-model="raidForm.is_heroic" type="checkbox" class="rounded border-border-default bg-bg-tertiary" />
              {{ t('admin.expansions.heroic') }}
            </label>
          </div>
        </div>
        <div v-if="raidFormError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ raidFormError }}</div>
      </form>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <WowButton variant="secondary" @click="showRaidModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="primary" :disabled="!raidForm.name || !raidForm.code" :loading="saving" @click="saveRaid">{{ editingRaid ? t('common.buttons.save') : t('common.buttons.create') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Delete Raid Confirmation -->
    <WowModal v-model="showDeleteModal" :title="t('common.buttons.delete')" size="sm">
      <p class="text-text-muted text-sm">
        {{ t('admin.raidDefinitions.deleteConfirm', { name: deleteTarget?.name }) }}
      </p>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <WowButton variant="secondary" @click="showDeleteModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="danger" :loading="saving" @click="doDeleteRaid">{{ t('common.buttons.delete') }}</WowButton>
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
import * as expansionsApi from '@/api/expansions'

const { t } = useI18n()
const uiStore = useUiStore()
const { getRaidIcon } = useWowIcons()

const expansions = ref([])
const raids = ref([])
const selectedExpansion = ref(null)
const loading = ref(true)
const raidsLoading = ref(false)
const saving = ref(false)
const error = ref(null)

const showRaidModal = ref(false)
const editingRaid = ref(null)
const raidForm = ref(defaultRaidForm())
const raidFormError = ref(null)

const showDeleteModal = ref(false)
const deleteTarget = ref(null)

function defaultRaidForm() {
  return { name: '', code: '', default_raid_size: 25, default_duration_minutes: 180, is_heroic: false }
}

async function loadExpansions() {
  loading.value = true
  error.value = null
  try {
    expansions.value = await expansionsApi.listExpansions()
  } catch (err) {
    error.value = err?.response?.data?.message ?? t('admin.raidDefinitions.loadError')
  } finally {
    loading.value = false
  }
}

async function loadRaids(slug) {
  raidsLoading.value = true
  try {
    raids.value = await expansionsApi.getRaids(slug)
  } catch (err) {
    raids.value = []
    uiStore.showToast(err?.response?.data?.message ?? t('admin.raidDefinitions.loadError'), 'error')
  } finally {
    raidsLoading.value = false
  }
}

function selectExpansion(exp) {
  selectedExpansion.value = exp
  loadRaids(exp.slug)
}

function openAddRaidModal() {
  editingRaid.value = null
  raidForm.value = defaultRaidForm()
  raidFormError.value = null
  showRaidModal.value = true
}

function openEditRaidModal(raid) {
  editingRaid.value = raid
  raidForm.value = {
    name: raid.name,
    code: raid.code || '',
    default_raid_size: raid.default_raid_size ?? 25,
    default_duration_minutes: raid.default_duration_minutes ?? 180,
    is_heroic: raid.is_heroic ?? false,
  }
  raidFormError.value = null
  showRaidModal.value = true
}

async function saveRaid() {
  raidFormError.value = null
  if (!raidForm.value.name || !raidForm.value.code) {
    raidFormError.value = t('raidDefinitions.toasts.nameTypeSizeRequired')
    return
  }
  saving.value = true
  try {
    if (editingRaid.value) {
      await expansionsApi.updateRaid(editingRaid.value.id, raidForm.value)
      uiStore.showToast(t('admin.raidDefinitions.updated'))
    } else {
      await expansionsApi.addRaid(selectedExpansion.value.id, raidForm.value)
      uiStore.showToast(t('admin.raidDefinitions.created'))
    }
    showRaidModal.value = false
    await loadRaids(selectedExpansion.value.slug)
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('admin.raidDefinitions.loadError'), 'error')
  } finally {
    saving.value = false
  }
}

function confirmDeleteRaid(raid) {
  deleteTarget.value = raid
  showDeleteModal.value = true
}

async function doDeleteRaid() {
  saving.value = true
  try {
    await expansionsApi.deleteRaid(deleteTarget.value.id)
    showDeleteModal.value = false
    uiStore.showToast(t('admin.raidDefinitions.deleted'))
    await loadRaids(selectedExpansion.value.slug)
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('admin.raidDefinitions.loadError'), 'error')
  } finally {
    saving.value = false
  }
}

onMounted(loadExpansions)
</script>
