<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-6 max-w-2xl">
      <h1 class="wow-heading text-xl sm:text-2xl">{{ t('tenant.invitesTitle') }}</h1>

      <!-- Create invitation -->
      <div class="p-4 rounded-lg bg-bg-secondary border border-border-default space-y-4">
        <h2 class="text-sm font-semibold text-text-primary">{{ t('tenant.createInvite') }}</h2>
        <div class="flex flex-wrap gap-3 items-end">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('tenant.inviteRole') }}</label>
            <select v-model="newInvite.role" class="bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-2 py-1.5 focus:border-border-gold outline-none">
              <option value="member">{{ t('tenant.roleMember') }}</option>
              <option value="admin">{{ t('tenant.roleAdmin') }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('tenant.maxUses') }}</label>
            <input v-model.number="newInvite.max_uses" type="number" min="1" placeholder="∞" class="w-20 bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-2 py-1.5 focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('tenant.expiresInDays') }}</label>
            <input v-model.number="newInvite.expires_in_days" type="number" min="1" max="30" class="w-20 bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-2 py-1.5 focus:border-border-gold outline-none" />
          </div>
          <button
            type="button"
            :disabled="creating"
            class="px-4 py-1.5 text-sm bg-accent-gold/20 text-accent-gold border border-accent-gold/50 rounded hover:bg-accent-gold/30 transition-colors disabled:opacity-50"
            @click="doCreate"
          >{{ creating ? t('common.labels.creating') : t('tenant.generateLink') }}</button>
        </div>
        <!-- Show generated link -->
        <div v-if="generatedToken" class="p-3 rounded bg-green-900/20 border border-green-700">
          <p class="text-xs text-text-muted mb-1">{{ t('tenant.inviteLink') }}</p>
          <div class="flex items-center gap-2">
            <code class="text-sm text-green-300 break-all flex-1">{{ inviteUrl }}</code>
            <button
              type="button"
              class="text-xs text-accent-gold hover:text-yellow-300 transition-colors whitespace-nowrap"
              @click="copyLink"
            >{{ copied ? t('common.labels.copied') : t('common.buttons.copy') }}</button>
          </div>
        </div>
      </div>

      <!-- Existing invitations -->
      <div class="space-y-3">
        <h2 class="text-lg font-semibold text-text-primary">{{ t('tenant.existingInvites') }}</h2>
        <div v-if="loading" class="text-sm text-text-muted">{{ t('common.labels.loading') }}</div>
        <div v-else-if="!invitations.length" class="text-sm text-text-muted">{{ t('tenant.noInvites') }}</div>
        <div v-else class="space-y-2">
          <div
            v-for="inv in invitations"
            :key="inv.id"
            class="flex items-center justify-between gap-3 p-3 rounded bg-bg-tertiary border border-border-default"
          >
            <div class="flex-1 min-w-0">
              <div class="text-sm text-text-primary">
                {{ t('tenant.inviteBy', { name: inv.inviter_username || '?' }) }}
                <span class="text-xs text-text-muted ml-1">({{ inv.role }})</span>
              </div>
              <div class="text-xs text-text-muted">
                {{ t('tenant.uses') }}: {{ inv.use_count }}{{ inv.max_uses ? ` / ${inv.max_uses}` : '' }}
                · {{ inv.status }}
              </div>
            </div>
            <button
              v-if="inv.status === 'pending'"
              type="button"
              class="text-xs text-red-400 hover:text-red-300 transition-colors"
              @click="doRevoke(inv)"
            >{{ t('tenant.revoke') }}</button>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import AppShell from '@/components/layout/AppShell.vue'
import { useTenantStore } from '@/stores/tenant'
import * as tenantsApi from '@/api/tenants'

const { t } = useI18n()
const tenantStore = useTenantStore()

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
  } catch {
    // ignore
  }
}

function copyLink() {
  if (inviteUrl.value) {
    navigator.clipboard.writeText(inviteUrl.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  }
}

onMounted(fetchInvitations)
</script>
