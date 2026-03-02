<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6">
      <h1 class="wow-heading text-xl sm:text-2xl">{{ t('roles.title') }}</h1>

      <div v-if="!permissions.can('manage_roles')" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">
        {{ t('roles.noPermission') }}
      </div>

      <template v-else>
        <!-- Roles list -->
        <WowCard>
          <div class="flex items-center justify-between mb-4">
            <h2 class="wow-heading text-base">{{ t('roles.allRoles') }} ({{ roles.length }})</h2>
            <WowButton @click="openCreateRole">+ {{ t('roles.newRole') }}</WowButton>
          </div>

          <div v-if="loading" class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
          <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>

          <div v-else class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-bg-tertiary border-b border-border-default">
                  <th class="text-left px-2 sm:px-4 py-2 sm:py-2.5 text-xs text-text-muted uppercase">Role</th>
                  <th class="text-left px-2 sm:px-4 py-2 sm:py-2.5 text-xs text-text-muted uppercase">Level</th>
                  <th class="text-left px-2 sm:px-4 py-2 sm:py-2.5 text-xs text-text-muted uppercase">Permissions</th>
                  <th class="text-left px-2 sm:px-4 py-2 sm:py-2.5 text-xs text-text-muted uppercase">Can Assign</th>
                  <th class="text-left px-2 sm:px-4 py-2 sm:py-2.5 text-xs text-text-muted uppercase">Type</th>
                  <th class="text-right px-2 sm:px-4 py-2 sm:py-2.5 text-xs text-text-muted uppercase">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-default">
                <tr v-for="role in roles" :key="role.id" class="hover:bg-bg-tertiary/50 transition-colors">
                  <td class="px-2 sm:px-4 py-2 sm:py-2.5">
                    <div class="text-text-primary font-medium">{{ role.display_name }}</div>
                    <div class="text-xs text-text-muted">{{ role.name }}</div>
                  </td>
                  <td class="px-2 sm:px-4 py-2 sm:py-2.5 text-text-muted">{{ role.level }}</td>
                  <td class="px-2 sm:px-4 py-2 sm:py-2.5">
                    <span class="text-accent-gold text-xs font-medium">{{ role.permissions.length }} permissions</span>
                  </td>
                  <td class="px-2 sm:px-4 py-2 sm:py-2.5">
                    <div class="flex flex-wrap gap-1">
                      <span
                        v-for="grantee in role.can_grant"
                        :key="grantee"
                        class="inline-block px-1.5 py-0.5 text-[10px] rounded bg-bg-tertiary border border-border-default text-text-muted"
                      >{{ grantee }}</span>
                      <span v-if="!role.can_grant.length" class="text-xs text-text-muted">—</span>
                    </div>
                  </td>
                  <td class="px-2 sm:px-4 py-2 sm:py-2.5">
                    <span
                      class="inline-block px-2 py-0.5 text-xs rounded-full font-medium"
                      :class="role.is_system ? 'bg-blue-900/50 text-blue-300 border border-blue-600' : 'bg-green-900/50 text-green-300 border border-green-600'"
                    >{{ role.is_system ? 'System' : 'Custom' }}</span>
                  </td>
                  <td class="px-2 sm:px-4 py-2 sm:py-2.5 text-right space-x-2">
                    <WowButton variant="secondary" class="text-xs py-1 px-2" @click="openEditRole(role)">{{ t('common.buttons.edit') }}</WowButton>
                    <WowButton
                      v-if="!role.is_system"
                      variant="danger"
                      class="text-xs py-1 px-2"
                      @click="confirmDeleteRole(role)"
                    >{{ t('common.buttons.delete') }}</WowButton>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </WowCard>

        <!-- All permissions reference -->
        <WowCard>
          <h2 class="wow-heading text-base mb-4">{{ t('roles.availablePermissions') }} ({{ allPermissions.length }})</h2>

          <div v-if="permissionsLoading" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
          <div v-else>
            <div v-for="cat in permissionCategories" :key="cat" class="mb-4">
              <h3 class="text-xs text-accent-gold uppercase tracking-wider mb-2 px-1">{{ cat }}</h3>
              <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                <div
                  v-for="perm in permissionsByCategory(cat)"
                  :key="perm.code"
                  class="px-3 py-2 rounded bg-bg-tertiary border border-border-default"
                >
                  <div class="text-sm text-text-primary">{{ perm.display_name }}</div>
                  <div class="text-xs text-text-muted">{{ perm.code }}</div>
                </div>
              </div>
            </div>
          </div>
        </WowCard>

        <!-- Grant Rules -->
        <WowCard>
          <div class="flex items-center justify-between mb-4">
            <h2 class="wow-heading text-base">{{ t('roles.grantRules') }}</h2>
            <WowButton @click="showGrantRuleModal = true">+ {{ t('roles.addRule') }}</WowButton>
          </div>
          <p class="text-text-muted text-sm mb-4">{{ t('roles.grantRulesHelp') }}</p>

          <div v-if="grantRulesLoading" class="h-24 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
          <div v-else class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-bg-tertiary border-b border-border-default">
                  <th class="text-left px-2 sm:px-4 py-2 sm:py-2.5 text-xs text-text-muted uppercase">Role (Granter)</th>
                  <th class="text-center px-2 sm:px-4 py-2 sm:py-2.5 text-xs text-text-muted uppercase"></th>
                  <th class="text-left px-2 sm:px-4 py-2 sm:py-2.5 text-xs text-text-muted uppercase">Can Assign (Grantee)</th>
                  <th class="text-right px-2 sm:px-4 py-2 sm:py-2.5 text-xs text-text-muted uppercase">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-default">
                <tr v-for="rule in grantRules" :key="rule.id" class="hover:bg-bg-tertiary/50 transition-colors">
                  <td class="px-2 sm:px-4 py-2 sm:py-2.5 text-text-primary font-medium">{{ roleDisplayName(rule.granter_role_name) }}</td>
                  <td class="px-2 sm:px-4 py-2 sm:py-2.5 text-center text-accent-gold">→</td>
                  <td class="px-2 sm:px-4 py-2 sm:py-2.5 text-text-primary">{{ roleDisplayName(rule.grantee_role_name) }}</td>
                  <td class="px-2 sm:px-4 py-2 sm:py-2.5 text-right">
                    <WowButton variant="danger" class="text-xs py-1 px-2" @click="doDeleteGrantRule(rule)">{{ t('common.buttons.remove') }}</WowButton>
                  </td>
                </tr>
                <tr v-if="!grantRules.length">
                  <td colspan="4" class="px-4 py-4 text-center text-text-muted text-sm">{{ t('roles.noGrantRules') }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </WowCard>
      </template>
    </div>

    <!-- Create/Edit Role Modal -->
    <WowModal v-model="showRoleModal" :title="editingRole ? t('roles.editRole') : t('roles.createRole')" size="lg">
      <form @submit.prevent="saveRole" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('roles.nameInternal') }}</label>
            <input
              v-model="roleForm.name"
              required
              :disabled="editingRole?.is_system"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none disabled:opacity-50"
              placeholder="e.g. raid_leader"
            />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('roles.displayName') }}</label>
            <input
              v-model="roleForm.display_name"
              required
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
              placeholder="e.g. Raid Leader"
            />
          </div>
        </div>

        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('common.labels.description') }}</label>
          <input
            v-model="roleForm.description"
            class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
            :placeholder="t('roles.descriptionPlaceholder')"
          />
        </div>

        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.level') }}</label>
          <input
            v-model.number="roleForm.level"
            type="number"
            min="0"
            max="100"
            class="w-32 bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
          />
        </div>

        <!-- Permission checkboxes grouped by category -->
        <div>
          <label class="block text-xs text-text-muted mb-2">{{ t('roles.permissions') }}</label>
          <div class="max-h-80 overflow-y-auto border border-border-default rounded p-3 space-y-4 bg-bg-tertiary/30">
            <div v-for="cat in permissionCategories" :key="cat">
              <div class="flex items-center gap-2 mb-2">
                <h4 class="text-xs text-accent-gold uppercase tracking-wider">{{ cat }}</h4>
                <button type="button" class="text-[10px] text-text-muted hover:text-accent-gold" @click="toggleCategory(cat, true)">All</button>
                <button type="button" class="text-[10px] text-text-muted hover:text-accent-gold" @click="toggleCategory(cat, false)">None</button>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-1">
                <label
                  v-for="perm in permissionsByCategory(cat)"
                  :key="perm.code"
                  class="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-bg-tertiary cursor-pointer text-sm"
                >
                  <input
                    type="checkbox"
                    :value="perm.code"
                    v-model="roleForm.permissions"
                    class="w-3.5 h-3.5 rounded bg-bg-tertiary border border-border-default accent-accent-gold"
                  />
                  <span class="text-text-primary">{{ perm.display_name }}</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <div v-if="roleFormError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ roleFormError }}</div>
      </form>

      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showRoleModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton :loading="savingRole" @click="saveRole">{{ editingRole ? t('common.fields.saveChanges') : t('roles.createRole') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Delete Role Confirmation -->
    <WowModal v-model="showDeleteConfirm" :title="t('roles.deleteRole')" size="sm">
      <p class="text-text-muted">
        Permanently delete the role <strong class="text-text-primary">{{ deleteTarget?.display_name }}</strong>?
        Members with this role will lose their permissions.
      </p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showDeleteConfirm = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="danger" :loading="deletingRole" @click="doDeleteRole">{{ t('common.buttons.delete') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Add Grant Rule Modal -->
    <WowModal v-model="showGrantRuleModal" :title="t('roles.addGrantRule')" size="sm">
      <form @submit.prevent="doCreateGrantRule" class="space-y-4">
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('roles.granterLabel') }}</label>
          <select v-model="grantRuleForm.granter_role_id" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option :value="null" disabled>{{ t('common.fields.selectRole') }}</option>
            <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.display_name }} (level {{ r.level }})</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('roles.granteeLabel') }}</label>
          <select v-model="grantRuleForm.grantee_role_id" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option :value="null" disabled>{{ t('common.fields.selectRole') }}</option>
            <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.display_name }} (level {{ r.level }})</option>
          </select>
        </div>
        <div v-if="grantRuleError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ grantRuleError }}</div>
      </form>

      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showGrantRuleModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton :loading="creatingGrantRule" @click="doCreateGrantRule">{{ t('roles.addRule') }}</WowButton>
        </div>
      </template>
    </WowModal>
  </AppShell>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import { useUiStore } from '@/stores/ui'
