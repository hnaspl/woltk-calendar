<template>
  <div class="space-y-6">
    <!-- Members table -->
    <WowCard>
      <div class="flex items-center justify-between mb-4">
        <h2 class="wow-heading text-base">Members ({{ members.length }})</h2>
        <WowButton v-if="permissions.can('manage_guild_members')" variant="secondary" class="text-xs py-1 px-3" @click="showAddMember = true">
          + Add Member
        </WowButton>
      </div>

      <div v-if="loading" class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-bg-tertiary border-b border-border-default">
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Username</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Role</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Joined</th>
              <th class="text-right px-4 py-2.5 text-xs text-text-muted uppercase">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-default">
            <tr v-for="m in members" :key="m.id" class="hover:bg-bg-tertiary/50 transition-colors">
              <td class="px-4 py-2.5">
                <div class="text-text-primary font-medium">{{ m.username ?? m.user?.username }}</div>
                <div v-if="m.user_id === authStore.user?.id" class="text-[10px] text-accent-gold">You</div>
              </td>
              <td class="px-4 py-2.5">
                <select
                  :value="m.role"
                  :disabled="!canChangeRole(m)"
                  class="bg-bg-tertiary border border-border-default text-text-primary text-xs rounded px-2 py-1 focus:border-border-gold outline-none disabled:opacity-50"
                  @change="updateRole(m, $event.target.value)"
                >
                  <option v-for="r in roleOptionsForMember(m)" :key="r.name" :value="r.name">{{ r.display_name }}</option>
                </select>
              </td>
              <td class="px-4 py-2.5 text-text-muted text-xs">{{ formatDate(m.joined_at ?? m.created_at) }}</td>
              <td class="px-4 py-2.5 text-right space-x-2">
                <WowButton variant="ghost" class="text-xs py-1 px-2" @click="viewMemberChars(m)">
                  Characters
                </WowButton>
                <WowButton v-if="canChangeRole(m)" variant="danger" class="text-xs py-1 px-2" @click="confirmKick(m)">
                  Remove
                </WowButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WowCard>

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

    <!-- Add Member modal -->
    <WowModal v-model="showAddMember" title="Add Member" size="sm">
      <div class="space-y-3">
        <!-- Warmane roster fetch for Warmane-sourced guilds -->
        <div v-if="isWarmaneSource">
          <div class="flex items-center justify-between mb-2">
            <p class="text-xs text-text-muted">Fetch guild roster from Warmane to find members.</p>
            <WowButton variant="secondary" class="text-xs py-1 px-3" :loading="fetchingRoster" @click="fetchWarmaneRoster">
              {{ fetchingRoster ? 'Fetching…' : 'Fetch Roster' }}
            </WowButton>
          </div>
          <div v-if="warmaneRosterError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ warmaneRosterError }}</div>
          <div v-if="warmaneRoster.length > 0" class="space-y-1">
            <label class="block text-xs text-text-muted mb-1">Filter by name</label>
            <input
              v-model="rosterFilter"
              placeholder="Type to filter…"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none mb-2"
            />
            <div class="max-h-48 overflow-y-auto space-y-1">
              <button
                v-for="ch in filteredRoster"
                :key="ch.name"
                type="button"
                class="w-full flex items-center justify-between px-3 py-2 rounded bg-bg-tertiary/60 hover:bg-bg-tertiary transition-colors text-sm"
                @click="doAddMemberByName(ch.name)"
              >
                <div>
                  <span class="text-text-primary">{{ ch.name }}</span>
                  <span class="text-text-muted text-xs ml-2">{{ ch.class_name }} · Lv{{ ch.level }}</span>
                </div>
                <span class="text-xs text-accent-gold">Add</span>
              </button>
            </div>
            <p v-if="rosterFilter && filteredRoster.length === 0" class="text-xs text-text-muted py-2">No matching characters.</p>
          </div>
          <!-- Multi-match user selection (shown when a roster click finds multiple users) -->
          <div v-if="availableUsers.length > 0" class="mt-3 space-y-1">
            <p class="text-xs text-text-muted">Multiple users match "{{ addMemberQuery }}" — select one:</p>
            <div class="max-h-40 overflow-y-auto space-y-1">
              <button
                v-for="u in availableUsers"
                :key="u.id"
                type="button"
                class="w-full flex items-center justify-between px-3 py-2 rounded bg-bg-tertiary/60 hover:bg-bg-tertiary transition-colors text-sm"
                @click="doAddMember(u)"
              >
                <span class="text-text-primary">{{ u.username }}</span>
                <span class="text-xs text-accent-gold">Add</span>
              </button>
            </div>
          </div>
        </div>
        <!-- Standard search for non-Warmane guilds -->
        <div v-else>
          <label class="block text-xs text-text-muted mb-1">Search by username</label>
          <input
            v-model="addMemberQuery"
            placeholder="Type username…"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
            @input="searchUsers"
          />
        </div>
        <div v-if="searchingUsers" class="text-xs text-text-muted">Searching…</div>
        <div v-if="availableUsers.length > 0 && !isWarmaneSource" class="max-h-40 overflow-y-auto space-y-1">
          <button
            v-for="u in availableUsers"
            :key="u.id"
            type="button"
            class="w-full flex items-center justify-between px-3 py-2 rounded bg-bg-tertiary/60 hover:bg-bg-tertiary transition-colors text-sm"
            @click="doAddMember(u)"
          >
            <span class="text-text-primary">{{ u.username }}</span>
            <span class="text-xs text-accent-gold">Add</span>
          </button>
        </div>
        <div v-else-if="addMemberQuery.length >= 2 && !searchingUsers && !isWarmaneSource" class="text-xs text-text-muted">
          No matching users found.
        </div>
      </div>
    </WowModal>

    <!-- Member Characters modal -->
    <WowModal v-model="showMemberChars" :title="memberCharsTitle" size="md">
      <div v-if="loadingMemberChars" class="py-6 text-center text-text-muted">Loading characters…</div>
      <div v-else-if="memberChars.length === 0" class="py-6 text-center text-text-muted">No characters found for this member.</div>
      <div v-else class="overflow-x-auto max-h-72 overflow-y-auto">
        <table class="w-full text-xs">
          <thead class="sticky top-0">
            <tr class="bg-bg-tertiary border-b border-border-default">
              <th class="text-left px-3 py-2 text-text-muted uppercase">Name</th>
              <th class="text-left px-3 py-2 text-text-muted uppercase">Class</th>
              <th class="text-left px-3 py-2 text-text-muted uppercase">Main</th>
              <th class="text-left px-3 py-2 text-text-muted uppercase">Default Role</th>
              <th class="text-left px-3 py-2 text-text-muted uppercase">Primary Spec</th>
              <th class="text-left px-3 py-2 text-text-muted uppercase">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-default">
            <tr v-for="c in memberChars" :key="c.id" class="hover:bg-bg-tertiary/50">
              <td class="px-3 py-1.5 text-text-primary font-medium">{{ c.name }}</td>
              <td class="px-3 py-1.5 text-text-muted">{{ c.class_name }}</td>
              <td class="px-3 py-1.5">
                <span v-if="c.is_main" class="text-accent-gold text-[10px] font-bold uppercase">Main</span>
                <span v-else class="text-text-muted text-[10px]">Alt</span>
              </td>
              <td class="px-3 py-1.5 text-text-muted">{{ c.default_role || '—' }}</td>
              <td class="px-3 py-1.5 text-text-muted">{{ c.primary_spec || '—' }}</td>
              <td class="px-3 py-1.5">
                <span v-if="c.is_active !== false && !c.archived_at" class="text-green-400 text-[10px]">Active</span>
                <span v-else class="text-red-400 text-[10px]">Archived</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WowModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import { useGuildStore } from '@/stores/guild'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { usePermissions } from '@/composables/usePermissions'
