<template>
  <div class="space-y-6">
    <WowCard>
      <div class="flex items-center justify-between gap-2 mb-4">
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-accent-gold flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h2 class="text-sm font-semibold text-text-primary">Guild Realms</h2>
            <p class="text-xs text-text-muted mt-0.5">Manage realms available for your guild members.</p>
          </div>
        </div>
      </div>

      <div v-if="loading" class="py-4 text-center">
        <div class="w-5 h-5 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin mx-auto" />
      </div>

      <div v-else>
        <!-- Realm list -->
        <div v-if="realms.length === 0" class="py-6 text-center">
          <p class="text-sm text-text-muted">No realms configured. Add one below.</p>
        </div>
        <div v-else class="space-y-2 mb-6">
          <div
            v-for="realm in realms"
            :key="realm.id"
            class="p-3 rounded-lg border transition-colors flex items-center justify-between gap-2"
            :class="realm.is_default
              ? 'bg-accent-gold/5 border-accent-gold/30'
              : 'bg-bg-tertiary border-border-default'"
          >
            <div class="flex items-center gap-2">
              <template v-if="editingId === realm.id">
                <input
                  v-model="editName"
                  class="bg-bg-tertiary border border-border-default text-text-primary rounded px-2 py-1 text-sm focus:border-border-gold outline-none w-40"
                  @keyup.enter="doSaveEdit(realm)"
                />
              </template>
              <template v-else>
                <span class="text-sm font-medium text-text-primary">{{ realm.name }}</span>
              </template>
              <span v-if="realm.is_default" class="text-[10px] px-1.5 py-0.5 rounded bg-accent-gold/20 text-accent-gold border border-accent-gold/30">
                Default
              </span>
            </div>
            <div class="flex items-center gap-2">
              <template v-if="editingId === realm.id">
                <WowButton class="text-xs py-1 px-2" :loading="saving" @click="doSaveEdit(realm)">Save</WowButton>
                <WowButton variant="secondary" class="text-xs py-1 px-2" @click="cancelEdit">Cancel</WowButton>
              </template>
              <template v-else>
                <WowButton
                  v-if="!realm.is_default"
                  variant="secondary"
                  class="text-xs py-1 px-2"
                  :loading="settingDefaultId === realm.id"
                  @click="doSetDefault(realm)"
                >Set Default</WowButton>
                <WowButton variant="secondary" class="text-xs py-1 px-2" @click="startEdit(realm)">Edit</WowButton>
                <WowButton variant="danger" class="text-xs py-1 px-2" :loading="removingId === realm.id" @click="doRemove(realm)">✕</WowButton>
              </template>
            </div>
          </div>
        </div>

        <!-- Add realm form -->
        <div class="border-t border-border-default pt-4">
          <h3 class="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Add Realm</h3>
          <form @submit.prevent="doAdd" class="flex items-end gap-3 max-w-lg">
            <div class="flex-1">
              <label class="block text-xs text-text-muted mb-1">Realm Name</label>
              <input
                v-model="newName"
                required
                class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
                placeholder="e.g. Icecrown"
              />
            </div>
            <label class="flex items-center gap-2 text-sm text-text-primary cursor-pointer pb-2">
              <input v-model="newIsDefault" type="checkbox" class="rounded border-border-default bg-bg-tertiary" />
              Default
            </label>
            <WowButton type="submit" :loading="adding" :disabled="!newName.trim()">Add</WowButton>
          </form>
        </div>
      </div>
    </WowCard>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import { useGuildStore } from '@/stores/guild'
import { useUiStore } from '@/stores/ui'
import * as guildRealmsApi from '@/api/guild_realms'

const guildStore = useGuildStore()
const uiStore = useUiStore()

const loading = ref(false)
const realms = ref([])
const saving = ref(false)
const adding = ref(false)
const removingId = ref(null)
const settingDefaultId = ref(null)

// Add form
const newName = ref('')
const newIsDefault = ref(false)

// Edit state
const editingId = ref(null)
const editName = ref('')

async function loadRealms() {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  loading.value = true
  try {
    const data = await guildRealmsApi.getGuildRealms(guildId)
    realms.value = data.realms || []
  } catch {
    uiStore.showToast('Failed to load realms', 'error')
  }
  loading.value = false
}

async function doAdd() {
  const guildId = guildStore.currentGuildId
  if (!guildId || !newName.value.trim()) return
  adding.value = true
  try {
    await guildRealmsApi.addGuildRealm(guildId, {
      name: newName.value.trim(),
      is_default: newIsDefault.value,
    })
    uiStore.showToast('Realm added', 'success')
    newName.value = ''
    newIsDefault.value = false
    await loadRealms()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || 'Failed to add realm', 'error')
  }
  adding.value = false
}

function startEdit(realm) {
  editingId.value = realm.id
  editName.value = realm.name
}

function cancelEdit() {
  editingId.value = null
  editName.value = ''
}

async function doSaveEdit(realm) {
  const guildId = guildStore.currentGuildId
  if (!guildId || !editName.value.trim()) return
  saving.value = true
  try {
    await guildRealmsApi.updateGuildRealm(guildId, realm.id, { name: editName.value.trim() })
    uiStore.showToast('Realm updated', 'success')
    editingId.value = null
    editName.value = ''
    await loadRealms()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || 'Failed to update realm', 'error')
  }
  saving.value = false
}

async function doSetDefault(realm) {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  settingDefaultId.value = realm.id
  try {
    await guildRealmsApi.updateGuildRealm(guildId, realm.id, { is_default: true })
    uiStore.showToast(`${realm.name} set as default`, 'success')
    await loadRealms()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || 'Failed to set default', 'error')
  }
  settingDefaultId.value = null
}

async function doRemove(realm) {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  removingId.value = realm.id
  try {
    await guildRealmsApi.removeGuildRealm(guildId, realm.id)
    uiStore.showToast('Realm removed', 'success')
    await loadRealms()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || 'Failed to remove realm', 'error')
  }
  removingId.value = null
}

onMounted(loadRealms)
</script>
