<template>
  <div class="space-y-6">
    <!-- Tenants table -->
    <WowCard>
      <div class="flex items-center justify-between mb-4">
        <h2 class="wow-heading text-base">{{ t('admin.tenants.title') }}</h2>
        <span class="text-sm text-text-muted bg-bg-tertiary border border-border-default rounded-full px-2.5 py-0.5">{{ tenants.length }} {{ t('admin.tenants.total') }}</span>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />

      <!-- Tenants table -->
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-bg-tertiary border-b border-border-default">
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.tenants.name') }}</th>
              <th class="hidden sm:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.tenants.owner') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.tenants.plan') }}</th>
              <th class="hidden md:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.tenants.guilds') }}</th>
              <th class="hidden md:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.tenants.members') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.tenants.status') }}</th>
              <th class="text-right px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.tenants.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-default">
            <tr
              v-for="tenant in tenants"
              :key="tenant.id"
              class="hover:bg-bg-tertiary/50 transition-colors"
            >
              <td class="px-4 py-2.5">
                <div class="text-text-primary font-medium">{{ tenant.name }}</div>
                <div class="text-xs text-text-muted">{{ tenant.slug }}</div>
              </td>
              <td class="hidden sm:table-cell px-4 py-2.5">
                <div class="flex items-center gap-2">
                  <div class="w-6 h-6 rounded-full bg-bg-tertiary border border-border-default flex items-center justify-center text-xs text-accent-gold font-bold uppercase">
                    {{ (tenant.owner_name || '?')[0] }}
                  </div>
                  <span class="text-text-primary text-sm">{{ tenant.owner_name || `#${tenant.owner_id}` }}</span>
                </div>
              </td>
              <td class="px-4 py-2.5">
                <button
                  type="button"
                  class="inline-block px-2 py-0.5 rounded-full text-xs font-medium cursor-pointer hover:opacity-80 transition-opacity"
                  :class="tenant.plan === 'free' ? 'bg-gray-700/50 text-gray-300 border border-gray-600' : 'bg-accent-gold/20 text-accent-gold border border-accent-gold/30'"
                  @click="openAssignModal(tenant)"
                >{{ tenant.plan }}</button>
              </td>
              <td class="hidden md:table-cell px-4 py-2.5 text-text-muted">{{ tenant.guild_count ?? 0 }} / {{ tenant.max_guilds }}</td>
              <td class="hidden md:table-cell px-4 py-2.5 text-text-muted">{{ tenant.member_count ?? 0 }}</td>
              <td class="px-4 py-2.5">
                <span
                  class="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
                  :class="tenant.is_active ? 'bg-green-900/50 text-green-300 border border-green-600' : 'bg-red-900/50 text-red-300 border border-red-600'"
                >{{ tenant.is_active ? t('admin.tenants.active') : t('admin.tenants.suspended') }}</span>
              </td>
              <td class="px-4 py-2.5 text-right">
                <div class="flex flex-wrap gap-1 justify-end">
                  <WowButton variant="secondary" class="!text-xs !py-1 !px-2" @click="showUsage(tenant)">{{ t('admin.tenants.usage') }}</WowButton>
                  <WowButton variant="secondary" class="!text-xs !py-1 !px-2" @click="showFeatures(tenant)">{{ t('admin.tenants.features') }}</WowButton>
                  <WowButton v-if="tenant.is_active" variant="secondary" class="!text-xs !py-1 !px-2" @click="doSuspend(tenant)">{{ t('admin.tenants.suspend') }}</WowButton>
                  <WowButton v-else variant="secondary" class="!text-xs !py-1 !px-2" @click="doActivate(tenant)">{{ t('admin.tenants.activate') }}</WowButton>
                  <WowButton variant="danger" class="!text-xs !py-1 !px-2" @click="doDelete(tenant)">{{ t('common.buttons.delete') }}</WowButton>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WowCard>

    <!-- Plan assignment modal -->
    <WowModal v-model="showAssignModal" :title="t('admin.tenants.assignPlan')" size="sm">
      <p class="text-sm text-text-muted mb-4">{{ assigningTenant?.name }}</p>
      <div v-if="loadingPlans" class="text-center py-4 text-text-muted">{{ t('common.labels.loading') }}</div>
      <div v-else class="space-y-3">
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('admin.tenants.selectPlan') }}</label>
          <select
            v-model="selectedPlanId"
            class="w-full px-3 py-2 rounded bg-bg-tertiary border border-border-default text-text-primary text-sm focus:border-border-gold focus:outline-none"
          >
            <option v-for="p in availablePlans" :key="p.id" :value="p.id">
              {{ p.name }} {{ p.is_free ? '(Free)' : '' }}
            </option>
          </select>
        </div>
        <div v-if="assignError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ assignError }}</div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showAssignModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton :loading="assignSaving" @click="doAssignPlan">{{ t('common.buttons.save') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Usage modal -->
    <WowModal v-model="showUsageModal" :title="t('admin.tenants.usageTitle')" size="sm">
      <p class="text-sm text-text-muted mb-4">{{ usageTenant?.name }}</p>
      <div v-if="loadingUsageData" class="text-center py-4 text-text-muted">{{ t('common.labels.loading') }}</div>
      <div v-else-if="usageData" class="space-y-3">
        <div v-for="res in ['guilds', 'members', 'events']" :key="res"
          class="flex items-center justify-between p-3 rounded-lg bg-bg-tertiary border border-border-default">
          <span class="text-sm text-text-muted capitalize">{{ t(`admin.tenants.${res}`) }}</span>
          <div class="text-right">
            <span class="text-text-primary font-medium">{{ usageData[res]?.current ?? 0 }}</span>
            <span class="text-text-muted"> / {{ usageData[res]?.max ?? '∞' }}</span>
            <span v-if="usageData[res]?.max && usageData[res]?.current >= usageData[res]?.max"
              class="ml-2 px-1.5 py-0.5 rounded text-xs bg-red-900/30 text-red-400">{{ t('admin.plans.limitReached') }}</span>
          </div>
        </div>
      </div>
    </WowModal>

    <!-- Features modal -->
    <WowModal v-model="showFeaturesModal" :title="t('admin.tenants.featuresTitle')" size="sm">
      <p class="text-sm text-text-muted mb-4">{{ featuresTenant?.name }}</p>
      <div v-if="loadingFeatures" class="text-center py-4 text-text-muted">{{ t('common.labels.loading') }}</div>
      <div v-else-if="tenantFeatures" class="space-y-2">
        <div v-for="(enabled, key) in tenantFeatures" :key="key"
          class="flex items-center justify-between p-3 rounded-lg bg-bg-tertiary border border-border-default">
          <span class="text-sm text-text-primary">{{ key }}</span>
          <button
            type="button"
            class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0"
            :class="enabled ? 'bg-accent-gold' : 'bg-bg-secondary border border-border-default'"
            @click="toggleTenantFeature(key)"
          >
            <span
              class="inline-block h-4 w-4 rounded-full bg-white transition-transform"
              :class="enabled ? 'translate-x-6' : 'translate-x-1'"
            />
          </button>
        </div>
        <p v-if="!Object.keys(tenantFeatures).length" class="text-sm text-text-muted text-center py-4">{{ t('admin.tenants.noFeatures') }}</p>
      </div>
    </WowModal>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import * as tenantsApi from '@/api/tenants'
