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
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
        <h1 class="wow-heading text-xl sm:text-2xl">{{ t('raidDefinitions.title') }}</h1>
        <WowButton @click="openAddModal">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          {{ t('raidDefinitions.newDefinition') }}
        </WowButton>
      </div>

      <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div v-for="i in 4" :key="i" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      </div>
      <div v-else-if="noGuild" class="p-4 rounded-lg bg-blue-900/30 border border-blue-600 text-blue-300">
        {{ t('raidDefinitions.noGuild') }}
      </div>
      <div v-else-if="error" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">{{ error }}</div>
      <div v-else-if="definitions.length === 0" class="text-center py-12 text-text-muted">
        {{ t('raidDefinitions.noDefinitions') }}
      </div>
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
        <WowCard v-for="def in definitions" :key="def.id">
          <div class="flex items-start gap-3 mb-3">
            <img :src="getRaidIcon(def.raid_type)" :alt="def.raid_type" class="w-10 h-10 sm:w-12 sm:h-12 rounded border border-border-default flex-shrink-0" />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-bold text-text-primary truncate">{{ def.name }}</span>
                <span v-if="def.is_builtin" class="text-[10px] px-1.5 py-0.5 rounded bg-accent-gold/15 text-accent-gold border border-accent-gold/40">{{ t('raidDefinitions.default') }}</span>
              </div>
              <div class="flex items-center gap-1.5 mt-1">
                <RaidSizeBadge v-if="def.size" :size="def.size" />
                <RealmBadge v-if="def.realm" :realm="def.realm" />
              </div>
            </div>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 text-center text-xs mb-4">
            <div class="bg-blue-600/10 rounded p-1.5">
              <div class="text-blue-200 font-bold">{{ def.main_tank_slots ?? 1 }}</div>
              <div class="text-text-muted">Main Tank</div>
            </div>
            <div class="bg-cyan-500/10 rounded p-1.5">
              <div class="text-cyan-300 font-bold">{{ def.off_tank_slots ?? 1 }}</div>
              <div class="text-text-muted">Off Tank</div>
            </div>
            <div class="bg-blue-500/10 rounded p-1.5">
              <div class="text-blue-300 font-bold">{{ def.melee_dps_slots ?? 0 }}</div>
              <div class="text-text-muted">Melee DPS</div>
            </div>
            <div class="bg-green-500/10 rounded p-1.5">
              <div class="text-green-300 font-bold">{{ def.healer_slots ?? 5 }}</div>
              <div class="text-text-muted">Heal</div>
            </div>
            <div class="bg-red-500/10 rounded p-1.5">
              <div class="text-red-300 font-bold">{{ def.range_dps_slots ?? 18 }}</div>
              <div class="text-text-muted">Range DPS</div>
            </div>
          </div>
          <div class="flex flex-wrap gap-1.5 sm:gap-2">
            <WowButton v-if="def.is_builtin && hasMultipleGuilds" variant="secondary" class="flex-1 text-xs py-1.5" @click="openCopyModal(def)">
              📋 {{ t('raidDefinitions.copyToGuild') }}
            </WowButton>
            <WowButton v-if="!def.is_builtin || canManageDefaults" variant="secondary" class="flex-1 text-xs py-1.5" @click="openEditModal(def)">{{ t('common.buttons.edit') }}</WowButton>
            <WowButton v-if="!def.is_builtin || canManageDefaults" variant="danger" class="text-xs py-1.5 px-3" @click="confirmDelete(def)">✕</WowButton>
          </div>
        </WowCard>
      </div>
      </template>
    </div>

    <!-- Add/Edit modal -->
    <WowModal v-model="showModal" :title="editing ? t('raidDefinitions.editDefinition') : t('raidDefinitions.newRaidDefinition')" size="lg">
      <form @submit.prevent="saveDef" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('raidDefinitions.nameRequired') }}</label>
            <input v-model="form.name" required :placeholder="t('raidDefinitions.namePlaceholder')" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('raidDefinitions.raidType') }}</label>
            <select v-model="form.raid_type" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="">{{ t('raidDefinitions.select') }}</option>
              <option v-for="r in raidTypes" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('raidDefinitions.sizeRequired') }}</label>
            <select v-model.number="form.size" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="">{{ t('raidDefinitions.select') }}</option>
              <option :value="10">{{ t('calendar.tenMan') }}</option>
              <option :value="25">{{ t('calendar.twentyFiveMan') }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('raidDefinitions.guildRealm') }}</label>
            <select v-model.number="selectedGuildId" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option v-for="g in guildStore.guilds" :key="g.id" :value="g.id">{{ g.name }} ({{ g.realm_name }})</option>
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
        <!-- Multi-guild creation -->
        <div v-if="!editing && otherGuilds.length > 0" class="p-3 rounded bg-bg-tertiary border border-border-default">
          <label class="flex items-center gap-2 cursor-pointer">
            <input v-model="applyToOtherGuilds" type="checkbox" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
            <span class="text-sm text-text-primary">{{ t('raidDefinitions.copyToOther') }}</span>
          </label>
          <div v-if="applyToOtherGuilds" class="mt-2 space-y-1 pl-6">
            <label class="flex items-center gap-2 cursor-pointer mb-1">
              <input type="checkbox" :checked="allOtherGuildsSelected" @change="toggleAllOtherGuilds" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
              <span class="text-xs text-accent-gold font-semibold">{{ t('raidDefinitions.copyToAll') }}</span>
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
          <WowButton variant="secondary" @click="showModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton :loading="saving" @click="saveDef">{{ editing ? t('common.buttons.save') : t('common.buttons.create') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Copy to Guild modal -->
    <WowModal v-model="showCopyModal" :title="t('raidDefinitions.copyDefinitionToGuilds')" size="sm">
      <p class="text-text-muted text-sm mb-3">Copy <strong class="text-text-primary">{{ copySource?.name }}</strong> to selected guilds:</p>
      <div class="space-y-1">
        <label class="flex items-center gap-2 cursor-pointer mb-1">
          <input type="checkbox" :checked="allCopyGuildsSelected" @change="toggleAllCopyGuilds" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
          <span class="text-xs text-accent-gold font-semibold">{{ t('raidDefinitions.copyToAll') }}</span>
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
    <WowModal v-model="showNoGuildConfirm" :title="t('raidDefinitions.noAdditionalGuilds')" size="sm">
      <p class="text-text-muted text-sm">{{ t('raidDefinitions.onlyCreatedIn') }} <strong class="text-text-primary">{{ selectedGuildLabel }}</strong>. {{ t('raidDefinitions.goBackQuestion') }}</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="goBackToForm">{{ t('common.buttons.goBack') }}</WowButton>
          <WowButton @click="confirmSaveCurrentOnly">{{ t('common.buttons.continue') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Delete confirmation -->
    <WowModal v-model="showDeleteConfirm" :title="t('raidDefinitions.deleteDefinition')" size="sm">
      <p class="text-text-muted">Delete <strong class="text-text-primary">{{ deleteTarget?.name }}</strong>? {{ t('raidDefinitions.eventsNotAffected') }}</p>
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
import RealmBadge from '@/components/common/RealmBadge.vue'
import { useGuildStore } from '@/stores/guild'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { usePermissions } from '@/composables/usePermissions'
import { useWowIcons } from '@/composables/useWowIcons'
import { RAID_TYPES } from '@/constants'
import * as raidDefsApi from '@/api/raidDefinitions'
import { useI18n } from 'vue-i18n'

const guildStore = useGuildStore()
const authStore = useAuthStore()
const uiStore = useUiStore()
const permissions = usePermissions()
const { getRaidIcon } = useWowIcons()
const { t } = useI18n()

const hasViewAccess = computed(() => permissions.can('create_events') || permissions.can('manage_raid_definitions'))
const canManageDefaults = computed(() => permissions.can('manage_default_definitions'))
const hasMultipleGuilds = computed(() => guildStore.guilds.length > 1)

const definitions = ref([])
const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const noGuild = ref(false)
const formError = ref(null)
const showModal = ref(false)
const showDeleteConfirm = ref(false)
const showCopyModal = ref(false)
const showNoGuildConfirm = ref(false)
const editing = ref(null)
const deleteTarget = ref(null)
const copySource = ref(null)

const raidTypes = RAID_TYPES

const form = reactive({ name: '', raid_type: '', size: '', default_duration_minutes: 180, main_tank_slots: 1, off_tank_slots: 1, melee_dps_slots: 0, healer_slots: 5, range_dps_slots: 18 })
const selectedGuildId = ref(null)
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

async function loadDefinitions() {
  if (!guildStore.currentGuild || !isActive) return
  const version = ++loadVersion
  loading.value = true
  error.value = null
  noGuild.value = false
  try {
    const data = await raidDefsApi.getRaidDefinitions(guildStore.currentGuild.id)
    if (version === loadVersion && isActive) definitions.value = data
  } catch {
    if (version === loadVersion && isActive) error.value = t('raidDefinitions.failedToLoad')
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
  loadDefinitions()
})

// Reload when guild changes in sidebar
watch(() => guildStore.currentGuild?.id, (newId, oldId) => {
  if (newId && newId !== oldId) loadDefinitions()
})

function openAddModal() {
  editing.value = null
  selectedGuildId.value = guildStore.currentGuild?.id ?? null
  Object.assign(form, { name: '', raid_type: '', size: '', default_duration_minutes: 180, main_tank_slots: 1, off_tank_slots: 1, melee_dps_slots: 0, healer_slots: 5, range_dps_slots: 18 })
  applyToOtherGuilds.value = false
  selectedGuildIds.value = []
  formError.value = null; showModal.value = true
}

function openEditModal(def) {
  editing.value = def
  selectedGuildId.value = def.guild_id ?? guildStore.currentGuild?.id ?? null
  Object.assign(form, { name: def.name, raid_type: def.raid_type || def.code || '', size: def.size, default_duration_minutes: def.default_duration_minutes ?? 180, main_tank_slots: def.main_tank_slots ?? 1, off_tank_slots: def.off_tank_slots ?? 1, melee_dps_slots: def.melee_dps_slots ?? 0, healer_slots: def.healer_slots ?? 5, range_dps_slots: def.range_dps_slots ?? 18 })
  formError.value = null; showModal.value = true
}

function confirmDelete(def) { deleteTarget.value = def; showDeleteConfirm.value = true }

function openCopyModal(def) {
  copySource.value = def
  copyGuildIds.value = []
  showCopyModal.value = true
}

async function saveDef() {
  formError.value = null
  if (!form.name || !form.raid_type || !form.size) { formError.value = t('raidDefinitions.toasts.nameTypeSizeRequired'); return }
  const totalSlots = (form.main_tank_slots || 0) + (form.off_tank_slots || 0) + (form.melee_dps_slots || 0) + (form.healer_slots || 0) + (form.range_dps_slots || 0)
  if (totalSlots > form.size) { formError.value = t('raidDefinitions.toasts.slotsExceedSize', { total: totalSlots, size: form.size }); return }

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
  if (!targetGuild) { formError.value = t('raidDefinitions.toasts.selectGuild'); return }
  saving.value = true
  // Set realm from selected guild
  const payload = { ...form, realm: targetGuild.realm_name ?? '' }
  try {
    if (editing.value) {
      const updated = await raidDefsApi.updateRaidDefinition(targetGuildId, editing.value.id, payload)
      const idx = definitions.value.findIndex(d => d.id === editing.value.id)
      if (idx !== -1) definitions.value[idx] = updated
    } else {
      const created = await raidDefsApi.createRaidDefinition(targetGuildId, payload)
      // Only add to local list if it belongs to current guild view
      if (targetGuildId === guildStore.currentGuild?.id) {
        definitions.value.push(created)
      }
      // Also create in other selected guilds
      if (applyToOtherGuilds.value && selectedGuildIds.value.length > 0) {
        let failed = 0
        for (const guildId of selectedGuildIds.value) {
          try { await raidDefsApi.createRaidDefinition(guildId, payload) } catch { failed++ }
        }
        if (failed > 0) uiStore.showToast(t('raidDefinitions.toasts.failedToCreateInGuilds', { count: failed }), 'warning')
      }
    }
    showModal.value = false
    const guildLabel = targetGuild ? `${targetGuild.name} (${targetGuild.realm_name})` : ''
    uiStore.showToast(editing.value ? t('raidDefinitions.definitionUpdated') : t('raidDefinitions.toasts.definitionCreated', { guild: guildLabel }), 'success')
    // Switch to target guild if different from current (only for single-guild creation, not multi-guild copy)
    if (!editing.value && targetGuildId !== guildStore.currentGuild?.id && !applyToOtherGuilds.value) {
      guildStore.setCurrentGuild(targetGuild)
    }
  } catch (err) {
    formError.value = err?.response?.data?.message ?? err?.response?.data?.error ?? 'Failed to save'
  } finally { saving.value = false }
}

async function doDelete() {
  saving.value = true
  try {
    await raidDefsApi.deleteRaidDefinition(guildStore.currentGuild.id, deleteTarget.value.id)
    definitions.value = definitions.value.filter(d => d.id !== deleteTarget.value.id)
    showDeleteConfirm.value = false
    uiStore.showToast(t('raidDefinitions.definitionDeleted'), 'success')
  } catch { uiStore.showToast(t('raidDefinitions.failedToDelete'), 'error') }
  finally { saving.value = false }
}

async function doCopy() {
  if (copyGuildIds.value.length === 0) return
  saving.value = true
  let succeeded = 0, failed = 0
  for (const guildId of copyGuildIds.value) {
    try {
      await raidDefsApi.copyRaidDefinition(guildId, copySource.value.id)
      succeeded++
    } catch { failed++ }
  }
  showCopyModal.value = false
  if (failed > 0) {
    uiStore.showToast(t('raidDefinitions.toasts.copiedWithFailures', { succeeded, failed }), 'warning')
  } else {
    uiStore.showToast(t('raidDefinitions.toasts.copiedSuccess', { name: copySource.value.name, count: succeeded }), 'success')
  }
  saving.value = false
}
</script>
