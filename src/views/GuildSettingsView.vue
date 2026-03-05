<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6">
      <h1 class="wow-heading text-xl sm:text-2xl">{{ t('admin.tabs.guildSettings') }}</h1>

      <div v-if="loading" class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="error" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">{{ error }}</div>

      <template v-else>
        <!-- Guild info form -->
        <WowCard>
          <h2 class="wow-heading text-base mb-4">{{ t('guild.settings.information') }}</h2>
          <form @submit.prevent="saveGuild" class="space-y-4 max-w-lg">
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.guildName') }}</label>
              <input v-model="form.name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.realm') }}</label>
              <select v-model="form.realm" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
                <option value="">{{ t('common.fields.selectRealm') }}</option>
                <option v-for="r in guildRealmNames" :key="r" :value="r">{{ r }}</option>
              </select>
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('guild.expansion') }}</label>
              <select v-model.number="form.expansion_id" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" @change="onExpansionChange">
                <option v-for="exp in sortedExpansions" :key="exp.id" :value="exp.id">{{ exp.name }}</option>
              </select>
              <p class="text-xs text-text-muted mt-1">{{ t('guild.expansionHelp') }}</p>
              <div v-if="form.expansion_id && includedExpansions.length" class="mt-2 flex flex-wrap gap-1">
                <span v-for="exp in includedExpansions" :key="exp.id"
                  class="px-2 py-0.5 rounded text-xs font-medium bg-green-900/30 text-green-300 border border-green-700/50">
                  ✓ {{ exp.name }}
                </span>
              </div>
              <div v-if="expansionSaving" class="mt-2 text-xs text-text-muted flex items-center gap-1">
                <div class="w-3 h-3 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin" />
                {{ t('common.labels.saving') }}
              </div>
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('common.labels.description') }}</label>
              <textarea v-model="form.description" rows="3" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none resize-none" />
            </div>
            <div v-if="saveError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ saveError }}</div>
            <WowButton type="submit" :loading="saving">{{ t('common.fields.saveChanges') }}</WowButton>
          </form>
        </WowCard>

        <!-- Armory Guild Lookup -->
        <WowCard>
          <h2 class="wow-heading text-base mb-4">{{ t('guild.settings.armoryInfo') }}</h2>
          <p class="text-text-muted text-sm mb-4">{{ t('members.fetchRoster') }}</p>
          <form @submit.prevent="fetchArmoryGuild" class="flex items-end gap-3 max-w-lg">
            <div class="flex-1">
              <label class="block text-xs text-text-muted mb-1">{{ t('guild.settings.guildName') }}</label>
              <input v-model="armoryGuildName" :placeholder="form.name || 'Guild name'" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
            </div>
            <div class="w-40">
              <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.realm') }}</label>
              <select v-model="armoryGuildRealm" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
                <option v-for="r in guildRealmNames" :key="r" :value="r">{{ r }}</option>
              </select>
            </div>
            <WowButton type="submit" :loading="fetchingArmory" variant="secondary">{{ t('guildSettings.fetch') }}</WowButton>
          </form>

          <div v-if="armoryError" class="mt-4 p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ armoryError }}</div>

          <div v-if="armoryGuildData" class="mt-4 space-y-3">
            <div class="flex items-center gap-4 text-sm">
              <span class="text-text-muted">Guild:</span>
              <span class="text-text-primary font-medium">{{ armoryGuildData.name }}</span>
              <span v-if="armoryGuildData.faction" class="px-2 py-0.5 rounded text-xs font-medium"
                :class="armoryGuildData.faction === 'Alliance' ? 'bg-blue-900/50 text-blue-300 border border-blue-600' : 'bg-red-900/50 text-red-300 border border-red-600'"
              >{{ armoryGuildData.faction }}</span>
              <span class="text-text-muted">{{ armoryGuildData.member_count }} members</span>
            </div>

            <div v-if="armoryGuildData.roster?.length" class="overflow-x-auto max-h-64 overflow-y-auto">
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
                  <tr v-for="ch in armoryGuildData.roster" :key="ch.name" class="hover:bg-bg-tertiary/50">
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
            <h2 class="wow-heading text-base">{{ t('common.labels.members') }} ({{ members.length }})</h2>
            <WowButton variant="secondary" class="text-xs py-1 px-3" @click="showAddMember = true">
              + {{ t('members.addMember') }}
            </WowButton>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-bg-tertiary border-b border-border-default">
                  <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.username') }}</th>
                  <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.role') }}</th>
                  <th class="text-right px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.labels.actions') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-default">
                <tr v-for="m in members" :key="m.id" class="hover:bg-bg-tertiary/50 transition-colors">
                  <td class="px-4 py-2.5 text-text-primary font-medium">{{ m.username ?? m.user?.username }}</td>
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
                  <td class="px-4 py-2.5 text-right space-x-2">
                    <WowButton variant="ghost" class="text-xs py-1 px-2" @click="viewMemberChars(m)">
                      {{ t('common.labels.characters') }}
                    </WowButton>
                    <WowButton v-if="canChangeRole(m)" variant="danger" class="text-xs py-1 px-2" @click="confirmKick(m)">
                      {{ t('common.buttons.remove') }}
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
    <WowModal v-model="showKickConfirm" :title="t('members.removeMember')" size="sm">
      <p class="text-text-muted">Remove <strong class="text-text-primary">{{ kickTarget?.username ?? kickTarget?.user?.username }}</strong> from the guild?</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showKickConfirm = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="danger" :loading="saving" @click="doKick">{{ t('common.buttons.remove') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Add Member modal -->
    <WowModal v-model="showAddMember" :title="t('members.addMemberTitle')" size="sm">
      <div class="space-y-3">
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('members.searchByUsername') }}</label>
          <input
            v-model="addMemberQuery"
            :placeholder="t('members.typePlaceholder')"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
            @input="searchUsers"
          />
        </div>
        <div v-if="searchingUsers" class="text-xs text-text-muted">{{ t('common.labels.searching') }}</div>
        <div v-if="availableUsers.length > 0" class="max-h-40 overflow-y-auto space-y-1">
          <button
            v-for="u in availableUsers"
            :key="u.id"
            type="button"
            class="w-full flex items-center justify-between px-3 py-2 rounded bg-bg-tertiary/60 hover:bg-bg-tertiary transition-colors text-sm"
            @click="doAddMember(u)"
          >
            <span class="text-text-primary">{{ u.username }}</span>
            <span class="text-xs text-accent-gold">{{ t('common.buttons.add') }}</span>
          </button>
        </div>
        <div v-else-if="addMemberQuery.length >= 2 && !searchingUsers" class="text-xs text-text-muted">
          {{ t('members.noMatchingUsers') }}
        </div>
      </div>
    </WowModal>

    <!-- Member Characters modal -->
    <WowModal v-model="showMemberChars" :title="memberCharsTitle" size="md">
      <div v-if="loadingMemberChars" class="py-6 text-center text-text-muted">{{ t('common.labels.loadingCharacters') }}</div>
      <div v-else-if="memberChars.length === 0" class="py-6 text-center text-text-muted">{{ t('members.noCharacters') }}</div>
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
  </AppShell>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import { useGuildStore } from '@/stores/guild'
