<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6">
      <!-- Header -->
      <div>
        <h1 class="wow-heading text-xl sm:text-2xl">{{ t('tenant.invitesTitle') }}</h1>
        <p class="text-xs text-text-muted mt-0.5">{{ t('tenant.invitesSubtitle') }}</p>
      </div>

      <!-- Create invitation -->
      <WowCard>
        <div class="flex items-center gap-2 mb-4">
          <svg class="w-5 h-5 text-accent-gold flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          <h2 class="text-sm font-semibold text-text-primary">{{ t('tenant.createInvite') }}</h2>
        </div>
        <p class="text-xs text-text-muted mb-4">{{ t('tenant.createInviteHelp') }}</p>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('tenant.inviteRole') }}</label>
            <select v-model="newInvite.role" class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-border-gold outline-none">
              <option value="member">{{ t('tenant.roleMember') }}</option>
              <option value="admin">{{ t('tenant.roleAdmin') }}</option>
            </select>
            <p class="text-[10px] text-text-muted mt-1">{{ newInvite.role === 'admin' ? t('tenant.roleAdminHelp') : t('tenant.roleMemberHelp') }}</p>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('tenant.maxUses') }}</label>
            <input v-model.number="newInvite.max_uses" type="number" min="1" :placeholder="t('tenant.unlimited')" class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('tenant.expiresInDays') }}</label>
            <input v-model.number="newInvite.expires_in_days" type="number" min="1" max="30" class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-border-gold outline-none" />
          </div>
        </div>
        <WowButton :loading="creating" @click="doCreate">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          {{ t('tenant.generateLink') }}
        </WowButton>

        <!-- Show generated link -->
        <div v-if="generatedToken" class="mt-4 p-4 rounded-lg bg-green-900/20 border border-green-700/50">
          <div class="flex items-center gap-2 mb-2">
            <svg class="w-4 h-4 text-green-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-sm text-green-300 font-medium">{{ t('tenant.linkGenerated') }}</p>
          </div>
          <p class="text-xs text-text-muted mb-3">{{ t('tenant.linkGeneratedHelp') }}</p>
          <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <code class="text-sm text-green-300 break-all flex-1 bg-bg-tertiary rounded px-3 py-2 select-all border border-border-default">{{ inviteUrl }}</code>
            <WowButton variant="secondary" class="flex-shrink-0" @click="copyLink">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              {{ copied ? t('common.labels.copied') : t('tenant.copyLink') }}
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
          <h2 class="text-sm font-semibold text-text-primary">{{ t('tenant.existingInvites') }}</h2>
          <span v-if="invitations.length" class="ml-auto text-xs text-text-muted bg-bg-tertiary border border-border-default rounded-full px-2 py-0.5">{{ invitations.length }}</span>
        </div>
        <div v-if="loading" class="py-8 text-center">
          <div class="w-6 h-6 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin mx-auto mb-2" />
          <p class="text-sm text-text-muted">{{ t('common.labels.loading') }}</p>
        </div>
        <div v-else-if="!invitations.length" class="py-8 text-center">
          <svg class="w-10 h-10 text-text-muted/30 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          <p class="text-sm text-text-muted">{{ t('tenant.noInvites') }}</p>
          <p class="text-xs text-text-muted/60 mt-1">{{ t('tenant.noInvitesHelp') }}</p>
        </div>
        <div v-else class="space-y-2">
          <InviteLinkCard
            v-for="inv in invitations"
            :key="inv.id"
            :invitation="inv"
            @revoke="doRevoke"
          />
        </div>
      </WowCard>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import InviteLinkCard from '@/components/common/InviteLinkCard.vue'
import { useTenantStore } from '@/stores/tenant'
import { useToast } from '@/composables/useToast'
import * as tenantsApi from '@/api/tenants'

const { t } = useI18n()
const tenantStore = useTenantStore()
const toast = useToast()

const invitations = ref([])
const loading = ref(false)
const creating = ref(false)
const generatedToken = ref(null)
const copied = ref(false)

const newInvite = ref({
  role: 'member',
  max_uses: null,
  expires_in_days: 7,
})

const inviteUrl = computed(() => {
  if (!generatedToken.value) return ''
  return `${window.location.origin}/invite/${generatedToken.value}`
})

async function fetchInvitations() {
  if (!tenantStore.activeTenantId) return
  loading.value = true
  try {
    invitations.value = await tenantsApi.getTenantInvitations(tenantStore.activeTenantId)
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function doCreate() {
  creating.value = true
  generatedToken.value = null
  try {
    const inv = await tenantsApi.createTenantInvitation(tenantStore.activeTenantId, {
      role: newInvite.value.role,
      max_uses: newInvite.value.max_uses || null,
      expires_in_days: newInvite.value.expires_in_days || 7,
    })
    generatedToken.value = inv.invite_token
    await fetchInvitations()
  } catch {
    // ignore
  } finally {
    creating.value = false
  }
}

async function doRevoke(inv) {
  if (!confirm(t('tenant.confirmRevoke'))) return
  try {
    await tenantsApi.revokeTenantInvitation(tenantStore.activeTenantId, inv.id)
    await fetchInvitations()
    toast.success(t('tenant.inviteRevoked'))
  } catch {
    // ignore
  }
}

async function copyLink() {
  if (!inviteUrl.value) return
  try {
    await navigator.clipboard.writeText(inviteUrl.value)
  } catch {
    // Fallback for older browsers / non-HTTPS
    const ta = document.createElement('textarea')
    ta.value = inviteUrl.value
    ta.style.position = 'fixed'
    ta.style.left = '-9999px'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

onMounted(fetchInvitations)
</script>