import { usePermissions } from '@/composables/usePermissions'
import * as rolesApi from '@/api/roles'
import { useI18n } from 'vue-i18n'

const uiStore = useUiStore()
const permissions = usePermissions()
const { t } = useI18n()

// Roles state
const roles = ref([])
const loading = ref(true)
const error = ref(null)

// All permissions
const allPermissions = ref([])
const permissionsLoading = ref(true)

// Grant rules
const grantRules = ref([])
const grantRulesLoading = ref(true)

// Role form
const showRoleModal = ref(false)
const editingRole = ref(null)
const savingRole = ref(false)
const roleFormError = ref(null)
const roleForm = reactive({
  name: '',
  display_name: '',
  description: '',
  level: 0,
  permissions: []
})

// Delete role
const showDeleteConfirm = ref(false)
const deleteTarget = ref(null)
const deletingRole = ref(false)

// Grant rule form
const showGrantRuleModal = ref(false)
const creatingGrantRule = ref(false)
const grantRuleError = ref(null)
const grantRuleForm = reactive({
  granter_role_id: null,
  grantee_role_id: null
})

// Computed
const permissionCategories = computed(() => {
  const cats = [...new Set(allPermissions.value.map(p => p.category))]
  return cats.sort()
})

function permissionsByCategory(category) {
  return allPermissions.value.filter(p => p.category === category)
}