import { useUiStore } from '@/stores/ui'
import { usePermissions } from '@/composables/usePermissions'
import { useAuthStore } from '@/stores/auth'
import * as guildsApi from '@/api/guilds'
import * as armoryLookupApi from '@/api/armory_lookup'
import * as guildRealmsApi from '@/api/guild_realms'
import * as guildExpansionsApi from '@/api/guild_expansions'
import api from '@/api'
import { useI18n } from 'vue-i18n'
import { useExpansionStore } from '@/stores/expansion'
import { useConstantsStore } from '@/stores/constants'

const guildStore = useGuildStore()
const uiStore = useUiStore()
const permissions = usePermissions()
const authStore = useAuthStore()
const expansionStore = useExpansionStore()
const constantsStore = useConstantsStore()
const { t } = useI18n()
const expansionSaving = ref(false)

const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const saveError = ref(null)
const members = ref([])
const showKickConfirm = ref(false)
const kickTarget = ref(null)
const allRoles = ref([])

const form = reactive({ name: '', realm: '', description: '', expansion_id: null })
const guildRealmNames = ref([])

async function fetchRoles() {
  try {
    allRoles.value = await api.get('/roles')
  } catch {
    allRoles.value = []
  }
}

const allExpansions = computed(() =>
  constantsStore.expansions.length ? constantsStore.expansions : expansionStore.expansions
)

const sortedExpansions = computed(() => {
  return [...allExpansions.value].sort((a, b) => (b.sort_order ?? 0) - (a.sort_order ?? 0))
})

const includedExpansions = computed(() => {
  const selected = sortedExpansions.value.find(e => e.id === form.expansion_id)
  if (!selected) return []
  return [...allExpansions.value]
    .filter(e => (e.sort_order ?? 0) <= (selected.sort_order ?? 0))
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
})

/** Roles the current user is allowed to grant, based on the roles API can_grant list */
const grantableRoles = computed(() => {
  const myRole = permissions.role.value
  if (!myRole && !permissions.can('manage_roles')) return []
  // Users with manage_roles permission can grant any role
  if (permissions.can('manage_roles') && !myRole) return allRoles.value
  const myRoleDef = allRoles.value.find(r => r.name === myRole)
  if (!myRoleDef) return allRoles.value
  const grantable = new Set(myRoleDef.can_grant || [])
  return allRoles.value.filter(r => grantable.has(r.name))
})

/** Role options to show in the dropdown for a member */
function roleOptionsForMember(member) {
  // Always include the member's current role so the dropdown shows the current value
  const options = [...grantableRoles.value]
  if (member.role && !options.find(r => r.name === member.role)) {
    const currentRoleDef = allRoles.value.find(r => r.name === member.role)
    if (currentRoleDef) options.push(currentRoleDef)
  }
  return options.sort((a, b) => a.level - b.level)
}

