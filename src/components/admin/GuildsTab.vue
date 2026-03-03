<template>
  <div class="space-y-6">
    <!-- Guilds table -->
    <WowCard>
      <div class="flex items-center justify-between mb-4">
        <h2 class="wow-heading text-base">{{ t('admin.guilds.title', { count: guilds.length }) }}</h2>
      </div>

      <div v-if="loading" class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>

      <div v-else class="overflow-x-auto">
        <!-- Pagination controls -->
        <div v-if="totalPages > 1" class="flex items-center justify-between mb-3 text-sm text-text-muted">
          <span>{{ t('admin.guilds.page', { current: currentPage, total: totalPages }) }}</span>
          <div class="flex gap-1">
            <WowButton variant="secondary" class="text-xs py-1 px-2" :disabled="currentPage <= 1" @click="currentPage--">←</WowButton>
            <WowButton variant="secondary" class="text-xs py-1 px-2" :disabled="currentPage >= totalPages" @click="currentPage++">→</WowButton>
          </div>
        </div>
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-bg-tertiary border-b border-border-default">
              <th class="hidden sm:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.users.id') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.guilds.name') }}</th>
              <th class="hidden md:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.guilds.realm') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.guilds.members') }}</th>
              <th class="hidden md:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.guilds.armoryConfig') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.guilds.owner') }}</th>
              <th class="hidden lg:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.guilds.created') }}</th>
              <th class="text-right px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.labels.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-default">
            <template v-for="(group, ownerName) in paginatedGroups" :key="ownerName">
              <!-- Owner group header -->
              <tr class="bg-bg-tertiary/70">
                <td :colspan="8" class="px-4 py-1.5 text-xs text-accent-gold font-semibold uppercase tracking-wide">
                  👑 {{ ownerName }}
                </td>
              </tr>
              <tr v-for="g in group" :key="g.id" class="hover:bg-bg-tertiary/50 transition-colors">
                <td class="hidden sm:table-cell px-4 py-2.5 text-text-muted">{{ g.id }}</td>
                <td class="px-4 py-2.5">
                  <div class="text-text-primary font-medium">{{ g.name }}</div>
                  <div v-if="g.faction" class="text-xs text-text-muted">{{ g.faction }}</div>
                </td>
                <td class="hidden md:table-cell px-4 py-2.5 text-text-muted">{{ g.realm_name }}</td>
                <td class="px-4 py-2.5">
                  <span class="text-accent-gold font-medium">{{ g.member_count }}</span>
                </td>
                <td class="hidden md:table-cell px-4 py-2.5 text-text-muted text-xs">
                  <span class="capitalize">{{ g.armory_provider || 'warmane' }}</span>
                </td>
                <td class="px-4 py-2.5 text-text-muted text-xs">{{ g.creator_username || '—' }}</td>
                <td class="hidden lg:table-cell px-4 py-2.5 text-text-muted text-xs">{{ formatDate(g.created_at) }}</td>
                <td class="px-4 py-2.5 text-right">
                  <div class="flex flex-wrap gap-1 justify-end">
                    <WowButton variant="secondary" class="text-xs py-1 px-2" @click="viewMembers(g)">{{ t('admin.guilds.viewMembers') }}</WowButton>
                    <WowButton variant="secondary" class="text-xs py-1 px-2" @click="openFeaturesModal(g)">{{ t('admin.guilds.features') }}</WowButton>
                    <WowButton variant="danger" class="text-xs py-1 px-2" @click="confirmDeleteGuild(g)">{{ t('admin.guilds.deleteGuild') }}</WowButton>
                  </div>
                </td>
              </tr>
            </template>
            <tr v-if="!guilds.length">
              <td colspan="8" class="px-4 py-8 text-center text-text-muted">{{ t('admin.guilds.noGuilds') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </WowCard>

    <!-- Guild Members Modal -->
    <WowModal v-model="showMembersModal" :title="selectedGuild ? `${selectedGuild.name} — ${t('common.labels.members')}` : t('common.labels.members')" size="xl">
      <div v-if="membersLoading" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="membersError" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ membersError }}</div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-bg-tertiary border-b border-border-default">
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.username') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.role') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.status') }}</th>
              <th class="hidden sm:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.guilds.joined') }}</th>
              <th class="text-right px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.labels.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-default">
            <tr v-for="m in guildMembers" :key="m.user_id" class="hover:bg-bg-tertiary/50 transition-colors">
              <td class="px-4 py-2.5 text-text-primary font-medium">{{ m.username || `User #${m.user_id}` }}</td>
              <td class="px-4 py-2.5">
                <select
                  class="bg-bg-secondary border border-border-default text-text-primary text-xs rounded px-2 py-1"
                  :value="m.role"
                  @change="changeMemberRole(m, $event.target.value)"
                >
                  <option v-for="r in availableRoles" :key="r.name" :value="r.name">{{ r.display_name || r.name }}</option>
                </select>
              </td>
              <td class="px-4 py-2.5">
                <span
                  class="inline-block px-2 py-0.5 text-xs rounded-full font-medium"
                  :class="m.status === 'active' ? 'bg-green-900/50 text-green-300 border border-green-600' : 'bg-yellow-900/50 text-yellow-300 border border-yellow-600'"
                >{{ m.status }}</span>
              </td>
              <td class="hidden sm:table-cell px-4 py-2.5 text-text-muted text-xs">{{ formatDate(m.created_at) }}</td>
              <td class="px-4 py-2.5">
                <div class="flex gap-1.5 justify-end whitespace-nowrap">
                  <WowButton v-if="!isGuildOwner(m)" variant="secondary" class="text-xs py-1.5 px-3" @click="openTransferModal(m)">{{ t('admin.guilds.transferOwnership') }}</WowButton>
                  <WowButton variant="secondary" class="text-xs py-1.5 px-3" @click="openNotifyModal(m)">{{ t('admin.guilds.sendNotification') }}</WowButton>
                  <WowButton variant="danger" class="text-xs py-1.5 px-3" @click="confirmRemoveMember(m)">{{ t('admin.guilds.removeMember') }}</WowButton>
                </div>
              </td>
            </tr>
            <tr v-if="!guildMembers.length">
              <td colspan="5" class="px-4 py-4 text-center text-text-muted">{{ t('admin.guilds.noMembers') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <template #footer>
        <WowButton variant="secondary" @click="showMembersModal = false">{{ t('common.buttons.close') }}</WowButton>
      </template>
    </WowModal>

    <!-- Transfer Ownership Confirmation -->
    <WowModal v-model="showTransferModal" :title="t('admin.guilds.transferOwnership')" size="sm">
      <p class="text-text-muted text-sm">
        {{ t('admin.guilds.transferConfirm', { user: transferTarget?.username, guild: selectedGuild?.name }) }}
      </p>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <WowButton variant="secondary" @click="showTransferModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="primary" @click="doTransferOwnership">{{ t('admin.guilds.transferOwnership') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Send Notification Modal -->
    <WowModal v-model="showNotifyModal" :title="t('admin.guilds.sendNotification')" size="sm">
      <div class="space-y-3">
        <p class="text-text-muted text-sm">
          {{ t('admin.guilds.notifyTo', { user: notifyTarget?.username }) }}
        </p>
        <textarea
          v-model="notifyMessage"
          rows="3"
          class="w-full bg-bg-secondary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-accent-gold focus:outline-none"
          :placeholder="t('admin.guilds.notifyPlaceholder')"
        />
      </div>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <WowButton variant="secondary" @click="showNotifyModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="primary" :disabled="!notifyMessage.trim()" @click="doSendNotification">{{ t('admin.guilds.send') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Delete Guild Confirmation -->
    <WowModal v-model="showDeleteGuildModal" :title="t('admin.guilds.deleteGuild')" size="sm">
      <p class="text-text-muted text-sm">
        {{ t('admin.guilds.deleteConfirm', { guild: deleteGuildTarget?.name }) }}
      </p>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <WowButton variant="secondary" @click="showDeleteGuildModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="danger" @click="doDeleteGuild">{{ t('admin.guilds.deleteGuild') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Remove Member Confirmation -->
    <WowModal v-model="showRemoveMemberModal" :title="t('admin.guilds.removeMember')" size="sm">
      <p class="text-text-muted text-sm">
        {{ t('admin.guilds.removeConfirm', { user: removeMemberTarget?.username, guild: selectedGuild?.name }) }}
      </p>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <WowButton variant="secondary" @click="showRemoveMemberModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="danger" @click="doRemoveMember">{{ t('admin.guilds.removeMember') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Feature Flags Modal -->
    <WowModal v-model="showFeaturesModal" :title="t('admin.guilds.featureFlags')" size="sm">
      <div v-if="featuresLoading" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else class="space-y-3">
        <p class="text-text-muted text-sm mb-2">{{ featuresGuild?.name }}</p>
        <label v-for="key in featureKeys" :key="key" class="flex items-center gap-3 cursor-pointer">
          <button
            type="button"
            class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0"
            :class="featuresForm[key] ? 'bg-accent-gold' : 'bg-bg-tertiary border border-border-default'"
            @click="featuresForm[key] = !featuresForm[key]"
          >
            <span
              class="inline-block h-4 w-4 rounded-full bg-white transition-transform"
              :class="featuresForm[key] ? 'translate-x-6' : 'translate-x-1'"
            />
          </button>
          <span class="text-sm text-text-primary">{{ featureLabels[key] }}</span>
        </label>
      </div>
      <template #footer>
        <div class="flex gap-2 justify-end">
          <WowButton variant="secondary" @click="showFeaturesModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton :loading="featuresSaving" @click="saveFeatures">{{ t('admin.system.saveSettings') }}</WowButton>
        </div>
      </template>
    </WowModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import { useUiStore } from '@/stores/ui'
import * as guildsApi from '@/api/guilds'
import * as rolesApi from '@/api/roles'
import * as adminApi from '@/api/admin'

const { t } = useI18n()
const uiStore = useUiStore()

const guilds = ref([])
const loading = ref(true)
const error = ref(null)
const ITEMS_PER_PAGE = 20
const currentPage = ref(1)

// Group guilds by owner and sort
const sortedGroups = computed(() => {
  const groups = {}
  for (const g of guilds.value) {
    const owner = g.creator_username || '—'
    if (!groups[owner]) groups[owner] = []
    groups[owner].push(g)
  }
  // Sort keys alphabetically
  const sorted = {}
  for (const key of Object.keys(groups).sort()) {
    sorted[key] = groups[key]
  }
  return sorted
})

// Flatten for pagination
const flatGuildList = computed(() => {
  const result = []
  for (const [owner, gs] of Object.entries(sortedGroups.value)) {
    for (const g of gs) {
      result.push({ owner, guild: g })
    }
  }
  return result
})

const totalPages = computed(() => Math.max(1, Math.ceil(flatGuildList.value.length / ITEMS_PER_PAGE)))

const paginatedGroups = computed(() => {
  const start = (currentPage.value - 1) * ITEMS_PER_PAGE
  const end = start + ITEMS_PER_PAGE
  const slice = flatGuildList.value.slice(start, end)
  const groups = {}
  for (const { owner, guild } of slice) {
    if (!groups[owner]) groups[owner] = []
    groups[owner].push(guild)
  }
  return groups
})

// Members modal
const showMembersModal = ref(false)
const selectedGuild = ref(null)
const guildMembers = ref([])
const membersLoading = ref(false)
const membersError = ref(null)
const availableRoles = ref([])

// Transfer ownership
const showTransferModal = ref(false)
const transferTarget = ref(null)

// Notification
const showNotifyModal = ref(false)
const notifyTarget = ref(null)
const notifyMessage = ref('')

// Delete guild
const showDeleteGuildModal = ref(false)
const deleteGuildTarget = ref(null)

// Remove member
const showRemoveMemberModal = ref(false)
const removeMemberTarget = ref(null)

// Feature flags
const showFeaturesModal = ref(false)
const featuresGuild = ref(null)
const featuresLoading = ref(false)
const featuresSaving = ref(false)
const featureKeys = ['attendance', 'templates', 'series', 'character_sync', 'notifications']
const featureLabels = computed(() => ({
  attendance: t('admin.guilds.featureAttendance'),
  templates: t('admin.guilds.featureTemplates'),
  series: t('admin.guilds.featureSeries'),
  character_sync: t('admin.guilds.featureCharacterSync'),
  notifications: t('admin.guilds.featureNotifications'),
}))
const featuresForm = ref({
  attendance: false,
  templates: false,
  series: false,
  character_sync: false,
  notifications: false,
})

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

async function loadGuilds() {
  loading.value = true
  try {
    guilds.value = await guildsApi.adminGetAllGuilds()
  } catch (err) {
    error.value = err?.response?.data?.message ?? t('admin.guilds.loadError')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadGuilds()
  // Load role objects for the dropdown (with display_name)
  // Filter out global_admin — that should only be assigned from the Users tab
  try {
    const roles = await rolesApi.getRoles()
    availableRoles.value = roles.filter(r => r.name !== 'global_admin')
  } catch {
    availableRoles.value = [
      { name: 'guild_admin', display_name: 'Guild Admin' },
      { name: 'officer', display_name: 'Officer' },
      { name: 'raid_leader', display_name: 'Raid Leader' },
      { name: 'member', display_name: 'Member' },
    ]
  }
})

async function viewMembers(guild) {
  selectedGuild.value = guild
  guildMembers.value = []
  membersError.value = null
  membersLoading.value = true
  showMembersModal.value = true
  try {
    guildMembers.value = await guildsApi.adminGetGuildMembers(guild.id)
  } catch (err) {
    membersError.value = err?.response?.data?.message ?? t('admin.guilds.loadError')
  } finally {
    membersLoading.value = false
  }
}

async function changeMemberRole(member, newRole) {
  if (newRole === member.role) return
  try {
    await guildsApi.adminUpdateMemberRole(selectedGuild.value.id, member.user_id, newRole)
    member.role = newRole
    uiStore.showToast(t('admin.guilds.roleUpdated'))
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('admin.guilds.loadError'), 'error')
  }
}

function openTransferModal(member) {
  transferTarget.value = member
  showTransferModal.value = true
}

function isGuildOwner(member) {
  return selectedGuild.value && member.user_id === selectedGuild.value.created_by
}

async function doTransferOwnership() {
  try {
    await guildsApi.adminTransferOwnership(selectedGuild.value.id, transferTarget.value.user_id)
    showTransferModal.value = false
    uiStore.showToast(t('admin.guilds.ownershipTransferred'))
    await loadGuilds()
    await viewMembers(selectedGuild.value)
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('admin.guilds.loadError'), 'error')
  }
}

