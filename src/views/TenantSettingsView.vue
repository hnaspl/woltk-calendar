<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-6 w-full max-w-3xl mx-auto">
      <!-- Header -->
      <div class="flex items-center gap-3">
        <RouterLink to="/dashboard" class="p-1.5 rounded-lg bg-bg-tertiary border border-border-default text-text-muted hover:text-accent-gold hover:border-border-gold transition-colors">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </RouterLink>
        <div class="flex-1">
          <h1 class="wow-heading text-xl sm:text-2xl">{{ t('tenant.settingsTitle') }}</h1>
          <p class="text-xs text-text-muted mt-0.5">{{ t('tenant.settingsSubtitle') }}</p>
        </div>
        <!-- Link to invitations -->
        <RouterLink
          to="/tenant/invites"
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-text-muted bg-bg-tertiary border border-border-default rounded hover:border-border-gold hover:text-accent-gold transition-colors"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          {{ t('tenant.invites') }}
        </RouterLink>
      </div>

      <div v-if="loading" class="py-8 text-center">
        <div class="w-6 h-6 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin mx-auto mb-2" />
        <p class="text-sm text-text-muted">{{ t('common.labels.loading') }}</p>
      </div>

      <template v-else-if="tenant">
        <!-- Plan & Usage dashboard -->
        <WowCard>
          <div class="flex items-center gap-2 mb-4">
            <svg class="w-5 h-5 text-accent-gold flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <h2 class="text-sm font-semibold text-text-primary">{{ t('tenant.plan') }} &amp; {{ t('admin.tenants.usage') }}</h2>
          </div>
          <div v-if="usageLoading" class="py-4 text-center">
            <div class="w-5 h-5 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin mx-auto" />
          </div>
          <div v-else class="space-y-3">
            <div v-for="res in ['guilds', 'members', 'events']" :key="res"
              class="flex items-center justify-between p-3 rounded-lg bg-bg-tertiary border border-border-default"
            >
              <span class="text-sm text-text-muted capitalize">{{ t(`admin.tenants.${res}`) }}</span>
              <div class="flex items-center gap-2">
                <span class="text-text-primary font-medium">{{ usageInfo(res) }}</span>
                <span v-if="shouldShowUpgrade(res)"
                  class="px-1.5 py-0.5 rounded text-xs bg-red-900/30 text-red-400">{{ t('admin.plans.limitReached') }}</span>
              </div>
            </div>
            <p v-if="shouldShowUpgrade('guilds') || shouldShowUpgrade('members') || shouldShowUpgrade('events')"
              class="text-xs text-yellow-500/80 mt-2">{{ t('admin.plans.upgradePrompt') }}</p>
          </div>
        </WowCard>

        <!-- Settings form -->
        <WowCard>
          <div class="flex items-center gap-2 mb-4">
            <svg class="w-5 h-5 text-accent-gold flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <h2 class="text-sm font-semibold text-text-primary">{{ t('tenant.workspaceInfo') }}</h2>
          </div>
          <form @submit.prevent="doSave" class="space-y-4">
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('tenant.name') }}</label>
              <input v-model="form.name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('tenant.description') }}</label>
              <textarea v-model="form.description" rows="3" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none resize-none" />
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('tenant.slug') }}</label>
              <input v-model="form.slug" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
              <p class="text-xs text-text-muted mt-1">{{ t('tenant.slugHelp') }}</p>
            </div>

            <div class="flex items-center gap-3 pt-2">
              <WowButton type="submit" :loading="saving">
                {{ t('common.buttons.save') }}
              </WowButton>
              <span v-if="saved" class="text-sm text-green-400">✓ {{ t('common.labels.saved') }}</span>
              <span v-if="saveError" class="text-sm text-red-400">{{ saveError }}</span>
            </div>
          </form>
        </WowCard>

        <!-- Members section -->
        <WowCard>
          <div class="flex items-center gap-2 mb-4">
            <svg class="w-5 h-5 text-accent-gold flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <h2 class="text-sm font-semibold text-text-primary">{{ t('tenant.membersTitle') }}</h2>
            <span v-if="members.length" class="ml-auto text-xs text-text-muted bg-bg-tertiary border border-border-default rounded-full px-2 py-0.5">{{ members.length }}</span>
          </div>
          <div v-if="membersLoading" class="py-4 text-center">
            <div class="w-5 h-5 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin mx-auto" />
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="m in members"
              :key="m.id"
              class="flex items-center justify-between gap-3 p-3 rounded-lg bg-bg-tertiary border border-border-default"
            >
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-full bg-bg-secondary border border-border-default flex items-center justify-center text-xs text-accent-gold font-bold uppercase">
                  {{ (m.display_name || m.username || '?')[0] }}
                </div>
                <div>
                  <span class="text-sm text-text-primary font-medium">{{ m.display_name || m.username }}</span>
                  <span class="inline-flex items-center ml-2 px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wide"
                    :class="m.role === 'owner' ? 'bg-accent-gold/20 text-accent-gold border border-accent-gold/30' : m.role === 'admin' ? 'bg-blue-900/30 text-blue-300 border border-blue-700/50' : 'bg-bg-secondary text-text-muted border border-border-default'"
                  >{{ m.role }}</span>
                </div>
              </div>
              <WowButton
                v-if="m.role !== 'owner'"
                variant="danger"
                class="text-xs py-1 px-3"
                @click="doRemoveMember(m)"
              >{{ t('common.buttons.remove') }}</WowButton>
            </div>
          </div>
        </WowCard>
      </template>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import { useTenantStore } from '@/stores/tenant'
import { usePlanLimits } from '@/composables/usePlanLimits'
import * as tenantsApi from '@/api/tenants'

const { t } = useI18n()
const tenantStore = useTenantStore()
const { fetchUsage, usageInfo, shouldShowUpgrade, loadingUsage: usageLoading } = usePlanLimits()

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
  if (tenantStore.activeTenantId) {
    fetchUsage(tenantStore.activeTenantId)
  }
})
</script>
