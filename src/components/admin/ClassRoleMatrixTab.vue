<template>
  <div class="space-y-6">
    <!-- Header with reset all button -->
    <WowCard>
      <div class="flex items-center justify-between gap-2 mb-4">
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-accent-gold flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
          </svg>
          <div>
            <h2 class="text-sm font-semibold text-text-primary">{{ t('guild.matrixTitle') }}</h2>
            <p class="text-xs text-text-muted mt-0.5">{{ t('guild.matrixSubtitle') }}</p>
          </div>
        </div>
        <WowButton v-if="hasOverrides" variant="danger" @click="doResetAll" :loading="resettingAll" class="text-xs">
          {{ t('guild.matrixResetAll') }}
        </WowButton>
      </div>

      <div v-if="loading" class="py-4 text-center">
        <div class="w-5 h-5 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin mx-auto" />
      </div>

      <div v-else-if="!matrix || !sortedClasses.length" class="py-6 text-center">
        <p class="text-sm text-text-muted">{{ t('guild.matrixNoData') }}</p>
        <p class="text-xs text-text-muted mt-1">{{ t('guild.matrixNoDataHelp') }}</p>
      </div>

      <!-- Grid matrix -->
      <div v-else class="overflow-x-auto">
        <table class="w-full border-collapse text-sm">
          <thead>
            <tr>
              <th class="text-left p-2 text-xs text-text-muted font-medium border-b border-border-default w-44">{{ t('guild.matrixClass') }}</th>
              <th v-for="role in allRoles" :key="role" class="p-2 text-center text-xs font-medium border-b border-border-default"
                :class="roleHeaderClass(role)">
                {{ roleLabels[role] || role }}
              </th>
              <th class="p-2 text-center text-xs text-text-muted font-medium border-b border-border-default w-24">{{ t('guild.matrixActions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="className in sortedClasses" :key="className"
              class="border-b border-border-default/50 hover:bg-bg-tertiary/50 transition-colors"
              :class="isCustomized(className) ? 'bg-accent-gold/5' : ''">
              <td class="p-2">
                <div class="flex items-center gap-2">
                  <img :src="getClassIcon(className)" :alt="className" class="w-6 h-6 rounded border border-border-default" />
                  <span class="text-sm font-medium" :style="{ color: getClassColor(className) }">{{ className }}</span>
                  <span v-if="isCustomized(className)" class="text-[8px] px-1 py-0.5 rounded bg-accent-gold/20 text-accent-gold border border-accent-gold/30 whitespace-nowrap">
                    {{ t('guild.matrixCustomized') }}
                  </span>
                </div>
              </td>
              <td v-for="role in allRoles" :key="role" class="p-2 text-center">
                <button
                  @click="toggleRole(className, role)"
                  class="w-7 h-7 rounded-md border transition-all flex items-center justify-center mx-auto"
                  :class="isRoleEnabled(className, role)
                    ? 'bg-accent-gold/20 border-accent-gold/50 text-accent-gold hover:bg-accent-gold/30'
                    : 'bg-bg-secondary border-border-default text-text-muted/30 hover:border-border-gold/50 hover:text-text-muted'"
                >
                  <svg v-if="isRoleEnabled(className, role)" class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                  </svg>
                  <span v-else class="text-xs">—</span>
                </button>
              </td>
              <td class="p-2 text-center">
                <div class="flex items-center justify-center gap-1">
                  <button v-if="hasLocalChanges(className)" @click="doSaveClass(className)"
                    class="text-[10px] px-2 py-1 rounded bg-accent-gold/20 text-accent-gold border border-accent-gold/30 hover:bg-accent-gold/30 transition-colors"
                    :disabled="savingClass === className">
                    {{ savingClass === className ? '…' : t('guild.matrixSave') }}
                  </button>
                  <button v-if="isCustomized(className)" @click="doResetClass(className)"
                    class="text-[10px] px-2 py-1 rounded bg-red-900/20 text-red-400 border border-red-700/30 hover:bg-red-900/30 transition-colors"
                    :disabled="resettingClass === className">
                    {{ resettingClass === className ? '…' : t('guild.matrixResetClass') }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </WowCard>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import { useGuildStore } from '@/stores/guild'
import { useToast } from '@/composables/useToast'
import { useWowIcons } from '@/composables/useWowIcons'
import * as guildsApi from '@/api/guilds'

import { ROLE_OPTIONS, ROLE_LABEL_MAP, ROLE_LABEL_CLASS } from '@/constants'

const { t } = useI18n()
const toast = useToast()
const guildStore = useGuildStore()
const { getClassIcon, getClassColor } = useWowIcons()

const loading = ref(false)
const matrix = ref(null)
const defaults = ref({})
const overrides = ref({})
const hasOverrides = ref(false)
const resettingAll = ref(false)
const resettingClass = ref(null)
const savingClass = ref(null)

const allRoles = ROLE_OPTIONS.map(r => r.value)
const roleLabels = ROLE_LABEL_MAP

function roleHeaderClass(role) {
  return ROLE_LABEL_CLASS[role] || 'text-text-muted'
}

// Local edits per class — tracks uncommitted checkbox changes
const localEdits = reactive({})

const sortedClasses = computed(() => {
  if (!matrix.value) return []
  return Object.keys(matrix.value).sort()
})

function isCustomized(className) {
  return className in overrides.value
}

function isRoleEnabled(className, role) {
  if (localEdits[className]) {
    return localEdits[className].includes(role)
  }
  const roles = matrix.value?.[className] || []
  return roles.includes(role)
}

function hasLocalChanges(className) {
  if (!localEdits[className]) return false
  const current = matrix.value?.[className] || []
  const local = localEdits[className]
  return JSON.stringify([...current].sort()) !== JSON.stringify([...local].sort())
}

function toggleRole(className, role) {
  if (!localEdits[className]) {
    localEdits[className] = [...(matrix.value?.[className] || [])]
  }
  const idx = localEdits[className].indexOf(role)
  if (idx >= 0) {
    localEdits[className].splice(idx, 1)
  } else {
    localEdits[className].push(role)
  }
}

async function loadMatrix() {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  loading.value = true
  try {
    const result = await guildsApi.getClassRoleMatrix(guildId)
    matrix.value = result.matrix
    defaults.value = result.defaults
    overrides.value = result.overrides
    hasOverrides.value = result.has_overrides
    // Clear local edits
    Object.keys(localEdits).forEach(k => delete localEdits[k])
  } catch { /* ignore */ }
  loading.value = false
}

async function doSaveClass(className) {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  const roles = localEdits[className]
  if (!roles || roles.length === 0) {
    toast.error(t('guild.matrixSelectAtLeastOne'))
    return
  }
  savingClass.value = className
  try {
    await guildsApi.setClassRoleOverrides(guildId, className, roles)
    toast.success(t('guild.matrixSaved'))
    await loadMatrix()
  } catch (err) {
    toast.error(err?.response?.data?.error || 'Error')
  }
  savingClass.value = null
}

async function doResetClass(className) {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  resettingClass.value = className
  try {
    await guildsApi.resetClassRoleOverrides(guildId, className)
    toast.success(t('guild.matrixReset'))
    await loadMatrix()
  } catch (err) {
    toast.error(err?.response?.data?.error || 'Error')
  }
  resettingClass.value = null
}

async function doResetAll() {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  if (!confirm(t('guild.matrixResetAllConfirm'))) return
  resettingAll.value = true
  try {
    await guildsApi.resetClassRoleMatrix(guildId)
    toast.success(t('guild.matrixAllReset'))
    await loadMatrix()
  } catch (err) {
    toast.error(err?.response?.data?.error || 'Error')
  }
  resettingAll.value = false
}

onMounted(loadMatrix)
</script>
