<template>
  <AppShell>
    <div class="p-4 md:p-6 space-y-6">
      <h1 class="wow-heading text-2xl">Guild Settings</h1>

      <div v-if="loading" class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="error" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">{{ error }}</div>

      <template v-else>
        <!-- Guild info form -->
        <WowCard>
          <h2 class="wow-heading text-base mb-4">Guild Information</h2>
          <form @submit.prevent="saveGuild" class="space-y-4 max-w-lg">
            <div>
              <label class="block text-xs text-text-muted mb-1">Guild Name *</label>
              <input v-model="form.name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">Realm *</label>
              <select v-model="form.realm" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
                <option value="">Select realm…</option>
                <option v-for="r in warmaneRealms" :key="r" :value="r">{{ r }}</option>
              </select>
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">Description</label>
              <textarea v-model="form.description" rows="3" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none resize-none" />
            </div>
            <div v-if="saveError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ saveError }}</div>
            <WowButton type="submit" :loading="saving">Save Changes</WowButton>
          </form>
        </WowCard>

        <!-- Warmane Guild Lookup -->
        <WowCard>
          <h2 class="wow-heading text-base mb-4">Warmane Guild Info</h2>
          <p class="text-text-muted text-sm mb-4">Fetch guild roster and info from the Warmane armory API.</p>
          <form @submit.prevent="fetchWarmaneGuild" class="flex items-end gap-3 max-w-lg">
            <div class="flex-1">
              <label class="block text-xs text-text-muted mb-1">Guild Name</label>
              <input v-model="warmaneGuildName" :placeholder="form.name || 'Guild name'" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
            </div>
            <div class="w-40">
              <label class="block text-xs text-text-muted mb-1">Realm</label>
              <select v-model="warmaneGuildRealm" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
                <option v-for="r in warmaneRealms" :key="r" :value="r">{{ r }}</option>
              </select>
            </div>
            <WowButton type="submit" :loading="fetchingWarmane" variant="secondary">Fetch</WowButton>
          </form>

          <div v-if="warmaneError" class="mt-4 p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ warmaneError }}</div>

          <div v-if="warmaneGuildData" class="mt-4 space-y-3">
            <div class="flex items-center gap-4 text-sm">
              <span class="text-text-muted">Guild:</span>
              <span class="text-text-primary font-medium">{{ warmaneGuildData.name }}</span>
              <span v-if="warmaneGuildData.faction" class="px-2 py-0.5 rounded text-xs font-medium"
                :class="warmaneGuildData.faction === 'Alliance' ? 'bg-blue-900/50 text-blue-300 border border-blue-600' : 'bg-red-900/50 text-red-300 border border-red-600'"
              >{{ warmaneGuildData.faction }}</span>
              <span class="text-text-muted">{{ warmaneGuildData.member_count }} members</span>
            </div>

            <div v-if="warmaneGuildData.roster?.length" class="overflow-x-auto max-h-64 overflow-y-auto">
              <table class="w-full text-xs">
                <thead class="sticky top-0">
                  <tr class="bg-bg-tertiary border-b border-border-default">
                    <th class="text-left px-3 py-2 text-text-muted uppercase">Name</th>
                    <th class="text-left px-3 py-2 text-text-muted uppercase">Class</th>
                    <th class="text-left px-3 py-2 text-text-muted uppercase">Level</th>
                    <th class="text-left px-3 py-2 text-text-muted uppercase">Race</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border-default">
                  <tr v-for="ch in warmaneGuildData.roster" :key="ch.name" class="hover:bg-bg-tertiary/50">
                    <td class="px-3 py-1.5 text-text-primary">{{ ch.name }}</td>
                    <td class="px-3 py-1.5 text-text-muted">{{ ch.class_name }}</td>
                    <td class="px-3 py-1.5 text-text-muted">{{ ch.level }}</td>
                    <td class="px-3 py-1.5 text-text-muted">{{ ch.race }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </WowCard>

        <!-- Members table -->
        <WowCard>
          <div class="flex items-center justify-between mb-4">
            <h2 class="wow-heading text-base">Members ({{ members.length }})</h2>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-bg-tertiary border-b border-border-default">
                  <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Username</th>
                  <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Role</th>
                  <th class="text-right px-4 py-2.5 text-xs text-text-muted uppercase">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-default">
                <tr v-for="m in members" :key="m.id" class="hover:bg-bg-tertiary/50 transition-colors">
                  <td class="px-4 py-2.5 text-text-primary font-medium">{{ m.username ?? m.user?.username }}</td>
                  <td class="px-4 py-2.5">
                    <select
                      :value="m.role"
                      class="bg-bg-tertiary border border-border-default text-text-primary text-xs rounded px-2 py-1 focus:border-border-gold outline-none"
                      @change="updateRole(m, $event.target.value)"
                    >
                      <option value="member">Member</option>
                      <option value="officer">Officer</option>
                      <option value="guild_admin">Admin</option>
                    </select>
                  </td>
                  <td class="px-4 py-2.5 text-right">
                    <WowButton variant="danger" class="text-xs py-1 px-2" @click="confirmKick(m)">
                      Remove
                    </WowButton>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </WowCard>
      </template>
    </div>

    <!-- Kick confirmation -->
    <WowModal v-model="showKickConfirm" title="Remove Member" size="sm">
      <p class="text-text-muted">Remove <strong class="text-text-primary">{{ kickTarget?.username ?? kickTarget?.user?.username }}</strong> from the guild?</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showKickConfirm = false">Cancel</WowButton>
          <WowButton variant="danger" :loading="saving" @click="doKick">Remove</WowButton>
        </div>
      </template>
    </WowModal>
  </AppShell>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import { useGuildStore } from '@/stores/guild'
import { useUiStore } from '@/stores/ui'
import { WARMANE_REALMS } from '@/constants'
import * as guildsApi from '@/api/guilds'
import * as warmaneApi from '@/api/warmane'

const guildStore = useGuildStore()
const uiStore = useUiStore()

const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const saveError = ref(null)
const members = ref([])
const showKickConfirm = ref(false)
const kickTarget = ref(null)

const form = reactive({ name: '', realm: '', description: '' })
const warmaneRealms = WARMANE_REALMS

async function loadGuildData() {
  loading.value = true
  error.value = null
  try {
    const g = guildStore.currentGuild
    if (g) {
      Object.assign(form, { name: g.name ?? '', realm: g.realm_name ?? '', description: g.description ?? '' })
      await guildStore.fetchMembers(g.id)
      members.value = guildStore.members
    }
  } catch {
    error.value = 'Failed to load guild settings'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  if (!guildStore.currentGuild) await guildStore.fetchGuilds()
  await loadGuildData()
})

// Reload settings when guild changes from sidebar dropdown
watch(
  () => guildStore.currentGuild?.id,
  (newId, oldId) => {
    if (newId && newId !== oldId) {
      loadGuildData()
    }
  }
)

async function saveGuild() {
  saveError.value = null
  saving.value = true
  try {
    const updated = await guildsApi.updateGuild(guildStore.currentGuild.id, {
      name: form.name,
      realm_name: form.realm,
    })
    guildStore.currentGuild = updated
    uiStore.showToast('Guild settings saved', 'success')
  } catch (err) {
    saveError.value = err?.response?.data?.message ?? 'Failed to save'
  } finally {
    saving.value = false
  }
}

async function updateRole(member, role) {
  try {
    await guildsApi.updateMemberRole(guildStore.currentGuild.id, member.user_id, role)
    member.role = role
    uiStore.showToast('Role updated', 'success')
  } catch {
    uiStore.showToast('Failed to update role', 'error')
  }
}

function confirmKick(member) {
  kickTarget.value = member
  showKickConfirm.value = true
}

async function doKick() {
  saving.value = true
  try {
    await guildsApi.removeMember(guildStore.currentGuild.id, kickTarget.value.user_id)
    members.value = members.value.filter(m => m.user_id !== kickTarget.value.user_id)
    showKickConfirm.value = false
    uiStore.showToast('Member removed', 'success')
  } catch {
    uiStore.showToast('Failed to remove member', 'error')
  } finally {
    saving.value = false
  }
}

// Warmane guild lookup
const warmaneGuildName = ref('')
const warmaneGuildRealm = ref('Icecrown')
const fetchingWarmane = ref(false)
const warmaneError = ref(null)
const warmaneGuildData = ref(null)

async function fetchWarmaneGuild() {
  warmaneError.value = null
  warmaneGuildData.value = null
  const name = warmaneGuildName.value || form.name
  const realm = warmaneGuildRealm.value || form.realm
  if (!name || !realm) {
    warmaneError.value = 'Guild name and realm are required'
    return
  }
  fetchingWarmane.value = true
  try {
    warmaneGuildData.value = await warmaneApi.lookupGuild(realm, name)
  } catch (err) {
    warmaneError.value = err?.response?.data?.message ?? 'Guild not found on Warmane'
  } finally {
    fetchingWarmane.value = false
  }
}
</script>