async function loadGuildData() {
  loading.value = true
  error.value = null
  try {
    const g = guildStore.currentGuild
    if (g) {
      Object.assign(form, { name: g.name ?? '', realm: g.realm_name ?? '', description: g.description ?? '' })
      await Promise.all([
        guildStore.fetchMembers(g.id),
        fetchRoles(),
        loadGuildRealmNames(g.id),
      ])
      members.value = guildStore.members

      // Load current guild expansion
      try {
        if (expansionStore.expansions.length === 0 && constantsStore.expansions.length === 0) {
          await expansionStore.fetchExpansions(true)
        }
        const expData = await guildExpansionsApi.getGuildExpansions(g.id)
        const enabledExps = (expData.expansions || [])
        if (enabledExps.length > 0) {
          const allExps = allExpansions.value          let highestEnabled = null
          for (const ge of enabledExps) {
            const full = allExps.find(e => e.id === ge.expansion_id)
            if (full && (!highestEnabled || (full.sort_order ?? 0) > (highestEnabled.sort_order ?? 0))) {
              highestEnabled = full
            }
          }
          if (highestEnabled) form.expansion_id = highestEnabled.id
        } else if (sortedExpansions.value.length) {
          form.expansion_id = sortedExpansions.value[0].id
        }
      } catch { /* ignore */ }
    }
  } catch {
    error.value = t('guildSettings.failedToLoad')
  } finally {
    loading.value = false
  }
}

async function loadGuildRealmNames(guildId) {
  try {
    const data = await guildRealmsApi.getGuildRealms(guildId)
    guildRealmNames.value = (data.realms || []).map(r => r.name)
  } catch {
    guildRealmNames.value = []
  }
}

async function onExpansionChange() {
  const guildId = guildStore.currentGuildId
  if (!guildId || !form.expansion_id) return

  expansionSaving.value = true
  try {
    const expData = await guildExpansionsApi.getGuildExpansions(guildId)
    const currentEnabled = new Set((expData.expansions || []).map(e => e.expansion_id))

    const selected = sortedExpansions.value.find(e => e.id === form.expansion_id)
    if (!selected) return

    const shouldBeEnabled = new Set(
      allExpansions.value
        .filter(e => (e.sort_order ?? 0) <= (selected.sort_order ?? 0))
        .map(e => e.id)
    )

    const enablePromises = []
    for (const id of shouldBeEnabled) {
      if (!currentEnabled.has(id)) {
        enablePromises.push(guildExpansionsApi.enableExpansion(guildId, id))
      }
    }

    const disablePromises = []
    for (const id of currentEnabled) {
      if (!shouldBeEnabled.has(id)) {
        disablePromises.push(guildExpansionsApi.disableExpansion(guildId, id))
      }
    }

    await Promise.all([...enablePromises, ...disablePromises])

    uiStore.showToast(t('guild.expansions.expansionUpdated'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || t('guild.expansions.failedToUpdate'), 'error')
  } finally {
    expansionSaving.value = false
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
    uiStore.showToast(t('guildSettings.toasts.settingsSaved'), 'success')
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
    uiStore.showToast(t('common.toasts.roleUpdated'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('common.toasts.failedToUpdateRole'), 'error')
  }
}

/** Can the current user change this member's role? */
function canChangeRole(member) {
  if (member.user_id === authStore.user?.id) return false
  if (!permissions.can('manage_roles')) return false
  // Can't modify someone with equal or higher role level
  const myRole = permissions.role.value
  const myRoleDef = allRoles.value.find(r => r.name === myRole)
  const memberRoleDef = allRoles.value.find(r => r.name === member.role)
  // Users with manage_roles can bypass level check
  if (permissions.can('manage_roles') && !myRoleDef) return true
  if (!myRoleDef || !memberRoleDef) return false
  return myRoleDef.level > memberRoleDef.level
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
    uiStore.showToast(t('common.toasts.memberRemoved'), 'success')
  } catch {
    uiStore.showToast(t('common.toasts.failedToRemoveMember'), 'error')
  } finally {
    saving.value = false
  }
}

// Armory guild lookup
const armoryGuildName = ref('')
const armoryGuildRealm = ref('Icecrown')
const fetchingArmory = ref(false)
const armoryError = ref(null)
const armoryGuildData = ref(null)

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
    uiStore.showToast(err?.response?.data?.error ?? t('common.toasts.failedToLoadCharacters'), 'error')
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
      uiStore.showToast(err?.response?.data?.message ?? t('common.toasts.failedToSearch'), 'error')
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
    uiStore.showToast(t('guildSettings.toasts.memberAdded', { username: user.username }), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.message ?? t('common.toasts.failedToAdd'), 'error')
  }
}

async function fetchArmoryGuild() {
  armoryError.value = null
  armoryGuildData.value = null
  const name = armoryGuildName.value || form.name
  const realm = armoryGuildRealm.value || form.realm
  if (!name || !realm) {
    armoryError.value = 'Guild name and realm are required'
    return
  }
  fetchingArmory.value = true
  try {
    armoryGuildData.value = await armoryLookupApi.lookupGuild(realm, name, guildStore.currentGuild?.id)
  } catch (err) {
    armoryError.value = err?.response?.data?.message ?? 'Guild not found on armory'
  } finally {
    fetchingArmory.value = false
  }
}
</script>
