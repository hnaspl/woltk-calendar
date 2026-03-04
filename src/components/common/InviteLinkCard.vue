<template>
  <div class="p-3 rounded bg-bg-tertiary border border-border-default">
    <div class="flex items-center justify-between gap-2">
      <div class="min-w-0 flex-1">
        <div class="text-sm text-text-primary font-medium">
          {{ t('tenant.inviteBy', { name: invitation.inviter_username || '?' }) }}
          <span class="text-xs text-text-muted ml-1">({{ invitation.role }})</span>
        </div>
        <div class="text-xs text-text-muted mt-0.5">
          {{ t('tenant.uses') }}: {{ invitation.use_count }}{{ invitation.max_uses ? ` / ${invitation.max_uses}` : '' }}
          · {{ invitation.status }}
        </div>
        <code v-if="invitation.invite_token" class="text-[10px] text-text-muted mt-1 block break-all">
          {{ inviteUrl }}
        </code>
      </div>
      <div class="flex items-center gap-1.5 flex-shrink-0">
        <button
          v-if="invitation.invite_token"
          type="button"
          class="text-xs text-accent-gold hover:text-yellow-300 transition-colors"
          @click="doCopy"
        >{{ copied ? t('common.labels.copied') : t('common.buttons.copy') }}</button>
        <button
          v-if="invitation.status === 'pending'"
          type="button"
          class="text-xs text-red-400 hover:text-red-300 transition-colors"
          @click="$emit('revoke', invitation)"
        >{{ t('tenant.revoke') }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  invitation: { type: Object, required: true }
})

defineEmits(['revoke'])

const copied = ref(false)

const inviteUrl = computed(() => {
  if (!props.invitation.invite_token) return ''
  return `${window.location.origin}/invite/${props.invitation.invite_token}`
})

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
