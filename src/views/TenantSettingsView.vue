<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-6 max-w-2xl">
      <h1 class="wow-heading text-xl sm:text-2xl">{{ t('tenant.settingsTitle') }}</h1>

      <div v-if="loading" class="text-center py-8 text-text-muted">{{ t('common.labels.loading') }}</div>

      <form v-else-if="tenant" @submit.prevent="doSave" class="space-y-4">
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('tenant.name') }}</label>
          <input v-model="form.name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('tenant.description') }}</label>
          <textarea v-model="form.description" rows="3" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('tenant.slug') }}</label>
          <input v-model="form.slug" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          <p class="text-xs text-text-muted mt-1">{{ t('tenant.slugHelp') }}</p>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <button type="submit" :disabled="saving" class="px-4 py-2 text-sm bg-accent-gold/20 text-accent-gold border border-accent-gold/50 rounded hover:bg-accent-gold/30 transition-colors disabled:opacity-50">
            {{ saving ? t('common.labels.saving') : t('common.buttons.save') }}
          </button>
          <span v-if="saved" class="text-sm text-green-400">{{ t('common.labels.saved') }}</span>
          <span v-if="saveError" class="text-sm text-red-400">{{ saveError }}</span>
        </div>
      </form>

      <!-- Members section -->
      <div v-if="tenant" class="space-y-3">
        <h2 class="text-lg font-semibold text-text-primary">{{ t('tenant.membersTitle') }}</h2>
        <div v-if="membersLoading" class="text-sm text-text-muted">{{ t('common.labels.loading') }}</div>
        <div v-else class="space-y-2">
          <div
            v-for="m in members"
            :key="m.id"
            class="flex items-center justify-between gap-3 p-3 rounded bg-bg-tertiary border border-border-default"
          >
            <div>
              <span class="text-sm text-text-primary">{{ m.display_name || m.username }}</span>
              <span class="text-xs text-text-muted ml-2">({{ m.role }})</span>
            </div>
            <button
              v-if="m.role !== 'owner'"
              type="button"
              class="text-xs text-red-400 hover:text-red-300 transition-colors"
              @click="doRemoveMember(m)"
            >{{ t('common.buttons.remove') }}</button>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import AppShell from '@/components/layout/AppShell.vue'
import { useTenantStore } from '@/stores/tenant'
import * as tenantsApi from '@/api/tenants'

const { t } = useI18n()
const tenantStore = useTenantStore()

const tenant = ref(null)
const loading = ref(false)
const saving = ref(false)
const saved = ref(false)
const saveError = ref(null)
const members = ref([])
const membersLoading = ref(false)

const form = ref({ name: '', description: '', slug: '' })

async function fetchTenant() {
  if (!tenantStore.activeTenantId) return
  loading.value = true
  try {
    tenant.value = await tenantsApi.getTenant(tenantStore.activeTenantId)
    form.value = {
      name: tenant.value.name || '',
      description: tenant.value.description || '',
      slug: tenant.value.slug || '',
    }
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function fetchMembers() {
  if (!tenantStore.activeTenantId) return
  membersLoading.value = true
  try {
    members.value = await tenantsApi.getTenantMembers(tenantStore.activeTenantId)
  } catch {
    // ignore
  } finally {
    membersLoading.value = false
  }
}

async function doSave() {
  saving.value = true
  saved.value = false
  saveError.value = null
  try {
    tenant.value = await tenantsApi.updateTenant(tenantStore.activeTenantId, form.value)
    saved.value = true
    await tenantStore.fetchTenants()
  } catch (err) {
    saveError.value = err?.response?.data?.message || 'Failed to save'
  } finally {
    saving.value = false
  }
}

async function doRemoveMember(m) {
  if (!confirm(t('tenant.confirmRemoveMember', { name: m.username }))) return
  try {
    await tenantsApi.removeTenantMember(tenantStore.activeTenantId, m.user_id)
    await fetchMembers()
  } catch {
    // ignore
  }
}

onMounted(() => {
  fetchTenant()
  fetchMembers()
})
</script>
