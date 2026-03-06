<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
      <h2 class="wow-heading text-base">{{ t('admin.expansions.title') }}</h2>
      <WowButton @click="openAddExpansionModal">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Add Expansion
      </WowButton>
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
              <span v-if="defaultExpansionSlug === exp.slug" class="text-accent-gold text-sm" title="Default expansion">★</span>
              <span v-if="exp.is_active" class="text-[10px] px-1.5 py-0.5 rounded bg-green-600/15 text-green-400 border border-green-600/40">{{ t('common.status.active') }}</span>
              <span v-else class="text-[10px] px-1.5 py-0.5 rounded bg-red-600/15 text-red-400 border border-red-600/40">{{ t('common.status.inactive') }}</span>
            </div>
            <div class="flex items-center gap-3 mt-1 text-xs text-text-muted">
              <span>{{ exp.slug }}</span>
              <span>{{ t('admin.raidDefinitions.code') }}: {{ exp.sort_order ?? 0 }}</span>
            </div>
          </div>
        </div>
        <div class="flex flex-wrap gap-1.5 sm:gap-2" @click.stop>
          <WowButton variant="secondary" class="flex-1 text-xs py-1.5" @click="openEditExpansionModal(exp)">{{ t('common.buttons.edit') }}</WowButton>
          <WowButton variant="secondary" class="text-xs py-1.5 px-3" @click="toggleExpansionActive(exp)" :loading="togglingId === exp.id">
            {{ exp.is_active ? 'Disable' : 'Enable' }}
          </WowButton>
          <WowButton
            v-if="defaultExpansionSlug !== exp.slug"
            variant="ghost"
            class="text-xs py-1.5 px-3"
            :loading="settingDefaultId === exp.id"
            @click="doSetDefault(exp)"
          >★ Set Default</WowButton>
          <WowButton variant="danger" class="text-xs py-1.5 px-3" @click="confirmDeleteExpansion(exp)">✕</WowButton>
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

    <!-- Classes & Specs section for selected expansion -->
    <template v-if="selectedExpansion">
      <div class="border-t border-border-default pt-6 space-y-4">
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
          <h3 class="wow-heading text-base">{{ t('admin.expansions.classes') }} — {{ selectedExpansion.name }}</h3>
          <WowButton @click="openAddClassModal">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
            </svg>
            {{ t('admin.expansions.addClass') }}
          </WowButton>
        </div>

        <div v-if="classesLoading" class="text-center py-4 text-text-muted text-sm">{{ t('common.labels.loading') }}</div>
        <div v-else-if="classes.length === 0" class="text-center py-8 text-text-muted text-sm">
          {{ t('admin.expansions.noClasses') }}
        </div>
        <div v-else class="space-y-3">
          <div v-for="cls in classes" :key="cls.id"
            class="rounded-lg border border-border-default bg-bg-secondary p-3">
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-2">
                <span class="font-bold text-text-primary">{{ cls.name }}</span>
                <span v-if="cls.icon" class="text-xs text-text-muted">{{ cls.icon }}</span>
              </div>
              <div class="flex gap-1.5">
                <button type="button" class="text-xs text-accent-gold hover:text-accent-gold/80" @click="openEditClassModal(cls)">{{ t('common.buttons.edit') }}</button>
                <button type="button" class="text-xs text-red-400 hover:text-red-300" @click="doDeleteClass(cls)">✕</button>
                <button type="button" class="text-xs text-blue-400 hover:text-blue-300" @click="toggleClassSpecs(cls)">
                  {{ expandedClassId === cls.id ? '▼' : '▶' }} {{ t('admin.expansions.specs') }}
                </button>
              </div>
            </div>
            <!-- Specs for this class -->
            <div v-if="expandedClassId === cls.id" class="mt-2 pl-4 border-l-2 border-border-default space-y-2">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs text-text-muted font-medium">{{ t('admin.expansions.specs') }}</span>
                <button type="button" class="text-xs text-accent-gold hover:text-accent-gold/80" @click="openAddSpecModal(cls)">+ {{ t('admin.expansions.addSpec') }}</button>
              </div>
              <div v-if="specsLoading" class="text-xs text-text-muted">{{ t('common.labels.loading') }}</div>
              <div v-else-if="classSpecs.length === 0" class="text-xs text-text-muted">{{ t('admin.expansions.noSpecs') }}</div>
              <div v-else v-for="spec in classSpecs" :key="spec.id"
                class="flex items-center justify-between py-1 px-2 rounded bg-bg-primary text-sm">
                <div class="flex items-center gap-2">
                  <span class="text-text-primary">{{ spec.name }}</span>
                  <span class="text-xs text-text-muted px-1.5 py-0.5 rounded bg-bg-tertiary">{{ spec.role }}</span>
                </div>
                <div class="flex gap-1.5">
                  <button type="button" class="text-xs text-accent-gold hover:text-accent-gold/80" @click="openEditSpecModal(spec, cls)">{{ t('common.buttons.edit') }}</button>
                  <button type="button" class="text-xs text-red-400 hover:text-red-300" @click="doDeleteSpec(spec)">✕</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Add / Edit Class Modal -->
    <div v-if="showClassModal" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div class="bg-bg-secondary border border-border-default rounded-lg shadow-xl w-full max-w-sm">
        <div class="p-4 border-b border-border-default">
          <h3 class="text-lg font-semibold text-text-primary">{{ editingClass ? t('admin.expansions.editClass') : t('admin.expansions.addClass') }}</h3>
        </div>
        <form class="p-4 space-y-3" @submit.prevent="saveClass">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('admin.expansions.className') }}</label>
            <input v-model="classForm.name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-accent-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Icon</label>
            <input v-model="classForm.icon" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-accent-gold outline-none" />
          </div>
          <div v-if="classFormError" class="text-sm text-red-400">{{ classFormError }}</div>
          <div class="flex justify-end gap-2 pt-2">
            <button type="button" class="px-3 py-1.5 rounded-lg text-sm text-text-muted" @click="showClassModal = false">{{ t('common.buttons.cancel') }}</button>
            <button type="submit" class="px-3 py-1.5 rounded-lg bg-accent-gold/20 text-accent-gold text-sm font-medium" :disabled="saving">{{ t('common.buttons.save') }}</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Add / Edit Spec Modal -->
    <div v-if="showSpecModal" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div class="bg-bg-secondary border border-border-default rounded-lg shadow-xl w-full max-w-sm">
        <div class="p-4 border-b border-border-default">
          <h3 class="text-lg font-semibold text-text-primary">{{ editingSpec ? t('admin.expansions.editSpec') : t('admin.expansions.addSpec') }}</h3>
        </div>
        <form class="p-4 space-y-3" @submit.prevent="saveSpec">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('admin.expansions.specName') }}</label>
            <input v-model="specForm.name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-accent-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('admin.expansions.specRole') }}</label>
            <select v-model="specForm.role" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-accent-gold outline-none">
              <option value="dps">DPS</option>
              <option value="tank">Tank</option>
              <option value="healer">Healer</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Icon</label>
            <input v-model="specForm.icon" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-accent-gold outline-none" />
          </div>
          <div v-if="specFormError" class="text-sm text-red-400">{{ specFormError }}</div>
          <div class="flex justify-end gap-2 pt-2">
            <button type="button" class="px-3 py-1.5 rounded-lg text-sm text-text-muted" @click="showSpecModal = false">{{ t('common.buttons.cancel') }}</button>
            <button type="submit" class="px-3 py-1.5 rounded-lg bg-accent-gold/20 text-accent-gold text-sm font-medium" :disabled="saving">{{ t('common.buttons.save') }}</button>
          </div>
        </form>
      </div>
    </div>

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

    <!-- Add / Edit Expansion Modal -->
    <WowModal v-model="showExpansionModal" :title="editingExpansion ? 'Edit Expansion' : 'Add Expansion'" size="md">
      <form @submit.prevent="saveExpansion" class="space-y-4">
        <div>
          <label class="block text-xs text-text-muted mb-1">Name</label>
          <input v-model="expansionForm.name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Slug</label>
          <input v-model="expansionForm.slug" :placeholder="generatedSlug" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          <p class="text-[10px] text-text-muted mt-1">Leave empty to auto-generate from name</p>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Sort Order</label>
          <input v-model.number="expansionForm.sort_order" type="number" min="0" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div v-if="!editingExpansion" class="flex items-end">
          <label class="flex items-center gap-2 text-sm text-text-primary cursor-pointer">
            <input v-model="expansionForm.is_active" type="checkbox" class="rounded border-border-default bg-bg-tertiary" />
            {{ t('common.status.active') }}
          </label>
        </div>
        <div v-if="expansionFormError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ expansionFormError }}</div>
      </form>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <WowButton variant="secondary" @click="showExpansionModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="primary" :disabled="!expansionForm.name" :loading="saving" @click="saveExpansion">{{ editingExpansion ? t('common.buttons.save') : t('common.buttons.create') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Delete Expansion Confirmation -->
    <WowModal v-model="showDeleteExpansionModal" :title="t('common.buttons.delete')" size="sm">
      <p class="text-text-muted text-sm">
        Are you sure you want to delete <strong class="text-text-primary">{{ deleteExpansionTarget?.name }}</strong>? This will also remove all associated raids.
      </p>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <WowButton variant="secondary" @click="showDeleteExpansionModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="danger" :loading="saving" @click="doDeleteExpansion">{{ t('common.buttons.delete') }}</WowButton>
        </div>
      </template>
    </WowModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import RaidSizeBadge from '@/components/common/RaidSizeBadge.vue'
