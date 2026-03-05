<template>
  <div class="p-3 sm:p-4 rounded-lg bg-bg-tertiary border border-border-default hover:border-border-default/80 transition-colors">
    <div class="flex flex-col sm:flex-row sm:items-center gap-3">
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-sm text-text-primary font-medium">{{ t('tenant.inviteBy', { name: invitation.inviter_username || '?' }) }}</span>
          <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wide"
            :class="invitation.role === 'admin' ? 'bg-accent-gold/20 text-accent-gold border border-accent-gold/30' : 'bg-bg-secondary text-text-muted border border-border-default'"
          >{{ invitation.role === 'admin' ? t('tenant.roleAdmin') : t('tenant.roleMember') }}</span>
          <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium"
            :class="statusClass"
          >{{ statusLabel }}</span>
        </div>
        <div class="flex items-center gap-3 mt-1.5 text-xs text-text-muted">
          <span class="flex items-center gap-1">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            {{ t('tenant.uses') }}: {{ invitation.use_count }}{{ invitation.max_uses ? ` / ${invitation.max_uses}` : ` / ${t('tenant.unlimited')}` }}
          </span>
          <span v-if="invitation.expires_at" class="flex items-center gap-1">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {{ t('tenant.expiresIn') }}: {{ formatExpiry(invitation.expires_at) }}
          </span>
        </div>
        <div v-if="invitation.invite_token" class="mt-2">
          <code class="text-[11px] text-text-muted/70 break-all bg-bg-secondary rounded px-2 py-1 border border-border-default inline-block max-w-full">{{ inviteUrl }}</code>
        </div>
      </div>
      <div class="flex items-center gap-2 flex-shrink-0">
        <WowButton
          v-if="invitation.invite_token"
          variant="secondary"
          class="text-xs py-1 px-3"
          @click="doCopy"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          {{ copied ? t('common.labels.copied') : t('tenant.copyLink') }}
        </WowButton>
        <WowButton
          v-if="invitation.status === 'pending'"
          variant="danger"
          class="text-xs py-1 px-3"
          @click="$emit('revoke', invitation)"
        >{{ t('tenant.revoke') }}</WowButton>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import WowButton from '@/components/common/WowButton.vue'

const { t } = useI18n()

const props = defineProps({
  invitation: { type: Object, required: true },
  linkBase: { type: String, default: '' }
})

defineEmits(['revoke'])

const copied = ref(false)

const inviteUrl = computed(() => {
  if (!props.invitation.invite_token) return ''
  if (props.linkBase) return `${props.linkBase}${props.invitation.invite_token}`
  return `${window.location.origin}/invite/${props.invitation.invite_token}`
})

const statusClass = computed(() => {
  switch (props.invitation.status) {
    case 'pending': return 'bg-yellow-900/30 text-yellow-300 border border-yellow-700/50'
    case 'accepted': return 'bg-green-900/30 text-green-300 border border-green-700/50'
    case 'expired': return 'bg-red-900/30 text-red-300 border border-red-700/50'
    case 'revoked': return 'bg-red-900/30 text-red-400 border border-red-700/50'
    default: return 'bg-bg-secondary text-text-muted border border-border-default'
  }
})

const statusLabel = computed(() => {
  switch (props.invitation.status) {
    case 'pending': return t('tenant.pending')
    case 'accepted': return t('tenant.accepted')
    case 'expired': return t('tenant.expired')
    case 'revoked': return t('tenant.revoked')
    default: return props.invitation.status
  }
})

function formatExpiry(dateStr) {
  if (!dateStr) return t('tenant.never')
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = d - now
  if (diffMs <= 0) return t('tenant.expired')
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  if (days > 0) return `${days}d ${hours}h`
  return `${hours}h`
}

async function doCopy() {
  if (!inviteUrl.value) return
  try {
    await navigator.clipboard.writeText(inviteUrl.value)
  } catch {
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
</script>
