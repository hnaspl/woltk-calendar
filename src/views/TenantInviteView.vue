<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-6 w-full max-w-3xl mx-auto">
      <h1 class="wow-heading text-xl sm:text-2xl">{{ t('tenant.invitesTitle') }}</h1>

      <!-- Create invitation -->
      <WowCard>
        <h2 class="text-sm font-semibold text-text-primary mb-4">{{ t('tenant.createInvite') }}</h2>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('tenant.inviteRole') }}</label>
            <select v-model="newInvite.role" class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-border-gold outline-none">
              <option value="member">{{ t('tenant.roleMember') }}</option>
              <option value="admin">{{ t('tenant.roleAdmin') }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('tenant.maxUses') }}</label>
            <input v-model.number="newInvite.max_uses" type="number" min="1" placeholder="∞" class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('tenant.expiresInDays') }}</label>
            <input v-model.number="newInvite.expires_in_days" type="number" min="1" max="30" class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2 focus:border-border-gold outline-none" />
          </div>
        </div>
        <WowButton :loading="creating" @click="doCreate">
          {{ t('tenant.generateLink') }}
        </WowButton>

        <!-- Show generated link -->
        <div v-if="generatedToken" class="mt-4 p-3 sm:p-4 rounded-lg bg-green-900/20 border border-green-700">
          <p class="text-xs text-text-muted mb-2">{{ t('tenant.inviteLink') }}</p>
          <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <code class="text-sm text-green-300 break-all flex-1 bg-bg-tertiary rounded px-3 py-2 select-all">{{ inviteUrl }}</code>
            <WowButton variant="secondary" class="flex-shrink-0" @click="copyLink">
              {{ copied ? t('common.labels.copied') : t('tenant.copyLink') }}
            </WowButton>
          </div>
          <p v-if="copied" class="text-xs text-green-400 mt-1">{{ t('tenant.linkCopied') }}</p>
        </div>
      </WowCard>

      <!-- Existing invitations -->
      <WowCard>
        <h2 class="text-sm font-semibold text-text-primary mb-4">{{ t('tenant.existingInvites') }}</h2>
        <div v-if="loading" class="text-sm text-text-muted py-4 text-center">{{ t('common.labels.loading') }}</div>
        <div v-else-if="!invitations.length" class="text-sm text-text-muted py-4 text-center">{{ t('tenant.noInvites') }}</div>
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
import { useUiStore } from '@/stores/ui'
import * as tenantsApi from '@/api/tenants'

const { t } = useI18n()
const tenantStore = useTenantStore()
const uiStore = useUiStore()

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
    uiStore.showToast(t('tenant.inviteRevoked'), 'success')
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
