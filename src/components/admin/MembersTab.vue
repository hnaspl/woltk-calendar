<template>
  <div class="space-y-6">
    <!-- Members table -->
    <WowCard>
      <div class="flex items-center justify-between mb-4">
        <h2 class="wow-heading text-base">{{ t('members.title', { count: members.length }) }}</h2>
        <div class="flex gap-2">
          <WowButton v-if="permissions.can('manage_guild_members')" variant="secondary" class="text-xs py-1 px-3" @click="showAddMember = true">
            {{ t('members.addMember') }}
          </WowButton>
          <WowButton v-if="permissions.can('remove_members')" variant="secondary" class="text-xs py-1 px-3" @click="showNotifyAllModal = true">
            📢 {{ t('members.notifyAll') }}
          </WowButton>
        </div>
      </div>

      <div v-if="loading" class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>

      <div v-else>
        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-bg-tertiary border-b border-border-default">
                <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.username') }}</th>
                <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.role') }}</th>
                <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('members.joined') }}</th>
                <th class="text-right px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.labels.actions') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border-default">
              <tr v-for="m in members" :key="m.id" class="hover:bg-bg-tertiary/50 transition-colors">
                <td class="px-4 py-2.5">
                  <div class="text-text-primary font-medium">{{ m.username ?? m.user?.username }}</div>
                  <div v-if="m.user_id === authStore.user?.id" class="text-[10px] text-accent-gold">{{ t('common.labels.you') }}</div>
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
                <td class="px-4 py-2.5">
                  <div class="flex flex-col gap-1 items-end">
                    <button
                      class="inline-flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded bg-accent-gold/15 text-accent-gold border border-accent-gold/40 hover:bg-accent-gold/25 hover:border-accent-gold/70 transition-colors w-full justify-center"
                      @click="viewMemberChars(m)"
                    >
                      📋 {{ t('common.labels.characters') }}
                    </button>
                    <WowButton v-if="canChangeRole(m)" variant="secondary" class="text-xs py-1 px-2 w-full" @click="openNotifyModal(m)">📢 {{ t('members.notify') }}</WowButton>
                    <WowButton v-if="canChangeRole(m) && m.status !== 'banned'" variant="danger" class="text-xs py-1 px-2 w-full" @click="confirmBan(m)">🚫 {{ t('members.ban') }}</WowButton>
                    <WowButton v-if="canChangeRole(m) && m.status === 'banned'" variant="secondary" class="text-xs py-1 px-2 w-full" @click="doUnban(m)">✅ {{ t('members.unban') }}</WowButton>
                    <WowButton v-if="canChangeRole(m)" variant="danger" class="text-xs py-1 px-2 w-full" @click="confirmKick(m)">{{ t('common.buttons.remove') }}</WowButton>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Mobile card layout -->
        <div class="sm:hidden space-y-3">
          <div
            v-for="m in members"
            :key="'mobile-' + m.id"
            class="p-3 rounded-lg bg-bg-tertiary border border-border-default space-y-2"
          >
            <div class="flex items-center justify-between">
              <div>
                <div class="text-text-primary font-medium text-sm">{{ m.username ?? m.user?.username }}</div>
                <div v-if="m.user_id === authStore.user?.id" class="text-[10px] text-accent-gold">{{ t('common.labels.you') }}</div>
              </div>
              <select
                :value="m.role"
                :disabled="!canChangeRole(m)"
                class="bg-bg-tertiary border border-border-default text-text-primary text-xs rounded px-2 py-1 focus:border-border-gold outline-none disabled:opacity-50"
                @change="updateRole(m, $event.target.value)"
              >
                <option v-for="r in roleOptionsForMember(m)" :key="r.name" :value="r.name">{{ r.display_name }}</option>
              </select>
            </div>
            <div class="text-xs text-text-muted">{{ t('members.joined') }}: {{ formatDate(m.joined_at ?? m.created_at) }}</div>
            <div class="flex flex-col gap-1">
              <button
                class="flex-1 inline-flex items-center justify-center gap-1 text-xs font-medium px-3 py-1.5 rounded bg-accent-gold/15 text-accent-gold border border-accent-gold/40 hover:bg-accent-gold/25 transition-colors"
                @click="viewMemberChars(m)"
              >📋 {{ t('common.labels.characters') }}</button>
              <WowButton v-if="canChangeRole(m)" variant="secondary" class="text-xs py-1 px-2" @click="openNotifyModal(m)">📢 {{ t('members.notify') }}</WowButton>
              <div class="flex gap-2">
                <WowButton v-if="canChangeRole(m) && m.status !== 'banned'" variant="danger" class="text-xs py-1 px-2 flex-1" @click="confirmBan(m)">🚫 {{ t('members.ban') }}</WowButton>
                <WowButton v-if="canChangeRole(m) && m.status === 'banned'" variant="secondary" class="text-xs py-1 px-2 flex-1" @click="doUnban(m)">✅ {{ t('members.unban') }}</WowButton>
                <WowButton v-if="canChangeRole(m)" variant="danger" class="text-xs py-1 px-2 flex-1" @click="confirmKick(m)">{{ t('common.buttons.remove') }}</WowButton>
              </div>
            </div>
          </div>
        </div>
      </div>
    </WowCard>

    <!-- Kick confirmation -->
    <WowModal v-model="showKickConfirm" :title="t('members.removeMember')" size="sm">
      <p class="text-text-muted">{{ t('members.removeConfirm', { name: kickTarget?.username ?? kickTarget?.user?.username }) }}</p>
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
        <!-- Invitation suggestion -->
        <div class="p-3 rounded-lg bg-accent-gold/10 border border-accent-gold/30">
          <p class="text-sm text-accent-gold mb-2">{{ t('members.inviteSuggestion') }}</p>
          <RouterLink
            to="/tenant/invites"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-accent-gold/20 text-accent-gold border border-accent-gold/50 rounded hover:bg-accent-gold/30 transition-colors"
          >
            {{ t('tenant.invitePlayers') }}
          </RouterLink>
        </div>

        <div class="flex items-center gap-3">
          <div class="flex-1 border-t border-border-default"></div>
          <span class="text-text-muted text-xs uppercase">{{ t('auth.orSeparator') }}</span>
          <div class="flex-1 border-t border-border-default"></div>
        </div>

        <!-- Standard search for existing registered users -->
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
    <WowModal v-model="showMemberChars" :title="memberCharsTitle" size="2xl">
      <div v-if="loadingMemberChars" class="py-6 text-center text-text-muted">{{ t('common.labels.loadingCharacters') }}</div>
      <div v-else-if="memberChars.length === 0" class="py-6 text-center text-text-muted">{{ t('members.noCharacters') }}</div>
      <div v-else class="overflow-x-auto max-h-[70vh] overflow-y-auto">
        <table class="w-full text-sm">
          <thead class="sticky top-0 z-10">
            <tr class="bg-bg-tertiary border-b border-border-default">
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.character') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.role') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('members.primarySpec') }}</th>
              <th class="hidden md:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.labels.secondarySpec') }}</th>
              <th class="hidden sm:table-cell text-center px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.labels.type') }}</th>
              <th class="hidden sm:table-cell text-center px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.status') }}</th>
              <th class="text-right px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.labels.details') }}</th>
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
              <td class="hidden md:table-cell px-4 py-2.5">
                <div v-if="c.secondary_spec" class="flex items-center gap-1.5">
                  <img v-if="getSpecIcon(c.secondary_spec, c.class_name)" :src="getSpecIcon(c.secondary_spec, c.class_name)" class="w-4 h-4 rounded" />
                  <span class="text-text-muted text-xs">{{ c.secondary_spec }}</span>
                </div>
                <span v-else class="text-text-muted text-xs">—</span>
              </td>
              <td class="hidden sm:table-cell px-4 py-2.5 text-center">
                <span v-if="c.is_main" class="text-accent-gold text-[10px] font-bold uppercase px-1.5 py-0.5 bg-accent-gold/10 rounded">{{ t('members.mainChar') }}</span>
                <span v-else class="text-text-muted text-[10px] px-1.5 py-0.5 bg-bg-secondary rounded">{{ t('members.altChar') }}</span>
              </td>
              <td class="hidden sm:table-cell px-4 py-2.5 text-center">
                <span v-if="c.is_active !== false && !c.archived_at" class="text-green-400 text-[10px] font-medium px-1.5 py-0.5 bg-green-400/10 rounded">{{ t('common.status.active') }}</span>
                <span v-else class="text-red-400 text-[10px] font-medium px-1.5 py-0.5 bg-red-400/10 rounded">{{ t('common.status.archived') }}</span>
              </td>
              <td class="px-4 py-2.5 text-right">
                <WowButton variant="secondary" class="text-xs py-1 px-2" @click="openCharDetailModal(c)">
                  🔍 {{ t('members.view') }}
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
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 class="wow-heading text-base">{{ t('members.ownership.title') }}</h2>
          <p class="text-xs text-text-muted mt-1">{{ t('members.ownership.description') }}</p>
        </div>
        <WowButton variant="danger" class="text-xs py-1.5 px-3 flex-shrink-0" @click="showTransferModal = true">
          👑 {{ t('members.ownership.transferBtn') }}
        </WowButton>
      </div>
    </WowCard>

    <!-- Transfer Ownership modal -->
    <WowModal v-model="showTransferModal" :title="'👑 ' + t('members.ownership.modalTitle')" size="sm" @update:modelValue="onTransferModalClose">
      <div class="space-y-4">
        <div class="p-3 rounded bg-red-900/30 border border-red-600">
          <p class="text-red-400 font-bold text-sm">⚠️ {{ t('members.ownership.warning') }}</p>
          <p class="text-red-300 text-xs mt-2">{{ t('members.ownership.warningDesc') }}</p>
        </div>

        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('members.ownership.selectOwner') }}</label>
          <select
            v-model="transferTargetId"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-border-gold outline-none"
          >
            <option :value="null" disabled>{{ t('members.ownership.chooseMember') }}</option>
            <option v-for="m in transferableMembers" :key="m.user_id" :value="m.user_id">
              {{ m.username ?? m.user?.username }}
            </option>
          </select>
        </div>

        <label class="flex items-start gap-2 cursor-pointer">
          <input v-model="transferConfirmed" type="checkbox" class="mt-0.5 accent-red-500" />
          <span class="text-xs"><strong class="text-red-400">{{ t('members.ownership.confirmText') }}</strong></span>
        </label>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showTransferModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="danger" :disabled="!canSubmitTransfer" :loading="transferring" @click="doTransferOwnership">
            {{ transferButtonLabel }}
          </WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Notify Single Member Modal -->
    <WowModal v-model="showNotifyModal" :title="t('members.sendNotification')" size="sm">
      <div class="space-y-3">
        <p class="text-text-muted text-sm">{{ t('members.notifyTo', { name: notifyTarget?.username ?? notifyTarget?.user?.username }) }}</p>
        <textarea v-model="notifyMessage" rows="3" class="w-full bg-bg-secondary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-accent-gold focus:outline-none" :placeholder="t('members.notifyPlaceholder')" />
      </div>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <WowButton variant="secondary" @click="showNotifyModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="primary" :disabled="!notifyMessage.trim()" :loading="notifying" @click="doNotify">{{ t('members.send') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Notify All Modal -->
    <WowModal v-model="showNotifyAllModal" :title="t('members.notifyAllTitle')" size="sm">
      <div class="space-y-3">
        <p class="text-text-muted text-sm">{{ t('members.notifyAllDesc', { count: members.length }) }}</p>
        <textarea v-model="notifyAllMessage" rows="3" class="w-full bg-bg-secondary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-accent-gold focus:outline-none" :placeholder="t('members.notifyPlaceholder')" />
      </div>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <WowButton variant="secondary" @click="showNotifyAllModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="primary" :disabled="!notifyAllMessage.trim()" :loading="notifyingAll" @click="doNotifyAll">{{ t('members.send') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Ban Confirmation Modal -->
    <WowModal v-model="showBanConfirm" :title="t('members.banMember')" size="sm">
      <p class="text-text-muted">{{ t('members.banConfirm', { name: banTarget?.username ?? banTarget?.user?.username }) }}</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showBanConfirm = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="danger" :loading="banning" @click="doBan">{{ t('members.ban') }}</WowButton>
        </div>
      </template>
    </WowModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
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
import { useFormatting } from '@/composables/useFormatting'
import * as guildsApi from '@/api/guilds'
import api from '@/api'

