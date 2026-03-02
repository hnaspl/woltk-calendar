<template>
  <WowModal :modelValue="modelValue" @update:modelValue="emit('update:modelValue', $event)" :title="t('common.labels.recordAttendance')" size="lg">
    <div class="space-y-4">
      <p class="text-text-muted text-sm">
        {{ t('attendance.modal.description') }}
      </p>

      <div v-if="players.length === 0" class="py-8 text-center text-text-muted">
        {{ t('attendance.modal.noSignups') }}
      </div>

      <div v-else class="overflow-x-auto max-h-[55vh] overflow-y-auto">
        <table class="w-full text-sm">
          <thead class="sticky top-0 z-10">
            <tr class="bg-bg-tertiary border-b border-border-default">
              <th class="text-left px-3 py-2 text-xs text-text-muted uppercase">{{ t('common.fields.character') }}</th>
              <th class="text-left px-3 py-2 text-xs text-text-muted uppercase hidden sm:table-cell">{{ t('common.labels.class') }}</th>
              <th class="text-left px-3 py-2 text-xs text-text-muted uppercase hidden sm:table-cell">{{ t('common.fields.role') }}</th>
              <th class="text-left px-3 py-2 text-xs text-text-muted uppercase">{{ t('attendance.modal.outcome') }}</th>
              <th class="text-left px-3 py-2 text-xs text-text-muted uppercase">{{ t('common.fields.note') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-default">
            <tr v-for="p in players" :key="p.signup.id" class="hover:bg-bg-tertiary/50">
              <td class="px-3 py-2 font-medium" :style="{ color: getClassColor(p.signup.character?.class_name) }">
                {{ p.signup.character?.name ?? '?' }}
              </td>
              <td class="px-3 py-2 text-text-muted text-xs hidden sm:table-cell">{{ p.signup.character?.class_name ?? '—' }}</td>
              <td class="px-3 py-2 text-text-muted text-xs hidden sm:table-cell">{{ roleLabel(p.signup.chosen_role) }}</td>
              <td class="px-3 py-2">
                <select
                  v-model="p.outcome"
                  class="bg-bg-tertiary border border-border-default text-text-primary text-xs rounded px-2 py-1 focus:border-border-gold outline-none"
                >
                  <option value="attended">{{ t('attendance.attended') }}</option>
                  <option value="late">{{ t('attendance.late') }}</option>
                  <option value="no_show">{{ t('attendance.unattended') }}</option>
                </select>
              </td>
              <td class="px-3 py-2">
                <input
                  v-model="p.note"
                  :placeholder="t('common.labels.optionalNote')"
                  class="w-full bg-bg-tertiary border border-border-default text-text-primary text-xs rounded px-2 py-1 focus:border-border-gold outline-none"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="saveError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ saveError }}</div>
    </div>

    <template #footer>
      <div class="flex items-center justify-between">
        <span v-if="saveProgress" class="text-xs text-text-muted">{{ saveProgress }}</span>
        <span v-else />
        <div class="flex gap-3">
          <WowButton variant="secondary" @click="emit('update:modelValue', false)">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton :loading="saving" :disabled="players.length === 0" @click="saveAttendance">{{ t('attendance.modal.saveAttendance') }}</WowButton>
        </div>
      </div>
    </template>
  </WowModal>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import WowModal from '@/components/common/WowModal.vue'
import WowButton from '@/components/common/WowButton.vue'
import { useWowIcons } from '@/composables/useWowIcons'
import { useUiStore } from '@/stores/ui'
import * as attendanceApi from '@/api/attendance'
import { ROLE_LABEL_MAP } from '@/constants'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  signups: { type: Array, default: () => [] },
  guildId: { type: [Number, String], required: true },
  eventId: { type: [Number, String], required: true }
})

const emit = defineEmits(['update:modelValue', 'saved'])

const { t } = useI18n()
const { getClassColor } = useWowIcons()
const uiStore = useUiStore()

function roleLabel(role) { return ROLE_LABEL_MAP[role] || role }

const players = ref([])
const saving = ref(false)
const saveError = ref(null)
const saveProgress = ref('')

// Build player list when modal opens or signups change
watch(
  () => [props.modelValue, props.signups],
  () => {
    if (!props.modelValue) return
    // Only include players who are in the lineup (not bench or declined)
    players.value = props.signups
      .filter(s => s.lineup_status === 'going')
      .map(s => ({
        signup: s,
        outcome: 'attended',
        note: ''
      }))
  },
  { immediate: true }
)

async function saveAttendance() {
  saving.value = true
  saveError.value = null
  saveProgress.value = ''
  let saved = 0
  const total = players.value.length

  try {
    for (const p of players.value) {
      await attendanceApi.recordAttendance(props.guildId, props.eventId, {
        user_id: p.signup.user_id,
        character_id: p.signup.character_id,
        outcome: p.outcome,
        note: p.note || undefined
      })
      saved++
      saveProgress.value = `${saved} / ${total} saved…`
    }
    uiStore.showToast(t('attendance.modal.recorded'), 'success')
    emit('saved')
    emit('update:modelValue', false)
  } catch (err) {
    saveError.value = err?.response?.data?.message ?? `Failed to save attendance (${saved}/${total} completed)`
  } finally {
    saving.value = false
    saveProgress.value = ''
  }
}
</script>
