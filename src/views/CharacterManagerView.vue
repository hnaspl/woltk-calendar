<template>
  <AppShell>
    <div class="p-4 md:p-6 space-y-6">
      <div class="flex items-center justify-between">
        <h1 class="wow-heading text-2xl">My Characters</h1>
        <WowButton @click="openAddModal">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          Add Character
        </WowButton>
      </div>

      <!-- Tabs: Active / Archived -->
      <div class="flex gap-4 border-b border-border-default">
        <button
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2"
          :class="activeTab === 'active' ? 'text-accent-gold border-accent-gold' : 'text-text-muted border-transparent hover:text-text-primary'"
          @click="activeTab = 'active'"
        >Active</button>
        <button
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2"
          :class="activeTab === 'archived' ? 'text-accent-gold border-accent-gold' : 'text-text-muted border-transparent hover:text-text-primary'"
          @click="switchToArchived"
        >Archived <span v-if="archivedCharacters.length" class="text-xs opacity-60">({{ archivedCharacters.length }})</span></button>
      </div>

      <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="i in 3" :key="i" class="h-24 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      </div>

      <div v-else-if="error" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">
        {{ error }}
      </div>

      <!-- Active characters -->
      <template v-else-if="activeTab === 'active'">
        <div v-if="characters.length === 0" class="text-center py-12 text-text-muted">
          <p class="mb-4">You haven't added any characters yet.</p>
          <WowButton @click="openAddModal">Add your first character</WowButton>
        </div>

        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <WowCard
            v-for="char in characters"
            :key="char.id"
            :gold="char.is_main"
            class="relative"
          >
            <!-- Main badge -->
            <span
              v-if="char.is_main"
              class="absolute top-3 right-3 text-[10px] font-bold text-accent-gold bg-accent-gold/10 border border-accent-gold/30 px-1.5 py-0.5 rounded"
            >MAIN</span>

            <CharacterTooltip :character="charToTooltip(char)" position="right">
              <div class="flex items-center gap-3 mb-3 cursor-pointer">
                <img
                  :src="getClassIcon(char.class)"
                  :alt="char.class"
                  class="w-12 h-12 rounded border border-border-default"
                />
                <div>
                  <div class="font-bold text-text-primary">{{ char.name }}</div>
                  <div class="text-xs text-text-muted">{{ char.realm }}</div>
                  <div v-if="char.metadata?.level" class="text-xs text-text-muted">
                    Level {{ char.metadata.level }} {{ char.metadata.race || '' }}
                  </div>
                </div>
              </div>
            </CharacterTooltip>

            <div class="flex flex-wrap gap-1.5 mb-2">
              <ClassBadge :class-name="char.class" />
              <RoleBadge v-if="char.role" :role="char.role" />
              <SpecBadge v-if="char.spec" :spec="char.spec" />
              <SpecBadge v-if="char.secondary_spec" :spec="char.secondary_spec" />
            </div>
            <!-- Synced metadata -->
            <div v-if="char.metadata?.professions?.length" class="text-xs text-text-muted mb-2">
              {{ char.metadata.professions.map(p => `${p.name} (${p.skill})`).join(', ') }}
            </div>
            <div v-if="char.metadata?.last_synced" class="text-[10px] text-text-muted/60 mb-3">
              Synced {{ new Date(char.metadata.last_synced).toLocaleDateString() }}
            </div>
            <div v-else class="mb-3"></div>

            <div class="flex gap-2">
              <WowButton
                v-if="!char.is_main"
                variant="secondary"
                class="flex-1 text-xs py-1.5"
                @click="setMain(char)"
              >Set Main</WowButton>
              <WowButton
                variant="secondary"
                class="flex-1 text-xs py-1.5"
                @click="syncFromWarmane(char)"
                :loading="syncing === char.id"
              >Sync</WowButton>
              <WowButton
                variant="secondary"
                class="flex-1 text-xs py-1.5"
                @click="openEditModal(char)"
              >Edit</WowButton>
              <WowButton
                variant="danger"
                class="text-xs py-1.5 px-3"
                @click="confirmRemove(char)"
              >✕</WowButton>
            </div>
          </WowCard>
        </div>
      </template>

      <!-- Archived characters -->
      <template v-else>
        <div v-if="archivedCharacters.length === 0" class="text-center py-12 text-text-muted">
          <p>No archived characters.</p>
        </div>

        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <WowCard
            v-for="char in archivedCharacters"
            :key="char.id"
            class="relative opacity-70"
          >
            <span class="absolute top-3 right-3 text-[10px] font-bold text-red-400 bg-red-900/20 border border-red-600/30 px-1.5 py-0.5 rounded">ARCHIVED</span>

            <div class="flex items-center gap-3 mb-3">
              <img
                :src="getClassIcon(char.class)"
                :alt="char.class"
                class="w-12 h-12 rounded border border-border-default"
              />
              <div>
                <div class="font-bold text-text-primary">{{ char.name }}</div>
                <div class="text-xs text-text-muted">{{ char.realm }}</div>
              </div>
            </div>

            <div class="flex flex-wrap gap-1.5 mb-3">
              <ClassBadge :class-name="char.class" />
              <RoleBadge v-if="char.role" :role="char.role" />
              <SpecBadge v-if="char.spec" :spec="char.spec" />
            </div>

            <div class="flex gap-2">
              <WowButton
                variant="secondary"
                class="flex-1 text-xs py-1.5"
                @click="doUnarchive(char)"
                :loading="saving"
              >Unarchive</WowButton>
              <WowButton
                variant="danger"
                class="text-xs py-1.5 px-3"
                @click="confirmDelete(char)"
              >Delete</WowButton>
            </div>
          </WowCard>
        </div>
      </template>
    </div>

    <!-- Add / Edit modal -->
    <WowModal v-model="showModal" :title="editingChar ? 'Edit Character' : 'Add Character'" size="md">
      <form @submit.prevent="saveChar" class="space-y-4">
        <!-- Warmane import section (only when adding, not editing) -->
        <div v-if="!editingChar" class="p-3 rounded bg-bg-tertiary border border-border-default space-y-3">
          <div class="flex items-center gap-2">
            <span class="text-xs text-accent-gold font-bold uppercase">Import from Warmane</span>
            <span class="text-xs text-text-muted">(optional — fill name & realm, then click Lookup)</span>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <input v-model="form.name" placeholder="Character name" class="w-full bg-bg-secondary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
            <select v-model="form.realm" class="w-full bg-bg-secondary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="">Select realm…</option>
              <option v-for="r in warmaneRealms" :key="r" :value="r">{{ r }}</option>
            </select>
          </div>
          <div class="flex items-center gap-3">
            <WowButton variant="secondary" class="text-xs py-1.5" :loading="lookingUp" :disabled="!form.name || !form.realm" @click="lookupFromWarmane">
              Lookup on Warmane
            </WowButton>
            <span v-if="lookupResult === 'found'" class="text-xs text-green-400">✓ Found — fields populated from armory</span>
            <span v-else-if="lookupResult === 'not_found'" class="text-xs text-yellow-400">Not found on Warmane — fill in manually below</span>
          </div>
        </div>

        <div>
          <label class="block text-xs text-text-muted mb-1">Character Name *</label>
          <input v-model="form.name" required placeholder="Arthas" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Class *</label>
          <select v-model="form.class" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" @change="onClassChange">
            <option value="">Select class…</option>
            <option v-for="c in wowClasses" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Realm *</label>
          <select v-model="form.realm" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option value="">Select realm…</option>
            <option v-for="r in (guildRealms.length ? guildRealms : warmaneRealms)" :key="r" :value="r">{{ r }}</option>
          </select>
          <span v-if="guildRealms.length" class="text-[10px] text-text-muted">Only realms from your guilds</span>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Role</label>
          <select v-model="form.role" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option value="">Select role…</option>
            <option v-for="r in filteredRoles" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Spec</label>
          <select v-if="filteredSpecs.length > 0" v-model="form.spec" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option value="">Select spec…</option>
            <option v-for="s in filteredSpecs" :key="s" :value="s">{{ s }}</option>
          </select>
          <input v-else v-model="form.spec" placeholder="e.g. Frost, Holy…" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Secondary Spec</label>
          <select v-if="filteredSpecs.length > 0" v-model="form.secondary_spec" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option value="">Select secondary spec…</option>
            <option v-for="s in filteredSpecs" :key="s" :value="s">{{ s }}</option>
          </select>
          <input v-else v-model="form.secondary_spec" placeholder="e.g. Unholy, Protection…" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Warmane Armory URL</label>
          <input v-model="form.armory_url" placeholder="https://armory.warmane.com/character/…" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div v-if="formError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ formError }}</div>
      </form>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showModal = false">Cancel</WowButton>
          <WowButton :loading="saving" @click="saveChar">
            {{ editingChar ? 'Save Changes' : 'Add Character' }}
          </WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Remove confirmation (Archive or Delete) -->
    <WowModal v-model="showRemoveConfirm" title="Remove Character" size="sm">
      <p class="text-text-muted mb-4">What would you like to do with <strong class="text-text-primary">{{ removeTarget?.name }}</strong>?</p>
      <div class="space-y-2">
        <p class="text-xs text-text-muted"><strong class="text-text-primary">Archive</strong> — hide from signups; can be restored later.</p>
        <p class="text-xs text-text-muted"><strong class="text-red-400">Delete</strong> — permanently remove. This cannot be undone.</p>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showRemoveConfirm = false">Cancel</WowButton>
          <WowButton variant="secondary" :loading="saving" @click="doArchive">Archive</WowButton>
          <WowButton variant="danger" :loading="saving" @click="doDelete">Delete</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Delete confirmation for archived chars -->
    <WowModal v-model="showDeleteConfirm" title="Delete Character" size="sm">
      <p class="text-text-muted">Permanently delete <strong class="text-text-primary">{{ deleteTarget?.name }}</strong>? This cannot be undone.</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showDeleteConfirm = false">Cancel</WowButton>
          <WowButton variant="danger" :loading="saving" @click="doDeleteArchived">Delete</WowButton>
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
import ClassBadge from '@/components/common/ClassBadge.vue'
import RoleBadge from '@/components/common/RoleBadge.vue'
import SpecBadge from '@/components/common/SpecBadge.vue'
import CharacterTooltip from '@/components/common/CharacterTooltip.vue'
import { useGuildStore } from '@/stores/guild'
import { useUiStore } from '@/stores/ui'
import { useWowIcons } from '@/composables/useWowIcons'
import { WARMANE_REALMS, WOW_CLASSES, ROLE_OPTIONS, CLASS_ROLES, CLASS_SPECS } from '@/constants'
import * as charApi from '@/api/characters'
import * as warmaneApi from '@/api/warmane'