const { t } = useI18n()
const guildStore = useGuildStore()
const uiStore = useUiStore()
const authStore = useAuthStore()
const permissions = usePermissions()
const { getClassIcon, getClassColor, getSpecIcon } = useWowIcons()
const systemSettings = useSystemSettings()
const { formatDate } = useFormatting()
systemSettings.fetchSettings()

const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const members = ref([])
const allRoles = ref([])
const showKickConfirm = ref(false)
const kickTarget = ref(null)

// Notify single member
const showNotifyModal = ref(false)
const notifyTarget = ref(null)
const notifyMessage = ref('')
const notifying = ref(false)

// Notify all members
const showNotifyAllModal = ref(false)
const notifyAllMessage = ref('')
const notifyingAll = ref(false)

// Ban/unban
const showBanConfirm = ref(false)
const banTarget = ref(null)
const banning = ref(false)


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
  const isGlobalAdmin = !!authStore.user?.is_admin
  const guild = guildStore.currentGuild
  const isCreator = guild && guild.created_by === authStore.user?.id
  // Global admin or guild creator can always change roles (matches backend bypass)
  if (isGlobalAdmin || isCreator) return true
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
    error.value = t('members.failedToLoad')
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
    uiStore.showToast(t('common.toasts.roleUpdated'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('common.toasts.failedToUpdateRole'), 'error')
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
    uiStore.showToast(t('common.toasts.memberRemoved'), 'success')
  } catch {
    uiStore.showToast(t('common.toasts.failedToRemoveMember'), 'error')
  } finally {
    saving.value = false
  }
}