import { useToast } from '@/composables/useToast'
import { useWowIcons } from '@/composables/useWowIcons'
import * as expansionsApi from '@/api/expansions'

const { t } = useI18n()
const toast = useToast()
const { getRaidIcon } = useWowIcons()

const expansions = ref([])
const raids = ref([])
const selectedExpansion = ref(null)
const loading = ref(true)
const raidsLoading = ref(false)
const saving = ref(false)
const error = ref(null)
const defaultExpansionSlug = ref(null)

const showRaidModal = ref(false)
const editingRaid = ref(null)
const raidForm = ref(defaultRaidForm())
const raidFormError = ref(null)

const showDeleteModal = ref(false)
const deleteTarget = ref(null)

// Expansion CRUD state
const showExpansionModal = ref(false)
const editingExpansion = ref(null)
const expansionForm = ref(defaultExpansionForm())
const expansionFormError = ref(null)
const showDeleteExpansionModal = ref(false)
const deleteExpansionTarget = ref(null)
const togglingId = ref(null)
const settingDefaultId = ref(null)

const generatedSlug = computed(() => {
  return expansionForm.value.name
    ? expansionForm.value.name.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
    : ''
})

function defaultRaidForm() {
  return { name: '', code: '', default_raid_size: 25, default_duration_minutes: 180, is_heroic: false }
}

