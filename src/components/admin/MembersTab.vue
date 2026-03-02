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
                <button
                  class="inline-flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded bg-accent-gold/15 text-accent-gold border border-accent-gold/40 hover:bg-accent-gold/25 hover:border-accent-gold/70 transition-colors"
                  @click="viewMemberChars(m)"
                >
                  📋 Characters
                </button>
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
                <div class="flex items-center gap-2">
                  <img :src="getClassIcon(ch.class_name)" :alt="ch.class_name" class="w-5 h-5 rounded flex-shrink-0" />
                  <span class="font-medium" :style="{ color: getClassColor(ch.class_name) }">{{ ch.name }}</span>
                  <span class="text-text-muted text-xs">{{ ch.class_name }} · Lv{{ ch.level }}</span>
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
    <WowModal v-model="showMemberChars" :title="memberCharsTitle" size="lg">
      <div v-if="loadingMemberChars" class="py-6 text-center text-text-muted">Loading characters…</div>
      <div v-else-if="memberChars.length === 0" class="py-6 text-center text-text-muted">No characters found for this member.</div>
      <div v-else class="overflow-x-auto max-h-96 overflow-y-auto">
        <table class="w-full text-sm">
          <thead class="sticky top-0 z-10">
            <tr class="bg-bg-tertiary border-b border-border-default">
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Character</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Role</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Primary Spec</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Secondary Spec</th>
              <th class="text-center px-4 py-2.5 text-xs text-text-muted uppercase">Type</th>
              <th class="text-center px-4 py-2.5 text-xs text-text-muted uppercase">Status</th>
              <th class="text-right px-4 py-2.5 text-xs text-text-muted uppercase">Details</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-default">
            <tr v-for="c in memberChars" :key="c.id" class="hover:bg-bg-tertiary/50 transition-colors">
              <td class="px-4 py-2.5">
                <div class="flex items-center gap-2">
                  <img :src="getClassIcon(c.class_name)" :alt="c.class_name" class="w-6 h-6 rounded flex-shrink-0" />
                  <div>
                    <span class="font-medium cursor-pointer hover:underline" :style="{ color: getClassColor(c.class_name) }" @click="openCharDetailModal(c)">{{ c.name }}</span>
                    <span class="text-text-muted text-xs ml-1.5">{{ c.class_name }}</span>
                  </div>
                </div>
              </td>
              <td class="px-4 py-2.5 text-text-muted text-xs capitalize">{{ c.default_role?.replace('_', ' ') || '—' }}</td>
              <td class="px-4 py-2.5">
                <div v-if="c.primary_spec" class="flex items-center gap-1.5">
                  <img v-if="getSpecIcon(c.primary_spec, c.class_name)" :src="getSpecIcon(c.primary_spec, c.class_name)" class="w-4 h-4 rounded" />
                  <span class="text-text-primary text-xs">{{ c.primary_spec }}</span>
                </div>
                <span v-else class="text-text-muted text-xs">—</span>
              </td>
              <td class="px-4 py-2.5">
                <div v-if="c.secondary_spec" class="flex items-center gap-1.5">
                  <img v-if="getSpecIcon(c.secondary_spec, c.class_name)" :src="getSpecIcon(c.secondary_spec, c.class_name)" class="w-4 h-4 rounded" />
                  <span class="text-text-muted text-xs">{{ c.secondary_spec }}</span>
                </div>
                <span v-else class="text-text-muted text-xs">—</span>
              </td>
              <td class="px-4 py-2.5 text-center">
                <span v-if="c.is_main" class="text-accent-gold text-[10px] font-bold uppercase px-1.5 py-0.5 bg-accent-gold/10 rounded">Main</span>
                <span v-else class="text-text-muted text-[10px] px-1.5 py-0.5 bg-bg-secondary rounded">Alt</span>
              </td>
              <td class="px-4 py-2.5 text-center">
                <span v-if="c.is_active !== false && !c.archived_at" class="text-green-400 text-[10px] font-medium px-1.5 py-0.5 bg-green-400/10 rounded">Active</span>
                <span v-else class="text-red-400 text-[10px] font-medium px-1.5 py-0.5 bg-red-400/10 rounded">Archived</span>
              </td>
              <td class="px-4 py-2.5 text-right">
                <WowButton variant="secondary" class="text-xs py-1 px-2" @click="openCharDetailModal(c)">
                  🔍 View
                </WowButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WowModal>

    <!-- Character Detail Modal -->
    <CharacterDetailModal
      v-model="showCharDetailModal"
      :character="charDetailTarget"
      :use-wowhead="systemSettings.wowheadEnabled()"
    />

    <!-- Transfer Ownership button -->
    <WowCard v-if="canTransferOwnership">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="wow-heading text-base">Guild Ownership</h2>
          <p class="text-xs text-text-muted mt-1">Transfer ownership of this guild to another member.</p>
        </div>
        <WowButton variant="danger" class="text-xs py-1.5 px-3" @click="showTransferModal = true">
          👑 Transfer Ownership
        </WowButton>
      </div>
    </WowCard>

    <!-- Transfer Ownership modal -->
    <WowModal v-model="showTransferModal" title="👑 Transfer Guild Ownership" size="sm" @update:modelValue="onTransferModalClose">
      <div class="space-y-4">
        <div class="p-3 rounded bg-red-900/30 border border-red-600">
          <p class="text-red-400 font-bold text-sm">⚠️ WARNING: This action is IRREVERSIBLE!</p>
          <p class="text-red-300 text-xs mt-2">The new owner will receive full control of the guild. You will be demoted to a regular member and lose all guild owner privileges.</p>
        </div>

        <div>
          <label class="block text-xs text-text-muted mb-1">Select new owner</label>
          <select
            v-model="transferTargetId"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-border-gold outline-none"
          >
            <option :value="null" disabled>Choose a member…</option>
            <option v-for="m in transferableMembers" :key="m.user_id" :value="m.user_id">
              {{ m.username ?? m.user?.username }}
            </option>
          </select>
        </div>

        <label class="flex items-start gap-2 cursor-pointer">
          <input v-model="transferConfirmed" type="checkbox" class="mt-0.5 accent-red-500" />
          <span class="text-xs"><strong class="text-red-400">I understand that this action cannot be undone and I will lose all guild owner privileges</strong></span>
        </label>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showTransferModal = false">Cancel</WowButton>
          <WowButton variant="danger" :disabled="!canSubmitTransfer" :loading="transferring" @click="doTransferOwnership">
            {{ transferButtonLabel }}
          </WowButton>
        </div>
      </template>
    </WowModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import CharacterDetailModal from '@/components/common/CharacterDetailModal.vue'