const guildStore = useGuildStore()
const uiStore = useUiStore()
const { getClassIcon } = useWowIcons()

/** Map display char to CharacterTooltip format */
function charToTooltip(char) {
  return {
    name: char.name,
    class_name: char.class,
    realm_name: char.realm,
    default_role: char.role,
    primary_spec: char.spec,
    secondary_spec: char.secondary_spec,
    armory_url: char.armory_url,
    metadata: char.metadata ?? {}
  }
}

const characters = ref([])
const archivedCharacters = ref([])
const activeTab = ref('active')
const loading = ref(true)
const saving = ref(false)
const syncing = ref(null)
const lookingUp = ref(false)
const lookupResult = ref(null)
const error = ref(null)
const formError = ref(null)
const showModal = ref(false)
const showRemoveConfirm = ref(false)
const showDeleteConfirm = ref(false)
const editingChar = ref(null)
const removeTarget = ref(null)
const deleteTarget = ref(null)

const wowClasses = WOW_CLASSES
const warmaneRealms = WARMANE_REALMS

/** Realms from guilds the user belongs to (for character realm selector) */
const guildRealms = computed(() => {
  const realms = new Set(guildStore.guilds.map(g => g.realm_name).filter(Boolean))
  return [...realms].sort()
})

const form = reactive({ name: '', class: '', realm: '', role: '', spec: '', secondary_spec: '', armory_url: '' })

