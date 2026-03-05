<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-text-primary">{{ t('admin.tenants.title') }}</h2>
      <span class="text-sm text-text-muted">{{ tenants.length }} {{ t('admin.tenants.total') }}</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-8 text-text-muted">{{ t('common.labels.loading') }}</div>

    <!-- Tenants table -->
    <div v-else class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-text-muted border-b border-border-default">
            <th class="px-3 py-2">{{ t('admin.tenants.name') }}</th>
            <th class="px-3 py-2">{{ t('admin.tenants.owner') }}</th>
            <th class="px-3 py-2">{{ t('admin.tenants.plan') }}</th>
            <th class="px-3 py-2">{{ t('admin.tenants.guilds') }}</th>
            <th class="px-3 py-2">{{ t('admin.tenants.members') }}</th>
            <th class="px-3 py-2">{{ t('admin.tenants.status') }}</th>
            <th class="px-3 py-2">{{ t('admin.tenants.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="tenant in tenants"
            :key="tenant.id"
            class="border-b border-border-default hover:bg-bg-tertiary/30 transition-colors"
          >
            <td class="px-3 py-2">
              <div>
                <div class="text-text-primary font-medium">{{ tenant.name }}</div>
                <div class="text-xs text-text-muted">{{ tenant.slug }}</div>
              </div>
            </td>
            <td class="px-3 py-2">
              <div class="flex items-center gap-2">
                <div class="w-6 h-6 rounded-full bg-bg-tertiary border border-border-default flex items-center justify-center text-xs text-accent-gold font-bold uppercase">
                  {{ (tenant.owner_name || '?')[0] }}
                </div>
                <span class="text-text-primary text-sm">{{ tenant.owner_name || `#${tenant.owner_id}` }}</span>
              </div>
            </td>
            <td class="px-3 py-2">
              <button
                type="button"
                class="px-2 py-0.5 rounded text-xs font-medium cursor-pointer hover:opacity-80 transition-opacity"
                :class="tenant.plan === 'free' ? 'bg-gray-700 text-gray-300' : 'bg-accent-gold/20 text-accent-gold'"
                @click="openAssignModal(tenant)"
              >{{ tenant.plan }}</button>
            </td>
            <td class="px-3 py-2 text-text-muted">{{ tenant.guild_count ?? 0 }} / {{ tenant.max_guilds }}</td>
            <td class="px-3 py-2 text-text-muted">{{ tenant.member_count ?? 0 }}</td>
            <td class="px-3 py-2">
              <span
                class="px-2 py-0.5 rounded text-xs font-medium"
                :class="tenant.is_active ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'"
              >{{ tenant.is_active ? t('admin.tenants.active') : t('admin.tenants.suspended') }}</span>
            </td>
            <td class="px-3 py-2">
              <div class="flex gap-1.5">
                <button
                  type="button"
                  class="px-2 py-1 rounded text-xs font-medium bg-blue-900/30 text-blue-400 border border-blue-700/50 hover:bg-blue-900/50 transition-colors"
                  @click="showUsage(tenant)"
                >{{ t('admin.tenants.usage') }}</button>
                <button
                  type="button"
                  class="px-2 py-1 rounded text-xs font-medium bg-purple-900/30 text-purple-400 border border-purple-700/50 hover:bg-purple-900/50 transition-colors"
                  @click="showFeatures(tenant)"
                >{{ t('admin.tenants.features') }}</button>
                <button
                  v-if="tenant.is_active"
                  type="button"
                  class="px-2 py-1 rounded text-xs font-medium bg-yellow-900/30 text-yellow-400 border border-yellow-700/50 hover:bg-yellow-900/50 transition-colors"
                  @click="doSuspend(tenant)"
                >{{ t('admin.tenants.suspend') }}</button>
                <button
                  v-else
                  type="button"
                  class="px-2 py-1 rounded text-xs font-medium bg-green-900/30 text-green-400 border border-green-700/50 hover:bg-green-900/50 transition-colors"
                  @click="doActivate(tenant)"
                >{{ t('admin.tenants.activate') }}</button>
                <button
                  type="button"
                  class="px-2 py-1 rounded text-xs font-medium bg-red-900/30 text-red-400 border border-red-700/50 hover:bg-red-900/50 transition-colors"
                  @click="doDelete(tenant)"
                >{{ t('common.buttons.delete') }}</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Plan assignment modal -->
    <div v-if="assigningTenant" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div class="bg-bg-secondary border border-border-default rounded-lg shadow-xl w-full max-w-sm">
        <div class="p-4 border-b border-border-default">
          <h3 class="text-lg font-semibold text-text-primary">{{ t('admin.tenants.assignPlan') }}</h3>
          <p class="text-sm text-text-muted mt-1">{{ assigningTenant.name }}</p>
        </div>
        <div class="p-4 space-y-3">
          <div v-if="loadingPlans" class="text-center py-4 text-text-muted">{{ t('common.labels.loading') }}</div>
          <div v-else>
            <label class="block text-sm font-medium text-text-muted mb-1">{{ t('admin.tenants.selectPlan') }}</label>
            <select
              v-model="selectedPlanId"
              class="w-full px-3 py-2 rounded-lg bg-bg-primary border border-border-default text-text-primary text-sm focus:border-accent-gold focus:outline-none"
            >
              <option v-for="p in availablePlans" :key="p.id" :value="p.id">
                {{ p.name }} {{ p.is_free ? '(Free)' : '' }}
              </option>
            </select>
          </div>
          <div v-if="assignError" class="text-sm text-red-400">{{ assignError }}</div>
          <div class="flex justify-end gap-2 pt-2">
            <button type="button" class="px-3 py-1.5 rounded-lg text-sm text-text-muted hover:text-text-primary"
              @click="assigningTenant = null">{{ t('common.buttons.cancel') }}</button>
            <button type="button" class="px-3 py-1.5 rounded-lg bg-accent-gold/20 text-accent-gold text-sm font-medium hover:bg-accent-gold/30"
              :disabled="assignSaving" @click="doAssignPlan">{{ t('common.buttons.save') }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Usage modal -->
    <div v-if="usageTenant" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div class="bg-bg-secondary border border-border-default rounded-lg shadow-xl w-full max-w-md">
        <div class="p-4 border-b border-border-default flex items-center justify-between">
          <div>
            <h3 class="text-lg font-semibold text-text-primary">{{ t('admin.tenants.usageTitle') }}</h3>
            <p class="text-sm text-text-muted mt-0.5">{{ usageTenant.name }}</p>
          </div>
          <button type="button" class="text-text-muted hover:text-text-primary" @click="usageTenant = null">✕</button>
        </div>
        <div class="p-4">
          <div v-if="loadingUsageData" class="text-center py-4 text-text-muted">{{ t('common.labels.loading') }}</div>
          <div v-else-if="usageData" class="space-y-3">
            <div v-for="res in ['guilds', 'members', 'events']" :key="res"
              class="flex items-center justify-between p-3 rounded-lg bg-bg-primary border border-border-default">
              <span class="text-sm text-text-muted capitalize">{{ t(`admin.tenants.${res}`) }}</span>
              <div class="text-right">
                <span class="text-text-primary font-medium">{{ usageData[res]?.current ?? 0 }}</span>
                <span class="text-text-muted"> / {{ usageData[res]?.max ?? '∞' }}</span>
                <span v-if="usageData[res]?.max && usageData[res]?.current >= usageData[res]?.max"
                  class="ml-2 px-1.5 py-0.5 rounded text-xs bg-red-900/30 text-red-400">{{ t('admin.plans.limitReached') }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- Features modal -->
    <div v-if="featuresTenant" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div class="bg-bg-secondary border border-border-default rounded-lg shadow-xl w-full max-w-md">
        <div class="p-4 border-b border-border-default flex items-center justify-between">
          <div>
            <h3 class="text-lg font-semibold text-text-primary">{{ t('admin.tenants.featuresTitle') }}</h3>
            <p class="text-sm text-text-muted mt-0.5">{{ featuresTenant.name }}</p>
          </div>
          <button type="button" class="text-text-muted hover:text-text-primary" @click="featuresTenant = null">✕</button>
        </div>
        <div class="p-4">
          <div v-if="loadingFeatures" class="text-center py-4 text-text-muted">{{ t('common.labels.loading') }}</div>
          <div v-else-if="tenantFeatures" class="space-y-2">
            <div v-for="(enabled, key) in tenantFeatures" :key="key"
              class="flex items-center justify-between p-3 rounded-lg bg-bg-primary border border-border-default">
              <span class="text-sm text-text-primary">{{ key }}</span>
              <button
                type="button"
                class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0"
                :class="enabled ? 'bg-accent-gold' : 'bg-bg-tertiary border border-border-default'"
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
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import * as tenantsApi from '@/api/tenants'
import * as plansApi from '@/api/plans'
import * as adminApi from '@/api/admin'

const { t } = useI18n()
const tenants = ref([])
const loading = ref(false)

// Plan assignment
const assigningTenant = ref(null)
const availablePlans = ref([])
const selectedPlanId = ref(null)
const loadingPlans = ref(false)
const assignSaving = ref(false)
const assignError = ref('')

// Usage dashboard
const usageTenant = ref(null)
const usageData = ref(null)
const loadingUsageData = ref(false)

// Tenant features
const featuresTenant = ref(null)
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