function openNotifyModal(member) {
  notifyTarget.value = member
  notifyMessage.value = ''
  showNotifyModal.value = true
}

async function doSendNotification() {
  try {
    await guildsApi.adminSendNotification(selectedGuild.value.id, notifyTarget.value.user_id, notifyMessage.value)
    showNotifyModal.value = false
    uiStore.showToast(t('admin.guilds.notificationSent'))
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('admin.guilds.loadError'), 'error')
  }
}

function confirmDeleteGuild(guild) {
  deleteGuildTarget.value = guild
  showDeleteGuildModal.value = true
}

async function doDeleteGuild() {
  try {
    await guildsApi.adminDeleteGuild(deleteGuildTarget.value.id)
    showDeleteGuildModal.value = false
    uiStore.showToast(t('admin.guilds.guildDeleted'))
    await loadGuilds()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('admin.guilds.loadError'), 'error')
  }
}

function confirmRemoveMember(member) {
  removeMemberTarget.value = member
  showRemoveMemberModal.value = true
}

async function doRemoveMember() {
  try {
    await guildsApi.adminRemoveMember(selectedGuild.value.id, removeMemberTarget.value.user_id)
    showRemoveMemberModal.value = false
    guildMembers.value = guildMembers.value.filter(m => m.user_id !== removeMemberTarget.value.user_id)
    uiStore.showToast(t('admin.guilds.memberRemovedSuccess'))
    await loadGuilds()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('admin.guilds.loadError'), 'error')
  }
}

async function openFeaturesModal(guild) {
  featuresGuild.value = guild
  featuresLoading.value = true
  showFeaturesModal.value = true
  try {
    const data = await adminApi.getGuildFeatures(guild.id)
    featuresForm.value = {
      attendance: !!data.attendance,
      templates: !!data.templates,
      series: !!data.series,
      character_sync: !!data.character_sync,
      notifications: !!data.notifications,
    }
  } catch {
    featuresForm.value = { attendance: true, templates: true, series: true, character_sync: true, notifications: true }
  } finally {
    featuresLoading.value = false
  }
}

async function saveFeatures() {
  featuresSaving.value = true
  try {
    await adminApi.updateGuildFeatures(featuresGuild.value.id, { ...featuresForm.value })
    showFeaturesModal.value = false
    uiStore.showToast(t('admin.guilds.featuresUpdated'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? t('admin.guilds.loadError'), 'error')
  } finally {
    featuresSaving.value = false
  }
}
</script>
