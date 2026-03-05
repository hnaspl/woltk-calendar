<template>
  <div class="space-y-6">
    <!-- Add member manually -->
    <WowCard v-if="canAddMembers">
      <div class="flex items-center gap-2 mb-4">
        <svg class="w-5 h-5 text-accent-gold flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
        </svg>
        <div>
          <h2 class="text-sm font-semibold text-text-primary">{{ t('guild.addMember') }}</h2>
          <p class="text-xs text-text-muted mt-0.5">{{ t('guild.addMemberHelp') }}</p>
        </div>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div class="sm:col-span-2 relative">
          <label class="block text-xs text-text-muted mb-1">{{ t('guild.searchUsers') }}</label>
          <input
            v-model="userSearch"
            type="text"
            :placeholder="t('guild.searchUsers')"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
            @input="onSearchInput"
          />
          <!-- Search results dropdown -->
          <div v-if="userResults.length > 0" class="absolute z-10 mt-1 w-full bg-bg-tertiary border border-border-default rounded shadow-lg max-h-48 overflow-y-auto">
            <button
              v-for="user in userResults"
              :key="user.id"
              type="button"
              class="w-full text-left px-3 py-2 text-sm hover:bg-bg-secondary transition-colors"
              :class="selectedUser?.id === user.id ? 'bg-bg-secondary text-accent-gold' : 'text-text-primary'"
              @click="selectUser(user)"
            >
              <span class="font-medium">{{ user.display_name || user.username }}</span>
              <span v-if="user.display_name" class="text-text-muted ml-1">({{ user.username }})</span>
            </button>
          </div>
          <p v-if="userSearch.length >= 2 && userResults.length === 0 && !searchingUsers" class="text-xs text-text-muted mt-1">
            {{ t('guild.noUsersFound') }}
          </p>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('guild.inviteRole') }}</label>
          <select v-model="addMemberRole" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option value="member">{{ t('guild.roleMember') }}</option>
            <option value="officer">{{ t('guild.roleOfficer') }}</option>
          </select>
        </div>
      </div>
      <!-- Selected user chip -->
      <div v-if="selectedUser" class="mt-3 flex items-center gap-2">
        <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-bg-secondary border border-border-default">
          <div class="w-6 h-6 rounded-full bg-bg-tertiary border border-border-default flex items-center justify-center text-xs text-accent-gold font-bold uppercase">
            {{ (selectedUser.display_name || selectedUser.username || '?')[0] }}
          </div>
          <span class="text-sm text-text-primary">{{ selectedUser.display_name || selectedUser.username }}</span>
          <button type="button" class="text-text-muted hover:text-text-primary ml-1" @click="selectedUser = null">✕</button>
        </div>
      </div>
      <div class="mt-4">
        <WowButton @click="doAddMember" :loading="addingMember" :disabled="!selectedUser">
          {{ t('guild.addMember') }}
        </WowButton>
      </div>
    </WowCard>

    <!-- Create invitation -->
    <WowCard>
      <div class="flex items-center gap-2 mb-4">
        <svg class="w-5 h-5 text-accent-gold flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        </svg>
        <div>
          <h2 class="text-sm font-semibold text-text-primary">{{ t('guild.createInvite') }}</h2>
          <p class="text-xs text-text-muted mt-0.5">{{ t('guild.createInviteHelp') }}</p>
        </div>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('guild.inviteRole') }}</label>
          <select v-model="form.role" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option value="member">{{ t('guild.roleMember') }}</option>
            <option value="officer">{{ t('guild.roleOfficer') }}</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('guild.maxUses') }}</label>
          <input v-model.number="form.max_uses" type="number" min="1" placeholder="∞"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('guild.expiresInDays') }}</label>
          <input v-model.number="form.expires_in_days" type="number" min="1" max="30"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
      </div>
      <div class="mt-4">
        <WowButton @click="doCreate" :loading="creating">
          {{ t('guild.generateLink') }}
        </WowButton>
      </div>
      <!-- Show generated link -->
      <div v-if="generatedToken" class="mt-4 p-3 rounded-lg bg-green-900/20 border border-green-700/30">
        <p class="text-sm text-green-300 font-medium mb-1">{{ t('guild.linkGenerated') }}</p>
        <p class="text-xs text-text-muted mb-2">{{ t('guild.linkGeneratedHelp') }}</p>
        <div class="flex items-center gap-2">
          <input readonly :value="generatedLink" class="flex-1 bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-xs font-mono" />
          <WowButton @click="doCopyLink" class="text-xs py-2 px-3">
            {{ t('guild.copyLink') }}
          </WowButton>
        </div>
      </div>
    </WowCard>

    <!-- Existing invitations -->
    <WowCard>
      <div class="flex items-center gap-2 mb-4">
        <svg class="w-5 h-5 text-accent-gold flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        <h2 class="text-sm font-semibold text-text-primary">{{ t('guild.existingInvites') }}</h2>
        <span v-if="invitations.length" class="ml-auto text-xs text-text-muted bg-bg-tertiary border border-border-default rounded-full px-2 py-0.5">{{ invitations.length }}</span>
      </div>
      <div v-if="loading" class="py-4 text-center">
        <div class="w-5 h-5 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin mx-auto" />
      </div>
      <div v-else-if="invitations.length === 0" class="py-6 text-center">
        <p class="text-sm text-text-muted">{{ t('guild.noInvites') }}</p>
        <p class="text-xs text-text-muted mt-1">{{ t('guild.noInvitesHelp') }}</p>
      </div>
      <div v-else class="space-y-2">
        <InviteLinkCard
          v-for="inv in invitations"
          :key="inv.id"
          :invitation="inv"
          :link-base="`${origin}/guild-invite/`"
          @revoke="doRevoke(inv)"
          @copy="doCopyInvite(inv)"
        />
      </div>
    </WowCard>

    <!-- Applications -->
    <WowCard v-if="canApprove">
      <div class="flex items-center gap-2 mb-4">
        <svg class="w-5 h-5 text-accent-gold flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
        </svg>
        <h2 class="text-sm font-semibold text-text-primary">{{ t('guild.applicationsTitle') }}</h2>
        <span v-if="applications.length" class="ml-auto text-xs text-text-muted bg-accent-gold/20 text-accent-gold border border-accent-gold/30 rounded-full px-2 py-0.5">{{ applications.length }}</span>
      </div>
      <div v-if="applications.length === 0" class="py-4 text-center">
        <p class="text-sm text-text-muted">{{ t('guild.noApplications') }}</p>
      </div>
      <div v-else class="space-y-2">
        <div v-for="app in applications" :key="app.id"
          class="flex items-center justify-between gap-3 p-3 rounded-lg bg-bg-tertiary border border-border-default">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-full bg-bg-secondary border border-border-default flex items-center justify-center text-xs text-accent-gold font-bold uppercase">
              {{ (app.display_name || app.username || '?')[0] }}
            </div>
            <span class="text-sm text-text-primary font-medium">{{ app.display_name || app.username }}</span>
          </div>
          <div class="flex items-center gap-2">
            <WowButton @click="doApprove(app)" class="text-xs py-1 px-3">
              {{ t('guild.approve') }}
            </WowButton>
            <WowButton variant="danger" @click="doDecline(app)" class="text-xs py-1 px-3">
              {{ t('guild.decline') }}
            </WowButton>
          </div>
        </div>
      </div>
    </WowCard>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import InviteLinkCard from '@/components/common/InviteLinkCard.vue'
