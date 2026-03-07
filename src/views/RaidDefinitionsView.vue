<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6">
      <!-- Loading permissions -->
      <div v-if="!permissions.permissionsLoaded.value && !authStore.user?.is_admin" class="p-4 rounded-lg bg-bg-tertiary border border-border-default text-text-muted flex items-center gap-3">
        <div class="w-5 h-5 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin" />
        {{ t('common.labels.loading') }}
      </div>
      <!-- No permission -->
      <div v-else-if="!hasViewAccess" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">
        {{ t('admin.noPermission') }}
      </div>
      <template v-else>
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
        <h1 class="wow-heading text-xl sm:text-2xl">{{ t('raidDefinitions.title') }}</h1>
        <div class="flex items-center gap-2">
          <WowButton variant="secondary" @click="openImportModal" :disabled="noGuild">
            📥 {{ t('raidDefinitions.importFromGlobal') }}
          </WowButton>
          <WowButton @click="openAddModal" :disabled="noGuild">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
            </svg>
            {{ t('raidDefinitions.newDefinition') }}
          </WowButton>
        </div>
      </div>

      <!-- Expansion filter -->
      <div v-if="guildExpansions.length > 0" class="flex flex-wrap gap-2">
        <button
          type="button"
          class="px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors"
          :class="!selectedExpansion ? 'bg-accent-gold/20 text-accent-gold border-accent-gold/50' : 'bg-bg-tertiary text-text-muted border-border-default hover:border-border-gold'"
          @click="selectedExpansion = null"
        >{{ t('common.labels.all') }}</button>
        <button
          v-for="exp in guildExpansions"
          :key="exp.id"
          type="button"
          class="px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors"
          :class="selectedExpansion === (exp.expansion_slug || exp.slug) ? 'bg-accent-gold/20 text-accent-gold border-accent-gold/50' : 'bg-bg-tertiary text-text-muted border-border-default hover:border-border-gold'"
          @click="selectedExpansion = exp.expansion_slug || exp.slug"
        >{{ exp.expansion_name || exp.name }}</button>
      </div>

      <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div v-for="i in 4" :key="i" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      </div>
      <div v-else-if="noGuild" class="p-4 rounded-lg bg-blue-900/30 border border-blue-600 text-blue-300">
        {{ t('raidDefinitions.noGuild') }}
      </div>
      <div v-else-if="error" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">{{ error }}</div>
      <div v-else-if="filteredDefinitions.length === 0" class="text-center py-12 text-text-muted">
        {{ t('raidDefinitions.noDefinitions') }}
      </div>
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
        <WowCard v-for="def in filteredDefinitions" :key="def.id">
          <div class="flex items-start gap-3 mb-3">
            <img :src="getRaidIcon(def.code || def.raid_type)" :alt="def.name" class="w-10 h-10 sm:w-12 sm:h-12 rounded border border-border-default flex-shrink-0" />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-bold text-text-primary truncate">{{ def.name }}</span>
                <span v-if="def.is_builtin" class="text-[10px] px-1.5 py-0.5 rounded bg-accent-gold/15 text-accent-gold border border-accent-gold/40">{{ t('raidDefinitions.default') }}</span>
              </div>
              <div class="flex items-center gap-1.5 mt-1">
                <RaidSizeBadge v-if="def.size" :size="def.size" />
                <span v-if="def.supported_sizes && def.supported_sizes.length > 1" class="text-[10px] px-1.5 py-0.5 rounded bg-bg-tertiary text-text-muted border border-border-default">{{ def.supported_sizes.join('/') }}-man</span>
                <span v-if="def.expansion" class="text-[10px] px-1.5 py-0.5 rounded bg-purple-900/30 text-purple-300 border border-purple-700/40 uppercase">{{ constantsStore.expansionLabelMap[def.expansion] || def.expansion }}</span>
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
              <option value="">{{ t('common.fields.select') }}</option>
              <option v-for="r in raidTypes" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('raidDefinitions.sizeRequired') }}</label>
            <select v-model.number="form.size" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="">{{ t('common.fields.select') }}</option>
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
            <span class="text-sm text-text-primary">{{ t('common.copy.copyToOther') }}</span>
          </label>
          <div v-if="applyToOtherGuilds" class="mt-2 space-y-1 pl-6">
            <label class="flex items-center gap-2 cursor-pointer mb-1">
              <input type="checkbox" :checked="allOtherGuildsSelected" @change="toggleAllOtherGuilds" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
              <span class="text-xs text-accent-gold font-semibold">{{ t('common.copy.copyToAll') }}</span>
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
      <p class="text-text-muted text-sm mb-3">{{ t('common.copy.copyNameToGuilds', { name: copySource?.name }) }}</p>
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
      <p class="text-text-muted text-sm">{{ t('common.copy.onlyCreatedIn') }} <strong class="text-text-primary">{{ selectedGuildLabel }}</strong>. {{ t('common.copy.goBackQuestion') }}</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="goBackToForm">{{ t('common.buttons.goBack') }}</WowButton>
          <WowButton @click="confirmSaveCurrentOnly">{{ t('common.buttons.continue') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Delete confirmation -->
    <WowModal v-model="showDeleteConfirm" :title="t('raidDefinitions.deleteDefinition')" size="sm">
      <p class="text-text-muted">{{ t('raidDefinitions.deleteConfirmName', { name: deleteTarget?.name }) }} {{ t('raidDefinitions.eventsNotAffected') }}</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showDeleteConfirm = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="danger" :loading="saving" @click="doDelete">{{ t('common.buttons.delete') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Import from Global modal -->
    <WowModal v-model="showImportModal" :title="t('raidDefinitions.importFromGlobal')" size="md">
      <div v-if="importLoading" class="flex items-center gap-2 text-text-muted py-4">
        <div class="w-5 h-5 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin" />
        {{ t('common.labels.loading') }}
      </div>
      <div v-else-if="importableDefinitions.length === 0" class="text-center py-8 text-text-muted">
        {{ t('raidDefinitions.noImportable') }}
      </div>
      <div v-else class="space-y-4 max-h-96 overflow-y-auto">
        <div v-for="group in importableByExpansion" :key="group.expansion">
          <h3 class="text-xs uppercase tracking-wider text-text-muted font-semibold mb-2">{{ group.label }}</h3>
          <div class="space-y-2">
            <div
              v-for="def in group.defs"
              :key="def.id"
              class="flex items-center gap-3 p-3 rounded-lg border transition-colors"
              :class="selectedImports.includes(def.id) ? 'bg-accent-gold/10 border-accent-gold/50' : 'bg-bg-tertiary border-border-default hover:border-border-gold'"
            >
              <input type="checkbox" :value="def.id" v-model="selectedImports" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
              <img :src="getRaidIcon(def.raid_type || def.code)" :alt="def.name" class="w-8 h-8 rounded border border-border-default flex-shrink-0" />
              <div class="flex-1 min-w-0">
                <span class="font-medium text-text-primary text-sm">{{ def.name }}</span>
                <div class="text-xs text-text-muted flex items-center gap-2">
                  <span v-if="def.supported_sizes && def.supported_sizes.length > 1">{{ def.supported_sizes.join('/') }}-man</span>
                  <span v-else>{{ def.default_raid_size }}-man</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="flex items-center justify-between w-full">
          <span v-if="importableDefinitions.length > 0" class="text-xs text-text-muted">{{ t('raidDefinitions.selectedCount', { count: selectedImports.length }) }}</span>
          <span v-else />
          <div class="flex gap-3">
            <WowButton variant="secondary" @click="showImportModal = false">{{ t('common.buttons.cancel') }}</WowButton>
            <WowButton :loading="importSaving" :disabled="selectedImports.length === 0" @click="doImport">{{ t('raidDefinitions.importSelected') }}</WowButton>
          </div>
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
import { useToast } from '@/composables/useToast'
import { usePermissions } from '@/composables/usePermissions'
import { useWowIcons } from '@/composables/useWowIcons'
import { useExpansionData } from '@/composables/useExpansionData'
import { useConstantsStore } from '@/stores/constants'
import * as raidDefsApi from '@/api/raidDefinitions'
import * as guildExpansionsApi from '@/api/guild_expansions'
import { useI18n } from 'vue-i18n'

const guildStore = useGuildStore()
const authStore = useAuthStore()
const toast = useToast()
const permissions = usePermissions()
const { getRaidIcon } = useWowIcons()
const { t } = useI18n()
const constantsStore = useConstantsStore()

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
const showImportModal = ref(false)
const importLoading = ref(false)
const importSaving = ref(false)
const importableDefinitions = ref([])
const selectedImports = ref([])

const importableByExpansion = computed(() => {
  const groups = {}
  for (const def of importableDefinitions.value) {
    const exp = def.expansion || 'unknown'
    if (!groups[exp]) {
      const ge = guildExpansions.value.find(e => e.expansion_slug === exp)
      groups[exp] = {
        expansion: exp,
        label: ge?.expansion_name || constantsStore.expansionLabelMap[exp] || exp,
        sortOrder: ge?.sort_order ?? 999,
        defs: []
      }
    }
    groups[exp].defs.push(def)
  }
  return Object.values(groups).sort((a, b) => a.sortOrder - b.sortOrder)
})

const editing = ref(null)
const deleteTarget = ref(null)
const copySource = ref(null)
const selectedExpansion = ref(null)
const guildExpansions = ref([])

const { raidTypes } = useExpansionData()

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

const filteredDefinitions = computed(() => {
  if (!selectedExpansion.value) return definitions.value
  return definitions.value.filter(d => d.expansion === selectedExpansion.value)
})

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
  // Ensure constants store has expansions for label lookups
  if (constantsStore.expansions.length === 0) {
    constantsStore.fetchConstants().catch(() => {})
  }
  // Load guild expansions for the filter
  try {
    const guildId = guildStore.currentGuildId
    if (guildId) {
      const res = await guildExpansionsApi.getGuildExpansions(guildId)
      guildExpansions.value = (res?.expansions ?? res ?? [])
      guildExpansions.value.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
    }
  } catch {
    guildExpansions.value = []
  }
})

// Reload when guild changes in sidebar
watch(() => guildStore.currentGuild?.id, async (newId, oldId) => {
  if (newId && newId !== oldId) {
    loadDefinitions()
    selectedExpansion.value = null
    try {
      const res = await guildExpansionsApi.getGuildExpansions(newId)
      guildExpansions.value = (res?.expansions ?? res ?? [])
      guildExpansions.value.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
    } catch {
      guildExpansions.value = []
    }
  }
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
  if (!targetGuild) { formError.value = t('common.copy.selectGuild'); return }
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
        if (failed > 0) toast.warning(t('common.copy.failedToCreateInGuilds', { count: failed }))
      }
    }
    showModal.value = false
    const guildLabel = targetGuild ? `${targetGuild.name} (${targetGuild.realm_name})` : ''
    toast.success(editing.value ? t('raidDefinitions.definitionUpdated') : t('raidDefinitions.toasts.definitionCreated', { guild: guildLabel }))
    // Switch to target guild if different from current (only for single-guild creation, not multi-guild copy)
    if (!editing.value && targetGuildId !== guildStore.currentGuild?.id && !applyToOtherGuilds.value) {
      guildStore.setCurrentGuild(targetGuild)
    }
  } catch (err) {
    formError.value = err?.response?.data?.message ?? err?.response?.data?.error ?? t('common.toasts.failedToSave')
  } finally { saving.value = false }
}