import * as guildsApi from '@/api/guilds'
import * as warmaneApi from '@/api/warmane'
import api from '@/api'

const guildStore = useGuildStore()
const uiStore = useUiStore()
const authStore = useAuthStore()
const permissions = usePermissions()

const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const members = ref([])
const allRoles = ref([])
const showKickConfirm = ref(false)
const kickTarget = ref(null)

const isWarmaneSource = computed(() => !!guildStore.currentGuild?.warmane_source)

async function fetchRoles() {
  try {
    allRoles.value = await api.get('/roles')
  } catch {
    allRoles.value = []
  }
}

const grantableRoles = computed(() => {
  const myRole = permissions.role.value
  if (!myRole && !permissions.can('manage_roles')) return []
  if (permissions.can('manage_roles') && !myRole) return allRoles.value
  const myRoleDef = allRoles.value.find(r => r.name === myRole)
  if (!myRoleDef) return allRoles.value
  const grantable = new Set(myRoleDef.can_grant || [])
  return allRoles.value.filter(r => grantable.has(r.name))
})

function roleOptionsForMember(member) {
  const options = [...grantableRoles.value]
  if (member.role && !options.find(r => r.name === member.role)) {
    const currentRoleDef = allRoles.value.find(r => r.name === member.role)
    if (currentRoleDef) options.push(currentRoleDef)
  }
  return options.sort((a, b) => a.level - b.level)
}