function openNotifyModal(member) {
  notifyTarget.value = member
  notifyMessage.value = ''
  showNotifyModal.value = true
}

async function doNotify() {
  notifying.value = true
  try {
    await guildsApi.sendGuildNotification(guildStore.currentGuild.id, notifyTarget.value.user_id, notifyMessage.value)
    showNotifyModal.value = false
    uiStore.showToast(t('members.toasts.notificationSent'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('members.toasts.notificationFailed'), 'error')
  } finally {
    notifying.value = false
  }
}

async function doNotifyAll() {
  notifyingAll.value = true
  try {
    await guildsApi.sendGuildNotificationAll(guildStore.currentGuild.id, notifyAllMessage.value)
    showNotifyAllModal.value = false
    uiStore.showToast(t('members.toasts.allNotified'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('members.toasts.notificationFailed'), 'error')
  } finally {
    notifyingAll.value = false
  }
}

function confirmBan(member) {
  banTarget.value = member
  showBanConfirm.value = true
}

async function doBan() {
  banning.value = true
  try {
    await guildsApi.banGuildMember(guildStore.currentGuild.id, banTarget.value.user_id)
    const idx = members.value.findIndex(m => m.user_id === banTarget.value.user_id)
    if (idx !== -1) members.value[idx].status = 'banned'
    showBanConfirm.value = false
    uiStore.showToast(t('members.toasts.memberBanned'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('members.toasts.banFailed'), 'error')
  } finally {
    banning.value = false
  }
}

async function doUnban(member) {
  try {
    await guildsApi.unbanGuildMember(guildStore.currentGuild.id, member.user_id)
    const idx = members.value.findIndex(m => m.user_id === member.user_id)
    if (idx !== -1) members.value[idx].status = 'active'
    uiStore.showToast(t('members.toasts.memberUnbanned'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('members.toasts.unbanFailed'), 'error')
  }
}

// Member characters viewer
const showMemberChars = ref(false)
const memberChars = ref([])
const loadingMemberChars = ref(false)
const memberCharsTitle = ref('')

// Character detail modal
const showCharDetailModal = ref(false)
const charDetailTarget = ref(null)

function openCharDetailModal(character) {
  charDetailTarget.value = character
  showCharDetailModal.value = true
}

async function viewMemberChars(member) {
  const username = member.username ?? member.user?.username ?? 'Unknown'
  memberCharsTitle.value = t('members.memberCharactersTitle', { name: username })
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
    uiStore.showToast(`${user.username} added to guild`, 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.message ?? t('common.toasts.failedToAdd'), 'error')
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
    return t('members.ownership.transferCountdown', { countdown: transferCountdown.value })
  }
  return t('members.ownership.transferBtn')
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
    uiStore.showToast(t('members.toasts.ownershipTransferred'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('members.toasts.failedToTransfer'), 'error')
  } finally {
    transferring.value = false
  }
}
</script>