/** Roles filtered by the selected class */
const filteredRoles = computed(() => {
  if (!form.class) return ROLE_OPTIONS
  const allowed = CLASS_ROLES[form.class] ?? []
  if (allowed.length === 0) return ROLE_OPTIONS
  return ROLE_OPTIONS.filter(r => allowed.includes(r.value))
})

/** Specs filtered by the selected class */
const filteredSpecs = computed(() => {
  if (!form.class) return []
  return CLASS_SPECS[form.class] ?? []
})

// Map backend response fields to display-friendly names
function mapChar(c) {
  return {
    ...c,
    class: c.class_name || c.class,
    realm: c.realm_name || c.realm,
    role: c.default_role || c.role,
    spec: c.primary_spec || c.spec,
    secondary_spec: c.secondary_spec,
    armory_url: c.armory_url,
  }
}

onMounted(async () => {
  loading.value = true
  if (!guildStore.currentGuild) await guildStore.fetchGuilds()
  if (!guildStore.currentGuild) {
    error.value = 'You need to join a guild first before managing characters'
    loading.value = false
    return
  }
  try {
    const raw = await charApi.getMyCharacters(guildStore.currentGuild?.id)
    characters.value = (Array.isArray(raw) ? raw : []).map(mapChar)
  } catch (err) {
    error.value = 'Failed to load characters'
  } finally {
    loading.value = false
  }
})

