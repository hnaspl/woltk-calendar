<template>
  <div class="space-y-6">
    <!-- Users table -->
    <WowCard>
      <div class="flex items-center justify-between mb-4">
        <h2 class="wow-heading text-base">{{ t('admin.users.title', { count: users.length }) }}</h2>
      </div>

      <div v-if="loading" class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-bg-tertiary border-b border-border-default">
              <th class="hidden sm:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.users.id') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.username') }}</th>
              <th class="hidden md:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.email') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.status') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.users.admin') }}</th>
              <th class="hidden lg:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.users.registered') }}</th>
              <th class="text-right px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.labels.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-default">
            <tr v-for="u in users" :key="u.id" class="hover:bg-bg-tertiary/50 transition-colors">
              <td class="hidden sm:table-cell px-4 py-2.5 text-text-muted">{{ u.id }}</td>
              <td class="px-4 py-2.5 text-text-primary font-medium">{{ u.username }}</td>
              <td class="hidden md:table-cell px-4 py-2.5 text-text-muted">{{ u.email }}</td>
              <td class="px-4 py-2.5">
                <span
                  class="inline-block px-2 py-0.5 text-xs rounded-full font-medium"
                  :class="u.is_active ? 'bg-green-900/50 text-green-300 border border-green-600' : 'bg-red-900/50 text-red-300 border border-red-600'"
                >
                  {{ u.is_active ? t('common.status.active') : t('admin.users.blocked') }}
                </span>
              </td>
              <td class="px-4 py-2.5">
                <span v-if="u.is_admin" class="text-accent-gold text-xs font-bold">{{ t('admin.users.admin') }}</span>
                <span v-else class="text-text-muted text-xs">—</span>
              </td>
              <td class="hidden lg:table-cell px-4 py-2.5 text-text-muted text-xs">{{ formatDate(u.created_at) }}</td>
              <td class="px-4 py-2.5 text-right">
                <div class="flex flex-wrap gap-1 justify-end">
                <template v-if="u.id !== authStore.user.id && u.id !== 1">
                  <WowButton
                    v-if="!u.is_admin"
                    variant="secondary"
                    class="text-xs py-1 px-2"
                    @click="toggleAdmin(u)"
                  >{{ t('admin.users.promoteAdmin') }}</WowButton>
                  <WowButton
                    v-else
                    variant="secondary"
                    class="text-xs py-1 px-2"
                    @click="toggleAdmin(u)"
                  >{{ t('admin.users.revokeAdmin') }}</WowButton>
                  <WowButton
                    v-if="u.is_active"
                    variant="secondary"
                    class="text-xs py-1 px-2"
                    @click="toggleBlock(u)"
                  >{{ t('admin.users.block') }}</WowButton>
                  <WowButton
                    v-else
                    variant="secondary"
                    class="text-xs py-1 px-2"
                    @click="toggleBlock(u)"
                  >{{ t('admin.users.unblock') }}</WowButton>
                  <WowButton variant="danger" class="text-xs py-1 px-2" @click="confirmDelete(u)">{{ t('common.buttons.delete') }}</WowButton>
                </template>
                <span v-else-if="u.id === authStore.user.id" class="text-text-muted text-xs italic">{{ t('common.labels.you') }}</span>
                <span v-else class="text-text-muted text-xs italic">{{ t('admin.users.primaryAdmin') }}</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WowCard>

    <!-- Delete confirmation -->
    <WowModal v-model="showDeleteConfirm" :title="t('admin.users.deleteUser')" size="sm">
      <p class="text-text-muted">{{ t('admin.users.deleteConfirm', { name: deleteTarget?.username }) }}</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showDeleteConfirm = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="danger" :loading="deleting" @click="doDelete">{{ t('common.buttons.delete') }}</WowButton>
        </div>
      </template>
    </WowModal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import * as adminApi from '@/api/admin'
import { useFormatting } from '@/composables/useFormatting'

const { t } = useI18n()
const authStore = useAuthStore()
const uiStore = useUiStore()
const { formatDate } = useFormatting()

const users = ref([])
const loading = ref(true)
const error = ref(null)
const showDeleteConfirm = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    users.value = await adminApi.getUsers()
  } catch (err) {
    error.value = err?.response?.data?.message ?? 'Failed to load users'
  } finally {
    loading.value = false
  }
})

async function toggleBlock(user) {
  try {
    const updated = await adminApi.updateUser(user.id, { is_active: !user.is_active })
    const idx = users.value.findIndex(u => u.id === user.id)
    if (idx !== -1) users.value[idx] = updated
    uiStore.showToast(t(updated.is_active ? 'admin.system.toasts.userUnblocked' : 'admin.system.toasts.userBlocked'), 'success')
  } catch {
    uiStore.showToast(t('admin.system.toasts.failedToUpdateUser'), 'error')
  }
}

async function toggleAdmin(user) {
  try {
    const updated = await adminApi.updateUser(user.id, { is_admin: !user.is_admin })
    const idx = users.value.findIndex(u => u.id === user.id)
    if (idx !== -1) users.value[idx] = updated
    const msg = updated.is_admin
      ? `${updated.username} promoted to Global Admin`
      : `${updated.username} admin status revoked`
    uiStore.showToast(msg, 'success')
  } catch {
    uiStore.showToast(t('admin.system.toasts.failedToUpdateAdmin'), 'error')
  }
}

function confirmDelete(user) {
  deleteTarget.value = user
  showDeleteConfirm.value = true
}

async function doDelete() {
  deleting.value = true
  try {
    await adminApi.deleteUser(deleteTarget.value.id)
    users.value = users.value.filter(u => u.id !== deleteTarget.value.id)
    showDeleteConfirm.value = false
    uiStore.showToast(t('admin.system.toasts.userDeleted'), 'success')
  } catch {
    uiStore.showToast(t('admin.system.toasts.failedToDeleteUser'), 'error')
  } finally {
    deleting.value = false
  }
}
</script>