function roleDisplayName(roleName) {
  const role = roles.value.find(r => r.name === roleName)
  return role ? role.display_name : roleName
}

function toggleCategory(category, on) {
  const codes = permissionsByCategory(category).map(p => p.code)
  if (on) {
    const existing = new Set(roleForm.permissions)
    codes.forEach(c => existing.add(c))
    roleForm.permissions = [...existing]
  } else {
    const toRemove = new Set(codes)
    roleForm.permissions = roleForm.permissions.filter(c => !toRemove.has(c))
  }
}

// Load data
onMounted(async () => {
  if (!permissions.can('manage_roles')) return
  await Promise.all([loadRoles(), loadPermissions(), loadGrantRules()])
})

async function loadRoles() {
  loading.value = true
  try {
    roles.value = await rolesApi.getRoles()
  } catch (err) {
    error.value = err?.response?.data?.message ?? 'Failed to load roles'
  } finally {
    loading.value = false
  }
}

async function loadPermissions() {
  permissionsLoading.value = true
  try {
    allPermissions.value = await rolesApi.getPermissions()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.message ?? t('roles.toasts.failedToLoadPermissions'), 'error')
  } finally {
    permissionsLoading.value = false
  }
}

async function loadGrantRules() {
  grantRulesLoading.value = true
  try {
    grantRules.value = await rolesApi.getGrantRules()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.message ?? t('roles.toasts.failedToLoadRules'), 'error')
  } finally {
    grantRulesLoading.value = false
  }
}