async function doDelete() {
  saving.value = true
  try {
    await raidDefsApi.deleteRaidDefinition(guildStore.currentGuild.id, deleteTarget.value.id)
    definitions.value = definitions.value.filter(d => d.id !== deleteTarget.value.id)
    showDeleteConfirm.value = false
    toast.success(t('raidDefinitions.definitionDeleted'))
  } catch { toast.error(t('common.toasts.failedToDelete')) }
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
    toast.warning(t('common.copy.copiedWithFailures', { succeeded, failed }))
  } else {
    toast.success(t('common.copy.copiedSuccess', { name: copySource.value.name, count: succeeded }))
  }
  saving.value = false
}

async function openImportModal() {
  showImportModal.value = true
  importLoading.value = true
  selectedImports.value = []
  importableDefinitions.value = []
  // Ensure expansion labels are available
  if (constantsStore.expansions.length === 0) {
    constantsStore.fetchConstants().catch(() => {})
  }
  try {
    const data = await raidDefsApi.getAvailableDefinitions(guildStore.currentGuild.id)
    importableDefinitions.value = Array.isArray(data) ? data : []
  } catch {
    importableDefinitions.value = []
  } finally {
    importLoading.value = false
  }
}

async function doImport() {
  if (selectedImports.value.length === 0) return
  importSaving.value = true
  let succeeded = 0, failed = 0
  for (const defId of selectedImports.value) {
    try {
      await raidDefsApi.importRaidDefinition(guildStore.currentGuild.id, defId)
      succeeded++
    } catch { failed++ }
  }
  showImportModal.value = false
  importSaving.value = false
  if (succeeded > 0) {
    toast.success(t('raidDefinitions.importSuccess', { count: succeeded }))
    loadDefinitions()
  }
  if (failed > 0) {
    toast.warning(t('raidDefinitions.importFailed', { count: failed }))
  }
}
</script>