import { useGuildStore } from '@/stores/guild'
import { useUiStore } from '@/stores/ui'
import * as guildsApi from '@/api/guilds'

const { t } = useI18n()
const uiStore = useUiStore()
const guildStore = useGuildStore()

const props = defineProps({
  permissions: { type: Array, default: () => [] },
})

const origin = window.location.origin
const loading = ref(false)
const creating = ref(false)
const invitations = ref([])
const applications = ref([])
const generatedToken = ref(null)

const form = ref({
  role: 'member',
  max_uses: null,
  expires_in_days: 7,
})

const canAddMembers = computed(() => props.permissions.includes('add_members'))
const canApprove = computed(() => props.permissions.includes('approve_applications'))

// --- Add member manually ---
const userSearch = ref('')
const userResults = ref([])
const selectedUser = ref(null)
const addMemberRole = ref('member')
const addingMember = ref(false)
const searchingUsers = ref(false)
const searchTimeout = ref(null)

onBeforeUnmount(() => {
  clearTimeout(searchTimeout.value)
})

function onSearchInput() {
  selectedUser.value = null
  clearTimeout(searchTimeout.value)
  if (userSearch.value.length < 2) {
    userResults.value = []
    return
  }
  searchTimeout.value = setTimeout(() => searchUsers(userSearch.value), 300)
}

