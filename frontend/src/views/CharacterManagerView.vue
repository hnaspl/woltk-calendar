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

      <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="i in 3" :key="i" class="h-24 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      </div>

      <div v-else-if="error" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">
        {{ error }}
      </div>

      <div v-else-if="characters.length === 0" class="text-center py-12 text-text-muted">
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

          <div class="flex items-center gap-3 mb-3">
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

          <div class="flex flex-wrap gap-1.5 mb-2">
            <ClassBadge :class-name="char.class" />
            <RoleBadge v-if="char.role" :role="char.role" />
            <SpecBadge v-if="char.spec" :spec="char.spec" />
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
              @click="confirmArchive(char)"
            >✕</WowButton>
          </div>
        </WowCard>
      </div>
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
            <span v-if="lookupResult === 'found'" class="text-xs text-green-400">✓ Found — class & armory URL filled in</span>
            <span v-else-if="lookupResult === 'not_found'" class="text-xs text-yellow-400">Not found on Warmane — fill in manually below</span>
          </div>
        </div>

        <div>
          <label class="block text-xs text-text-muted mb-1">Character Name *</label>
          <input v-model="form.name" required placeholder="Arthas" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Class *</label>
          <select v-model="form.class" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option value="">Select class…</option>
            <option v-for="c in wowClasses" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Realm *</label>
          <select v-model="form.realm" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option value="">Select realm…</option>
            <option v-for="r in warmaneRealms" :key="r" :value="r">{{ r }}</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Role</label>
          <select v-model="form.role" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option value="">Select role…</option>
            <option value="tank">Tank</option>
            <option value="healer">Healer</option>
            <option value="dps">DPS</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Spec</label>
          <input v-model="form.spec" placeholder="e.g. Frost, Holy…" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">Secondary Spec</label>
          <input v-model="form.secondary_spec" placeholder="e.g. Unholy, Protection…" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
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

    <!-- Archive confirmation -->
    <WowModal v-model="showArchiveConfirm" title="Archive Character" size="sm">
      <p class="text-text-muted">Archive <strong class="text-text-primary">{{ archiveTarget?.name }}</strong>? They will no longer appear in signups.</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showArchiveConfirm = false">Cancel</WowButton>
          <WowButton variant="danger" :loading="saving" @click="doArchive">Archive</WowButton>
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
import ClassBadge from '@/components/common/ClassBadge.vue'
import RoleBadge from '@/components/common/RoleBadge.vue'
import SpecBadge from '@/components/common/SpecBadge.vue'
import { useGuildStore } from '@/stores/guild'
import { useUiStore } from '@/stores/ui'
import { useWowIcons } from '@/composables/useWowIcons'
import * as charApi from '@/api/characters'
import * as warmaneApi from '@/api/warmane'

const guildStore = useGuildStore()
const uiStore = useUiStore()
const { getClassIcon } = useWowIcons()

const characters = ref([])
const loading = ref(true)
const saving = ref(false)
const syncing = ref(null)
const lookingUp = ref(false)
const lookupResult = ref(null)
const error = ref(null)
const formError = ref(null)
const showModal = ref(false)
const showArchiveConfirm = ref(false)
const editingChar = ref(null)
const archiveTarget = ref(null)

const wowClasses = ['Death Knight', 'Druid', 'Hunter', 'Mage', 'Paladin', 'Priest', 'Rogue', 'Shaman', 'Warlock', 'Warrior']
const warmaneRealms = ['Icecrown', 'Lordaeron', 'Onyxia', 'Blackrock', 'Frostwolf', 'Frostmourne', 'Neltharion']

const form = reactive({ name: '', class: '', realm: '', role: '', spec: '', secondary_spec: '', armory_url: '' })

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
  try {
    const raw = await charApi.getMyCharacters(guildStore.currentGuild?.id)
    characters.value = (Array.isArray(raw) ? raw : []).map(mapChar)
  } catch (err) {
    error.value = 'Failed to load characters'
  } finally {
    loading.value = false
  }
})

function openAddModal() {
  editingChar.value = null
  Object.assign(form, { name: '', class: '', realm: '', role: '', spec: '', secondary_spec: '', armory_url: '' })
  formError.value = null
  lookingUp.value = false
  lookupResult.value = null
  showModal.value = true
}

function openEditModal(char) {
  editingChar.value = char
  Object.assign(form, { name: char.name, class: char.class, realm: char.realm, role: char.role ?? '', spec: char.spec ?? '', secondary_spec: char.secondary_spec ?? '', armory_url: char.armory_url ?? '' })
  formError.value = null
  showModal.value = true
}

function confirmArchive(char) {
  archiveTarget.value = char
  showArchiveConfirm.value = true
}

async function lookupFromWarmane() {
  if (!form.name || !form.realm) return
  lookingUp.value = true
  lookupResult.value = null
  formError.value = null
  try {
    const data = await warmaneApi.lookupCharacter(form.realm, form.name)
    if (data?.class_name) form.class = data.class_name
    if (data?.armory_url) form.armory_url = data.armory_url
    if (data?.name) form.name = data.name
    lookupResult.value = 'found'
  } catch {
    lookupResult.value = 'not_found'
  } finally {
    lookingUp.value = false
  }
}

async function saveChar() {
  formError.value = null
  if (!form.name || !form.class || !form.realm) { formError.value = 'Name, class and realm are required'; return }
  saving.value = true
  try {
    const payload = {
      name: form.name,
      class_name: form.class,
      realm_name: form.realm,
      default_role: form.role || 'dps',
      primary_spec: form.spec || undefined,
      secondary_spec: form.secondary_spec || undefined,
      armory_url: form.armory_url || undefined,
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
    await charApi.archiveCharacter(guildStore.currentGuild.id, archiveTarget.value.id)
    characters.value = characters.value.filter(c => c.id !== archiveTarget.value.id)
    showArchiveConfirm.value = false
    uiStore.showToast('Character archived', 'success')
  } catch {
    uiStore.showToast('Failed to archive character', 'error')
  } finally {
    saving.value = false
  }
}
</script>