async function loadArchivedCharacters() {
  try {
    // include_archived=true returns ALL chars (active + archived); filter for archived only
    const all = await charApi.getArchivedCharacters(guildStore.currentGuild?.id)
    const allMapped = (Array.isArray(all) ? all : []).map(mapChar)
    archivedCharacters.value = allMapped.filter(c => !c.is_active)
  } catch {
    // ignore
  }
}

async function switchToArchived() {
  activeTab.value = 'archived'
  await loadArchivedCharacters()
}

function openAddModal() {
  editingChar.value = null
  Object.assign(form, { name: '', class: '', realm: '', role: '', spec: '', secondary_spec: '', armory_url: '' })
  formError.value = null
  lookingUp.value = false
  lookupResult.value = null
  showModal.value = true
}

/** Reset role and specs when class changes so invalid values don't persist */
function onClassChange() {
  const allowed = CLASS_ROLES[form.class] ?? []
  if (form.role && !allowed.includes(form.role)) form.role = ''
  const specs = CLASS_SPECS[form.class] ?? []
  if (form.spec && specs.length > 0 && !specs.includes(form.spec)) form.spec = ''
  if (form.secondary_spec && specs.length > 0 && !specs.includes(form.secondary_spec)) form.secondary_spec = ''
}

function openEditModal(char) {
  editingChar.value = char
  Object.assign(form, { name: char.name, class: char.class, realm: char.realm, role: char.role ?? '', spec: char.spec ?? '', secondary_spec: char.secondary_spec ?? '', armory_url: char.armory_url ?? '' })
  formError.value = null
  showModal.value = true
}

function confirmRemove(char) {
  removeTarget.value = char
  showRemoveConfirm.value = true
}

function confirmDelete(char) {
  deleteTarget.value = char
  showDeleteConfirm.value = true
}

async function lookupFromWarmane() {
  if (!form.name || !form.realm) return
  lookingUp.value = true
  lookupResult.value = null
  formError.value = null
  try {
    const data = await warmaneApi.lookupCharacter(form.realm, form.name)
    if (data?.class_name) {
      form.class = data.class_name
      // Auto-populate default role from CLASS_ROLES
      const allowed = CLASS_ROLES[data.class_name] ?? []
      if (allowed.length > 0 && !form.role) {
        form.role = allowed[0]
      }
    }
    if (data?.armory_url) form.armory_url = data.armory_url
    if (data?.name) form.name = data.name
    // Auto-fill spec from talents
    if (data?.talents?.length) {
      form.spec = data.talents[0]?.tree || ''
      if (data.talents.length > 1) {
        form.secondary_spec = data.talents[1]?.tree || ''
      }
    }
    // Store warmane data for metadata on save
    warmaneData.value = data
    lookupResult.value = 'found'
  } catch {
    lookupResult.value = 'not_found'
  } finally {
    lookingUp.value = false
  }
}

const warmaneData = ref(null)