function canChangeRole(member) {
  if (member.user_id === authStore.user?.id) return false
  if (!permissions.can('update_member_roles')) return false
  const myRole = permissions.role.value
  const myRoleDef = allRoles.value.find(r => r.name === myRole)
  const memberRoleDef = allRoles.value.find(r => r.name === member.role)
  if (permissions.can('manage_roles') && !myRoleDef) return true
  if (!myRoleDef || !memberRoleDef) return false
  return myRoleDef.level > memberRoleDef.level
}

async function loadMembers() {
  loading.value = true
  error.value = null
  try {
    const g = guildStore.currentGuild
    if (g) {
      await Promise.all([
        guildStore.fetchMembers(g.id),
        fetchRoles()
      ])
      members.value = guildStore.members
    }
  } catch {
    error.value = 'Failed to load members'
  } finally {
    loading.value = false
  }
}

onMounted(loadMembers)

watch(
  () => guildStore.currentGuild?.id,
  (newId, oldId) => {
    if (newId && newId !== oldId) loadMembers()
  }
)

async function updateRole(member, role) {
  try {
    await guildsApi.updateMemberRole(guildStore.currentGuild.id, member.user_id, role)
    member.role = role
    uiStore.showToast('Role updated', 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? 'Failed to update role', 'error')
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

// Member characters viewer
const showMemberChars = ref(false)
const memberChars = ref([])
const loadingMemberChars = ref(false)
const memberCharsTitle = ref('Member Characters')

async function viewMemberChars(member) {
  const username = member.username ?? member.user?.username ?? 'Unknown'
  memberCharsTitle.value = `${username}'s Characters`
  showMemberChars.value = true
  loadingMemberChars.value = true
  memberChars.value = []
  try {
    memberChars.value = await guildsApi.getMemberCharacters(guildStore.currentGuild.id, member.user_id)
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? 'Failed to load characters', 'error')
  } finally {
    loadingMemberChars.value = false
  }
}

// Add member
const showAddMember = ref(false)
const addMemberQuery = ref('')
const availableUsers = ref([])
const searchingUsers = ref(false)
let searchTimeout = null

function searchUsers() {
  clearTimeout(searchTimeout)
  if (addMemberQuery.value.length < 2) {
    availableUsers.value = []
    return
  }
  searchingUsers.value = true
  searchTimeout = setTimeout(async () => {
    try {
      availableUsers.value = await guildsApi.getAvailableUsers(
        guildStore.currentGuild.id,
        addMemberQuery.value
      )
    } catch (err) {
      availableUsers.value = []
      uiStore.showToast(err?.response?.data?.message ?? 'Failed to search users', 'error')
    } finally {
      searchingUsers.value = false
    }
  }, 300)
}

async function doAddMember(user) {
  try {
    await guildsApi.addMember(guildStore.currentGuild.id, user.id)
    await guildStore.fetchMembers(guildStore.currentGuild.id)
    members.value = guildStore.members
    showAddMember.value = false
    addMemberQuery.value = ''
    availableUsers.value = []
    uiStore.showToast(`${user.username} added to guild`, 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.message ?? 'Failed to add member', 'error')
  }
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

// Warmane roster fetch
const fetchingRoster = ref(false)
const warmaneRoster = ref([])
const warmaneRosterError = ref(null)
const rosterFilter = ref('')

const filteredRoster = computed(() => {
  if (!rosterFilter.value) return warmaneRoster.value
  const q = rosterFilter.value.toLowerCase()
  return warmaneRoster.value.filter(ch => ch.name.toLowerCase().includes(q))
})

async function fetchWarmaneRoster() {
  const g = guildStore.currentGuild
  if (!g) return
  fetchingRoster.value = true
  warmaneRosterError.value = null
  try {
    const data = await warmaneApi.lookupGuild(g.realm_name, g.name)
    warmaneRoster.value = data.roster || []
  } catch (err) {
    warmaneRosterError.value = err?.response?.data?.message ?? 'Failed to fetch guild roster from Warmane'
  } finally {
    fetchingRoster.value = false
  }
}

async function doAddMemberByName(characterName) {
  try {
    // Search for a user account matching this character name
    const users = await guildsApi.getAvailableUsers(guildStore.currentGuild.id, characterName)
    if (users.length === 1) {
      await doAddMember(users[0])
    } else if (users.length > 1) {
      // Show available matches for manual selection
      availableUsers.value = users
      addMemberQuery.value = characterName
      uiStore.showToast(`Multiple users match "${characterName}" — select one below.`, 'info')
    } else {
      uiStore.showToast(`No registered user found for "${characterName}". They need to create an account first.`, 'info')
    }
  } catch (err) {
    uiStore.showToast(err?.response?.data?.message ?? 'Failed to add member', 'error')
  }
}
</script>