// Role CRUD
function openCreateRole() {
  editingRole.value = null
  roleForm.name = ''
  roleForm.display_name = ''
  roleForm.description = ''
  roleForm.level = 0
  roleForm.permissions = []
  roleFormError.value = null
  showRoleModal.value = true
}

function openEditRole(role) {
  editingRole.value = role
  roleForm.name = role.name
  roleForm.display_name = role.display_name
  roleForm.description = role.description || ''
  roleForm.level = role.level
  roleForm.permissions = [...role.permissions]
  roleFormError.value = null
  showRoleModal.value = true
}

async function saveRole() {
  roleFormError.value = null
  savingRole.value = true
  try {
    const data = {
      name: roleForm.name,
      display_name: roleForm.display_name,
      description: roleForm.description || null,
      level: roleForm.level,
      permissions: roleForm.permissions
    }

    if (editingRole.value) {
      await rolesApi.updateRole(editingRole.value.id, data)
      uiStore.showToast(t('common.toasts.roleUpdated'), 'success')
    } else {
      await rolesApi.createRole(data)
      uiStore.showToast(t('roles.toasts.roleCreated'), 'success')
    }

    showRoleModal.value = false
    await loadRoles()
  } catch (err) {
    roleFormError.value = err?.response?.data?.message ?? 'Failed to save role'
  } finally {
    savingRole.value = false
  }
}

function confirmDeleteRole(role) {
  deleteTarget.value = role
  showDeleteConfirm.value = true
}

async function doDeleteRole() {
  deletingRole.value = true
  try {
    await rolesApi.deleteRole(deleteTarget.value.id)
    uiStore.showToast(t('roles.toasts.roleDeleted'), 'success')
    showDeleteConfirm.value = false
    await loadRoles()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.message ?? t('roles.toasts.failedToDeleteRole'), 'error')
  } finally {
    deletingRole.value = false
  }
}

// Grant rules
async function doCreateGrantRule() {
  if (!grantRuleForm.granter_role_id || !grantRuleForm.grantee_role_id) {
    grantRuleError.value = 'Both roles are required'
    return
  }
  grantRuleError.value = null
  creatingGrantRule.value = true
  try {
    await rolesApi.createGrantRule({
      granter_role_id: grantRuleForm.granter_role_id,
      grantee_role_id: grantRuleForm.grantee_role_id
    })
    uiStore.showToast(t('roles.toasts.grantRuleAdded'), 'success')
    showGrantRuleModal.value = false
    grantRuleForm.granter_role_id = null
    grantRuleForm.grantee_role_id = null
    await Promise.all([loadRoles(), loadGrantRules()])
  } catch (err) {
    grantRuleError.value = err?.response?.data?.message ?? 'Failed to add grant rule'
  } finally {
    creatingGrantRule.value = false
  }
}

async function doDeleteGrantRule(rule) {
  try {
    await rolesApi.deleteGrantRule(rule.id)
    uiStore.showToast(t('roles.toasts.grantRuleRemoved'), 'success')
    await Promise.all([loadRoles(), loadGrantRules()])
  } catch (err) {
    uiStore.showToast(err?.response?.data?.message ?? t('roles.toasts.failedToRemoveRule'), 'error')
  }
}
</script>