import * as plansApi from '@/api/plans'
import * as adminApi from '@/api/admin'

const { t } = useI18n()
const tenants = ref([])
const loading = ref(false)

// Plan assignment
const assigningTenant = ref(null)
const showAssignModal = computed({
  get: () => !!assigningTenant.value,
  set: (v) => { if (!v) assigningTenant.value = null }
})
const availablePlans = ref([])
const selectedPlanId = ref(null)
const loadingPlans = ref(false)
const assignSaving = ref(false)
const assignError = ref('')

// Usage dashboard
const usageTenant = ref(null)
const showUsageModal = computed({
  get: () => !!usageTenant.value,
  set: (v) => { if (!v) usageTenant.value = null }
})
const usageData = ref(null)
const loadingUsageData = ref(false)

// Tenant features
const featuresTenant = ref(null)
const showFeaturesModal = computed({
  get: () => !!featuresTenant.value,
  set: (v) => { if (!v) featuresTenant.value = null }
})
const tenantFeatures = ref(null)
const loadingFeatures = ref(false)

async function fetchTenants() {
  loading.value = true
  try {
    tenants.value = await tenantsApi.adminListTenants()
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function openAssignModal(tenant) {
  assigningTenant.value = tenant
  assignError.value = ''
  loadingPlans.value = true
  try {
    availablePlans.value = await plansApi.listPlans()
    const current = availablePlans.value.find(p => p.slug === tenant.plan || p.name === tenant.plan)
    selectedPlanId.value = current ? current.id : (availablePlans.value[0]?.id ?? null)
  } catch {
    availablePlans.value = []
  } finally {
    loadingPlans.value = false
  }
}

async function doAssignPlan() {
  if (!selectedPlanId.value || !assigningTenant.value) return
  assignSaving.value = true
  assignError.value = ''
  try {
    await plansApi.assignPlanToTenant(assigningTenant.value.id, selectedPlanId.value)
    assigningTenant.value = null
    await fetchTenants()
  } catch (err) {
    assignError.value = err.response?.data?.error || err.response?.data?.message || t('common.labels.error')
  } finally {
    assignSaving.value = false
  }
}

async function showUsage(tenant) {
  usageTenant.value = tenant
  usageData.value = null
  loadingUsageData.value = true
  try {
    usageData.value = await plansApi.getTenantUsage(tenant.id)
  } catch {
    usageData.value = null
  } finally {
    loadingUsageData.value = false
  }
}

async function showFeatures(tenant) {
  featuresTenant.value = tenant
  tenantFeatures.value = null
  loadingFeatures.value = true
  try {
    tenantFeatures.value = await adminApi.getTenantFeatures(tenant.id)
  } catch {
    tenantFeatures.value = null
  } finally {
    loadingFeatures.value = false
  }
}

async function toggleTenantFeature(key) {
  if (!featuresTenant.value || !tenantFeatures.value) return
  const newVal = !tenantFeatures.value[key]
  try {
    tenantFeatures.value = await adminApi.updateTenantFeatures(featuresTenant.value.id, { [key]: newVal })
  } catch {
    // revert on error
    tenantFeatures.value[key] = !newVal
  }
}

async function doSuspend(tenant) {
  if (!confirm(t('admin.tenants.confirmSuspend', { name: tenant.name }))) return
  try {
    await tenantsApi.adminSuspendTenant(tenant.id)
    await fetchTenants()
  } catch {
    // ignore
  }
}

async function doActivate(tenant) {
  try {
    await tenantsApi.adminActivateTenant(tenant.id)
    await fetchTenants()
  } catch {
    // ignore
  }
}

async function doDelete(tenant) {
  if (!confirm(t('admin.tenants.confirmDelete', { name: tenant.name }))) return
  try {
    await tenantsApi.adminDeleteTenant(tenant.id)
    await fetchTenants()
  } catch {
    // ignore
  }
}

onMounted(fetchTenants)
</script>