function defaultExpansionForm() {
  return { name: '', slug: '', sort_order: 0, is_active: true }
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

async function loadDefaultExpansion() {
  try {
    const result = await expansionsApi.getDefaultExpansion()
    defaultExpansionSlug.value = result?.slug ?? null
  } catch {
    defaultExpansionSlug.value = null
  }
}

async function loadRaids(slug) {
  raidsLoading.value = true
  try {
    raids.value = await expansionsApi.getRaids(slug)
  } catch (err) {
    raids.value = []
    toast.error(err?.response?.data?.message ?? t('admin.raidDefinitions.loadError'))
  } finally {
    raidsLoading.value = false
  }
}

function selectExpansion(exp) {
  selectedExpansion.value = exp
  expandedClassId.value = null
  classSpecs.value = []
  loadRaids(exp.slug)
  loadClasses()
}

// --- Expansion CRUD ---

function openAddExpansionModal() {
  editingExpansion.value = null
  expansionForm.value = defaultExpansionForm()
  expansionFormError.value = null
  showExpansionModal.value = true
}

function openEditExpansionModal(exp) {
  editingExpansion.value = exp
  expansionForm.value = {
    name: exp.name,
    slug: exp.slug || '',
    sort_order: exp.sort_order ?? 0,
    is_active: exp.is_active ?? true,
  }
  expansionFormError.value = null
  showExpansionModal.value = true
}

async function saveExpansion() {
  expansionFormError.value = null
  if (!expansionForm.value.name) {
    expansionFormError.value = 'Name is required'
    return
  }
  const payload = {
    ...expansionForm.value,
    slug: expansionForm.value.slug || generatedSlug.value,
  }
  saving.value = true
  try {
    if (editingExpansion.value) {
      await expansionsApi.updateExpansion(editingExpansion.value.id, payload)
      toast.info('Expansion updated')
    } else {
      await expansionsApi.createExpansion(payload)
      toast.info('Expansion created')
    }
    showExpansionModal.value = false
    await loadExpansions()
  } catch (err) {
    expansionFormError.value = err?.response?.data?.error ?? err?.response?.data?.message ?? 'Failed to save expansion'
  } finally {
    saving.value = false
  }
}

function confirmDeleteExpansion(exp) {
  deleteExpansionTarget.value = exp
  showDeleteExpansionModal.value = true
}

async function doDeleteExpansion() {
  saving.value = true
  try {
    await expansionsApi.deleteExpansion(deleteExpansionTarget.value.id)
    showDeleteExpansionModal.value = false
    toast.info('Expansion deleted')
    if (selectedExpansion.value?.id === deleteExpansionTarget.value.id) {
      selectedExpansion.value = null
      raids.value = []
    }
    await loadExpansions()
  } catch (err) {
    toast.error(err?.response?.data?.error ?? 'Failed to delete expansion')
  } finally {
    saving.value = false
  }
}

async function toggleExpansionActive(exp) {
  togglingId.value = exp.id
  try {
    await expansionsApi.updateExpansion(exp.id, { is_active: !exp.is_active })
    toast.info(`Expansion ${exp.is_active ? 'disabled' : 'enabled'}`)
    await loadExpansions()
  } catch (err) {
    toast.error(err?.response?.data?.error ?? 'Failed to toggle expansion')
  } finally {
    togglingId.value = null
  }
}

async function doSetDefault(exp) {
  settingDefaultId.value = exp.id
  try {
    await expansionsApi.setDefaultExpansion(exp.slug)
    defaultExpansionSlug.value = exp.slug
    toast.info(`${exp.name} set as default`)
  } catch (err) {
    toast.error(err?.response?.data?.error ?? 'Failed to set default expansion')
  } finally {
    settingDefaultId.value = null
  }
}

// --- Raid CRUD ---

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
      toast.info(t('admin.raidDefinitions.updated'))
    } else {
      await expansionsApi.addRaid(selectedExpansion.value.id, raidForm.value)
      toast.info(t('admin.raidDefinitions.created'))
    }
    showRaidModal.value = false
    await loadRaids(selectedExpansion.value.slug)
  } catch (err) {
    toast.error(err?.response?.data?.error ?? t('admin.raidDefinitions.loadError'))
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
    toast.info(t('admin.raidDefinitions.deleted'))
    await loadRaids(selectedExpansion.value.slug)
  } catch (err) {
    toast.error(err?.response?.data?.error ?? t('admin.raidDefinitions.loadError'))
  } finally {
    saving.value = false
  }
}

