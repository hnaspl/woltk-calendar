<template>
  <AppShell>
    <div class="flex items-center justify-center min-h-[50vh]">
      <div class="w-full max-w-md p-6 bg-bg-secondary border border-border-default rounded-lg shadow-xl space-y-4">
        <h1 class="wow-heading text-xl text-center">{{ t('tenant.acceptInviteTitle') }}</h1>

        <div v-if="loading" class="text-center text-text-muted">{{ t('common.labels.loading') }}</div>

        <div v-else-if="accepted" class="text-center space-y-3">
          <div class="text-green-400 text-lg">✓ {{ t('tenant.inviteAccepted') }}</div>
          <p class="text-sm text-text-muted">{{ t('tenant.inviteAcceptedMsg') }}</p>
          <RouterLink to="/dashboard" class="inline-block px-4 py-2 text-sm bg-accent-gold/20 text-accent-gold border border-accent-gold/50 rounded hover:bg-accent-gold/30 transition-colors">
            {{ t('tenant.goToDashboard') }}
          </RouterLink>
        </div>

        <div v-else-if="errorMsg" class="text-center space-y-3">
          <div class="text-red-400">{{ errorMsg }}</div>
          <RouterLink to="/dashboard" class="inline-block px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors">
            {{ t('tenant.goToDashboard') }}
          </RouterLink>
        </div>

        <div v-else class="text-center space-y-3">
          <p class="text-sm text-text-muted">{{ t('tenant.acceptInviteMsg') }}</p>
          <button
            type="button"
            :disabled="accepting"
            class="px-6 py-2 text-sm bg-accent-gold/20 text-accent-gold border border-accent-gold/50 rounded hover:bg-accent-gold/30 transition-colors disabled:opacity-50"
            @click="doAccept"
          >{{ accepting ? t('common.labels.loading') : t('tenant.acceptInvite') }}</button>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppShell from '@/components/layout/AppShell.vue'
import { useTenantStore } from '@/stores/tenant'
import * as tenantsApi from '@/api/tenants'

const { t } = useI18n()
const route = useRoute()
const tenantStore = useTenantStore()

const loading = ref(false)
const accepting = ref(false)
const accepted = ref(false)
const errorMsg = ref(null)

async function doAccept() {
  const token = route.params.token
  if (!token) {
    errorMsg.value = t('tenant.invalidToken')
    return
  }
  accepting.value = true
  try {
    await tenantsApi.acceptInvite(token)
    accepted.value = true
    // Refresh tenant list
    await tenantStore.fetchTenants()
  } catch (err) {
    errorMsg.value = err?.response?.data?.message || t('tenant.inviteFailed')
  } finally {
    accepting.value = false
  }
}

onMounted(() => {
  // Auto-accept if there's a token
  if (route.params.token) {
    // Don't auto-accept, let user click the button
  }
})
</script>