async function searchUsers(query) {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  searchingUsers.value = true
  try {
    const result = await guildsApi.getAvailableUsers(guildId, query)
    userResults.value = Array.isArray(result) ? result : []
  } catch {
    userResults.value = []
  } finally {
    searchingUsers.value = false
  }
}

function selectUser(user) {
  selectedUser.value = user
  userResults.value = []
  userSearch.value = user.display_name || user.username
}

async function doAddMember() {
  const guildId = guildStore.currentGuildId
  if (!guildId || !selectedUser.value) return
  addingMember.value = true
  try {
    await guildsApi.addMember(guildId, selectedUser.value.id, addMemberRole.value)
    uiStore.showToast(t('guild.memberAdded'), 'success')
    selectedUser.value = null
    userSearch.value = ''
    userResults.value = []
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || err?.response?.data?.message || t('guild.addMember'), 'error')
  } finally {
    addingMember.value = false
  }
}

const generatedLink = computed(() => {
  if (!generatedToken.value) return ''
  return `${origin}/guild-invite/${generatedToken.value}`
})

onMounted(() => {
  // Initial load handled by the watch below with immediate: true
})

// Reload when guild becomes available or changes
watch(() => guildStore.currentGuildId, (newId) => {
  if (newId) {
    loadInvitations()
    if (canApprove.value) loadApplications()
  }
}, { immediate: true })

async function loadInvitations() {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  loading.value = true
  try {
    const result = await guildsApi.getGuildInvitations(guildId)
    invitations.value = Array.isArray(result) ? result : (result?.invitations ?? [])
  } catch (err) {
    console.warn('Failed to load invitations:', err?.response?.status, err?.response?.data)
    invitations.value = []
  } finally {
    loading.value = false
  }
}

async function loadApplications() {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  try {
    const result = await guildsApi.getGuildApplications(guildId)
    applications.value = Array.isArray(result) ? result : (result?.applications ?? [])
  } catch (err) {
    console.warn('Failed to load applications:', err?.response?.status, err?.response?.data)
    applications.value = []
  }
}

async function doCreate() {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  creating.value = true
  try {
    const payload = { ...form.value }
    if (!payload.max_uses) delete payload.max_uses
    const result = await guildsApi.createGuildInvitation(guildId, payload)
    generatedToken.value = result.invite_token
    await loadInvitations()
    uiStore.showToast(t('guild.linkGenerated'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || 'Error', 'error')
  }
  creating.value = false
}

async function doRevoke(inv) {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  try {
    await guildsApi.revokeGuildInvitation(guildId, inv.id)
    await loadInvitations()
    uiStore.showToast(t('guild.inviteRevoked'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || 'Error', 'error')
  }
}

function doCopyInvite(inv) {
  const link = `${origin}/guild-invite/${inv.invite_token}`
  doCopyText(link)
}

function doCopyLink() {
  doCopyText(generatedLink.value)
}

function doCopyText(text) {
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(() => uiStore.showToast(t('guild.copyLink'), 'success'))
  } else {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    uiStore.showToast(t('guild.copyLink'), 'success')
  }
}

async function doApprove(app) {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  try {
    await guildsApi.approveApplication(guildId, app.user_id)
    await loadApplications()
    uiStore.showToast(t('guild.applicationApproved'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || 'Error', 'error')
  }
}

async function doDecline(app) {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  try {
    await guildsApi.declineApplication(guildId, app.user_id)
    await loadApplications()
    uiStore.showToast(t('guild.applicationDeclined'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || 'Error', 'error')
  }
}
</script>