// --- Class / Spec CRUD ---

const classes = ref([])
const classSpecs = ref([])
const classesLoading = ref(false)
const specsLoading = ref(false)
const expandedClassId = ref(null)

const showClassModal = ref(false)
const editingClass = ref(null)
const classForm = ref({ name: '', icon: '' })
const classFormError = ref('')

const showSpecModal = ref(false)
const editingSpec = ref(null)
const specParentClass = ref(null)
const specForm = ref({ name: '', role: 'dps', icon: '' })
const specFormError = ref('')

async function loadClasses() {
  if (!selectedExpansion.value) return
  classesLoading.value = true
  try {
    classes.value = await expansionsApi.getClasses(selectedExpansion.value.slug)
  } catch {
    classes.value = []
  } finally {
    classesLoading.value = false
  }
}

async function loadSpecsForClass(cls) {
  specsLoading.value = true
  try {
    classSpecs.value = await expansionsApi.getClassSpecs(selectedExpansion.value.slug, cls.name)
  } catch {
    classSpecs.value = []
  } finally {
    specsLoading.value = false
  }
}

function toggleClassSpecs(cls) {
  if (expandedClassId.value === cls.id) {
    expandedClassId.value = null
    classSpecs.value = []
  } else {
    expandedClassId.value = cls.id
    loadSpecsForClass(cls)
  }
}

