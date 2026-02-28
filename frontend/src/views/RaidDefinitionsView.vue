<template>
  <AppShell>
    <div class="p-4 md:p-6 space-y-6">
      <div class="flex items-center justify-between">
        <h1 class="wow-heading text-2xl">Raid Definitions</h1>
        <WowButton @click="openAddModal">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          New Definition
        </WowButton>
      </div>

      <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div v-for="i in 4" :key="i" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      </div>
      <div v-else-if="error" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">{{ error }}</div>
      <div v-else-if="definitions.length === 0" class="text-center py-12 text-text-muted">
        No raid definitions yet. Create one to start scheduling raids.
      </div>
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <WowCard v-for="def in definitions" :key="def.id">
          <div class="flex items-start gap-3 mb-3">
            <img :src="getRaidIcon(def.raid_type)" :alt="def.raid_type" class="w-12 h-12 rounded border border-border-default flex-shrink-0" />
            <div class="flex-1 min-w-0">
              <div class="font-bold text-text-primary truncate">{{ def.name }}</div>
              <div class="flex items-center gap-1.5 mt-1">
                <RaidSizeBadge v-if="def.size" :size="def.size" />
                <RealmBadge v-if="def.realm" :realm="def.realm" />
              </div>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-2 text-center text-xs mb-4">
            <div class="bg-blue-500/10 rounded p-1.5">
              <div class="text-blue-300 font-bold">{{ def.tank_slots ?? 2 }}</div>
              <div class="text-text-muted">Tanks</div>
            </div>
            <div class="bg-green-500/10 rounded p-1.5">
              <div class="text-green-300 font-bold">{{ def.healer_slots ?? 5 }}</div>
              <div class="text-text-muted">Healers</div>
            </div>
            <div class="bg-red-500/10 rounded p-1.5">
              <div class="text-red-300 font-bold">{{ def.dps_slots ?? 18 }}</div>
              <div class="text-text-muted">DPS</div>
            </div>
          </div>
          <div class="flex gap-2">
            <WowButton variant="secondary" class="flex-1 text-xs py-1.5" @click="openEditModal(def)">Edit</WowButton>
            <WowButton variant="danger" class="text-xs py-1.5 px-3" @click="confirmDelete(def)">✕</WowButton>
          </div>
        </WowCard>
      </div>
    </div>

    <!-- Add/Edit modal -->
    <WowModal v-model="showModal" :title="editing ? 'Edit Raid Definition' : 'New Raid Definition'" size="md">
      <form @submit.prevent="saveDef" class="space-y-4">
        <div>
          <label class="block text-xs text-text-muted mb-1">Name *</label>
          <input v-model="form.name" required placeholder="ICC 25 Heroic" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
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
            <label class="block text-xs text-text-muted mb-1">Size *</label>
            <select v-model.number="form.size" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="">Select…</option>
              <option :value="10">10-man</option>
              <option :value="25">25-man</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Realm</label>
          <select v-model="form.realm" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option value="">Select realm…</option>
            <option v-for="r in warmaneRealms" :key="r" :value="r">{{ r }}</option>
          </select>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label class="block text-xs text-text-muted mb-1">Tank Slots</label>
            <input v-model.number="form.tank_slots" type="number" min="1" max="10" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">Healer Slots</label>
            <input v-model.number="form.healer_slots" type="number" min="1" max="15" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">DPS Slots</label>
            <input v-model.number="form.dps_slots" type="number" min="1" max="30" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
        </div>
        <div v-if="formError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ formError }}</div>
      </form>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showModal = false">Cancel</WowButton>
          <WowButton :loading="saving" @click="saveDef">{{ editing ? 'Save' : 'Create' }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Delete confirmation -->
    <WowModal v-model="showDeleteConfirm" title="Delete Definition" size="sm">
      <p class="text-text-muted">Delete <strong class="text-text-primary">{{ deleteTarget?.name }}</strong>? Events using this definition won't be affected.</p>
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
import * as raidDefsApi from '@/api/raidDefinitions'

const guildStore = useGuildStore()
const uiStore = useUiStore()
const { getRaidIcon } = useWowIcons()

const definitions = ref([])
const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const formError = ref(null)
const showModal = ref(false)
const showDeleteConfirm = ref(false)
const editing = ref(null)
const deleteTarget = ref(null)

const raidTypes = [
  { value: 'naxx', label: 'Naxxramas' }, { value: 'os', label: 'Obsidian Sanctum' },
  { value: 'eoe', label: 'Eye of Eternity' }, { value: 'voa', label: 'Vault of Archavon' },
  { value: 'ulduar', label: 'Ulduar' }, { value: 'toc', label: 'Trial of the Crusader' },
  { value: 'icc', label: 'Icecrown Citadel' }, { value: 'rs', label: 'Ruby Sanctum' }
]

const warmaneRealms = ['Icecrown', 'Lordaeron', 'Onyxia', 'Blackrock', 'Frostwolf', 'Frostmourne', 'Neltharion']

const form = reactive({ name: '', raid_type: '', size: '', realm: '', tank_slots: 2, healer_slots: 5, dps_slots: 18 })

onMounted(async () => {
  loading.value = true
  if (!guildStore.currentGuild) await guildStore.fetchGuilds()
  try {
    definitions.value = await raidDefsApi.getRaidDefinitions(guildStore.currentGuild.id)
  } catch { error.value = 'Failed to load raid definitions' }
  finally { loading.value = false }
})

function openAddModal() {
  editing.value = null
  Object.assign(form, { name: '', raid_type: '', size: '', realm: '', tank_slots: 2, healer_slots: 5, dps_slots: 18 })
  formError.value = null; showModal.value = true
}

function openEditModal(def) {
  editing.value = def
  Object.assign(form, { name: def.name, raid_type: def.raid_type, size: def.size, realm: def.realm ?? '', tank_slots: def.tank_slots ?? 2, healer_slots: def.healer_slots ?? 5, dps_slots: def.dps_slots ?? 18 })
  formError.value = null; showModal.value = true
}

function confirmDelete(def) { deleteTarget.value = def; showDeleteConfirm.value = true }

async function saveDef() {
  formError.value = null
  if (!form.name || !form.raid_type || !form.size) { formError.value = 'Name, type and size are required'; return }
  saving.value = true
  try {
    if (editing.value) {
      const updated = await raidDefsApi.updateRaidDefinition(guildStore.currentGuild.id, editing.value.id, form)
      const idx = definitions.value.findIndex(d => d.id === editing.value.id)
      if (idx !== -1) definitions.value[idx] = updated
    } else {
      definitions.value.push(await raidDefsApi.createRaidDefinition(guildStore.currentGuild.id, form))
    }
    showModal.value = false
    uiStore.showToast(editing.value ? 'Definition updated' : 'Definition created', 'success')
  } catch (err) {
    formError.value = err?.response?.data?.message ?? 'Failed to save'
  } finally { saving.value = false }
}

async function doDelete() {
  saving.value = true
  try {
    await raidDefsApi.deleteRaidDefinition(guildStore.currentGuild.id, deleteTarget.value.id)
    definitions.value = definitions.value.filter(d => d.id !== deleteTarget.value.id)
    showDeleteConfirm.value = false
    uiStore.showToast('Definition deleted', 'success')
  } catch { uiStore.showToast('Failed to delete', 'error') }
  finally { saving.value = false }
}
</script>