async function saveChar() {
  formError.value = null
  if (!guildStore.currentGuild) { formError.value = 'You need to join a guild first before adding characters'; return }
  if (!form.name || !form.class || !form.realm) { formError.value = 'Name, class and realm are required'; return }
  saving.value = true
  try {
    const payload = {
      name: form.name,
      class_name: form.class,
      realm_name: form.realm,
      default_role: form.role || undefined,
      primary_spec: form.spec || undefined,
      secondary_spec: form.secondary_spec || undefined,
      armory_url: form.armory_url || undefined,
    }
    // Include warmane metadata when creating from lookup
    if (!editingChar.value && warmaneData.value) {
      payload.metadata = {
        level: warmaneData.value.level,
        race: warmaneData.value.race,
        gender: warmaneData.value.gender,
        faction: warmaneData.value.faction,
        guild: warmaneData.value.guild,
        achievement_points: warmaneData.value.achievement_points,
        honorable_kills: warmaneData.value.honorable_kills,
        professions: warmaneData.value.professions || [],
        talents: warmaneData.value.talents || [],
        equipment: warmaneData.value.equipment || [],
        last_synced: new Date().toISOString(),
      }
    }
    if (editingChar.value) {
      const updated = await charApi.updateCharacter(guildStore.currentGuild.id, editingChar.value.id, payload)
      const idx = characters.value.findIndex(c => c.id === editingChar.value.id)
      if (idx !== -1) characters.value[idx] = mapChar(updated)
      uiStore.showToast('Character updated', 'success')
    } else {
      const created = await charApi.createCharacter(guildStore.currentGuild.id, payload)
      characters.value.push(mapChar(created))
      uiStore.showToast('Character added', 'success')
    }
    warmaneData.value = null
    showModal.value = false
  } catch (err) {
    formError.value = err?.response?.data?.error ?? 'Failed to save character'
  } finally {
    saving.value = false
  }
}

async function setMain(char) {
  try {
    await charApi.setMainCharacter(guildStore.currentGuild.id, char.id)
    characters.value.forEach(c => { c.is_main = c.id === char.id })
    uiStore.showToast(`${char.name} set as main`, 'success')
  } catch {
    uiStore.showToast('Failed to set main', 'error')
  }
}

async function syncFromWarmane(char) {
  syncing.value = char.id
  try {
    const updated = await warmaneApi.syncCharacter(char.id)
    const idx = characters.value.findIndex(c => c.id === char.id)
    if (idx !== -1) characters.value[idx] = mapChar(updated)
    uiStore.showToast(`${char.name} synced from Warmane`, 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? 'Sync failed — character may not exist on Warmane', 'error')
  } finally {
    syncing.value = null
  }
}

async function doArchive() {
  saving.value = true
  try {
    await charApi.archiveCharacter(guildStore.currentGuild.id, removeTarget.value.id)
    characters.value = characters.value.filter(c => c.id !== removeTarget.value.id)
    showRemoveConfirm.value = false
    uiStore.showToast('Character archived', 'success')
  } catch {
    uiStore.showToast('Failed to archive character', 'error')
  } finally {
    saving.value = false
  }
}

async function doDelete() {
  saving.value = true
  try {
    await charApi.deleteCharacter(guildStore.currentGuild.id, removeTarget.value.id)
    characters.value = characters.value.filter(c => c.id !== removeTarget.value.id)
    showRemoveConfirm.value = false
    uiStore.showToast('Character permanently deleted', 'success')
  } catch {
    uiStore.showToast('Failed to delete character', 'error')
  } finally {
    saving.value = false
  }
}

async function doUnarchive(char) {
  saving.value = true
  try {
    const restored = await charApi.unarchiveCharacter(guildStore.currentGuild.id, char.id)
    archivedCharacters.value = archivedCharacters.value.filter(c => c.id !== char.id)
    characters.value.push(mapChar(restored))
    uiStore.showToast(`${char.name} restored`, 'success')
  } catch {
    uiStore.showToast('Failed to restore character', 'error')
  } finally {
    saving.value = false
  }
}

async function doDeleteArchived() {
  saving.value = true
  try {
    await charApi.deleteCharacter(guildStore.currentGuild.id, deleteTarget.value.id)
    archivedCharacters.value = archivedCharacters.value.filter(c => c.id !== deleteTarget.value.id)
    showDeleteConfirm.value = false
    uiStore.showToast('Character permanently deleted', 'success')
  } catch {
    uiStore.showToast('Failed to delete character', 'error')
  } finally {
    saving.value = false
  }
}
</script>