import { useGuildStore } from '@/stores/guild'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { usePermissions } from '@/composables/usePermissions'
import { useWowIcons } from '@/composables/useWowIcons'
import { useSystemSettings } from '@/composables/useSystemSettings'
import * as guildsApi from '@/api/guilds'
import api from '@/api'

const guildStore = useGuildStore()
const uiStore = useUiStore()
const authStore = useAuthStore()
const permissions = usePermissions()
const { getClassIcon, getClassColor, getSpecIcon } = useWowIcons()
const systemSettings = useSystemSettings()
systemSettings.fetchSettings()

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

// Character detail modal
const showCharDetailModal = ref(false)
const charDetailTarget = ref(null)

function openCharDetailModal(character) {
  charDetailTarget.value = character
  showCharDetailModal.value = true
}

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
    const data = await guildsApi.getWarmaneRoster(g.id)
    warmaneRoster.value = data.roster || []
  } catch (err) {
    warmaneRosterError.value = err?.response?.data?.error ?? err?.response?.data?.message ?? 'Failed to fetch guild roster from Warmane'
  } finally {
    fetchingRoster.value = false
  }
}

// Auto-fetch roster for Warmane-sourced guilds on mount
onMounted(() => {
  if (isWarmaneSource.value) {
    fetchWarmaneRoster()
  }
})

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

// Transfer ownership
const showTransferModal = ref(false)
const transferTargetId = ref(null)
const transferConfirmed = ref(false)
const transferring = ref(false)
const transferCountdown = ref(30)
let transferTimer = null

const canTransferOwnership = computed(() => {
  const guild = guildStore.currentGuild
  if (!guild) return false
  const isCreator = guild.created_by === authStore.user?.id
  const isGlobalAdmin = authStore.user?.is_admin
  if (!isCreator && !isGlobalAdmin) return false
  return members.value.filter(m => m.user_id !== guild.created_by).length > 0
})

const transferableMembers = computed(() => {
  const guild = guildStore.currentGuild
  if (!guild) return []
  return members.value.filter(m => m.user_id !== guild.created_by)
})

const canSubmitTransfer = computed(() => {
  return transferConfirmed.value && transferTargetId.value && transferCountdown.value <= 0
})

const transferButtonLabel = computed(() => {
  if (transferCountdown.value > 0 && transferConfirmed.value) {
    return `Transfer Ownership (${transferCountdown.value}s)`
  }
  return 'Transfer Ownership'
})

watch(transferConfirmed, (checked) => {
  if (checked) {
    transferCountdown.value = 30
    transferTimer = setInterval(() => {
      transferCountdown.value--
      if (transferCountdown.value <= 0) {
        clearInterval(transferTimer)
        transferTimer = null
      }
    }, 1000)
  } else {
    clearInterval(transferTimer)
    transferTimer = null
    transferCountdown.value = 30
  }
})

function onTransferModalClose(val) {
  if (!val) {
    clearInterval(transferTimer)
    transferTimer = null
    transferConfirmed.value = false
    transferTargetId.value = null
    transferCountdown.value = 30
  }
}

onUnmounted(() => {
  clearInterval(transferTimer)
})

async function doTransferOwnership() {
  if (!canSubmitTransfer.value) return
  transferring.value = true
  try {
    await guildsApi.transferOwnership(guildStore.currentGuild.id, transferTargetId.value)
    showTransferModal.value = false
    onTransferModalClose(false)
    await guildStore.fetchGuild(guildStore.currentGuild.id)
    await loadMembers()
    uiStore.showToast('Guild ownership transferred successfully', 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? 'Failed to transfer ownership', 'error')
  } finally {
    transferring.value = false
  }
}
</script>