function openAddClassModal() {
  editingClass.value = null
  classForm.value = { name: '', icon: '' }
  classFormError.value = ''
  showClassModal.value = true
}

function openEditClassModal(cls) {
  editingClass.value = cls
  classForm.value = { name: cls.name, icon: cls.icon || '' }
  classFormError.value = ''
  showClassModal.value = true
}

async function saveClass() {
  classFormError.value = ''
  saving.value = true
  try {
    if (editingClass.value) {
      await expansionsApi.updateClass(editingClass.value.id, classForm.value)
    } else {
      await expansionsApi.addClass(selectedExpansion.value.id, classForm.value)
    }
    showClassModal.value = false
    await loadClasses()
  } catch (err) {
    classFormError.value = err?.response?.data?.error || err?.response?.data?.message || 'Failed to save class'
  } finally {
    saving.value = false
  }
}

async function doDeleteClass(cls) {
  if (!confirm(`Delete class "${cls.name}" and all its specs?`)) return
  try {
    await expansionsApi.deleteClass(cls.id)
    if (expandedClassId.value === cls.id) {
      expandedClassId.value = null
      classSpecs.value = []
    }
    await loadClasses()
  } catch {
    // ignore
  }
}

function openAddSpecModal(cls) {
  editingSpec.value = null
  specParentClass.value = cls
  specForm.value = { name: '', role: 'dps', icon: '' }
  specFormError.value = ''
  showSpecModal.value = true
}

function openEditSpecModal(spec, cls) {
  editingSpec.value = spec
  specParentClass.value = cls
  specForm.value = { name: spec.name, role: spec.role || 'dps', icon: spec.icon || '' }
  specFormError.value = ''
  showSpecModal.value = true
}

async function saveSpec() {
  specFormError.value = ''
  saving.value = true
  try {
    if (editingSpec.value) {
      await expansionsApi.updateSpec(editingSpec.value.id, specForm.value)
    } else {
      await expansionsApi.addSpec(specParentClass.value.id, specForm.value)
    }
    showSpecModal.value = false
    await loadSpecsForClass(specParentClass.value)
  } catch (err) {
    specFormError.value = err?.response?.data?.error || err?.response?.data?.message || 'Failed to save spec'
  } finally {
    saving.value = false
  }
}

async function doDeleteSpec(spec) {
  if (!confirm(`Delete spec "${spec.name}"?`)) return
  try {
    await expansionsApi.deleteSpec(spec.id)
    await loadSpecsForClass({ name: classes.value.find(c => expandedClassId.value === c.id)?.name, id: expandedClassId.value })
  } catch {
    // ignore
  }
}

onMounted(() => {
  loadExpansions()
  loadDefaultExpansion()
})
</script>
