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

      <div v-else-if="!matrix" class="py-6 text-center">
        <p class="text-sm text-text-muted">{{ t('guild.matrixNoOverrides') }}</p>
      </div>

      <div v-else class="space-y-3">
        <div v-for="className in sortedClasses" :key="className"
          class="p-3 rounded-lg border transition-colors"
          :class="isCustomized(className)
            ? 'bg-accent-gold/5 border-accent-gold/30'
            : 'bg-bg-tertiary border-border-default'">
          <div class="flex items-center justify-between gap-2 mb-2">
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-text-primary">{{ className }}</span>
              <span v-if="isCustomized(className)" class="text-[10px] px-1.5 py-0.5 rounded bg-accent-gold/20 text-accent-gold border border-accent-gold/30">
                {{ t('guild.matrixCustomized') }}
              </span>
              <span v-else class="text-[10px] px-1.5 py-0.5 rounded bg-bg-secondary text-text-muted border border-border-default">
                {{ t('guild.matrixDefault') }}
              </span>
            </div>
            <div class="flex items-center gap-2">
              <WowButton v-if="isCustomized(className)" variant="danger" @click="doResetClass(className)" :loading="resettingClass === className" class="text-xs py-1 px-2">
                {{ t('guild.matrixResetClass') }}
              </WowButton>
              <WowButton v-if="hasLocalChanges(className)" @click="doSaveClass(className)" :loading="savingClass === className" class="text-xs py-1 px-2">
                {{ t('guild.matrixSave') }}
              </WowButton>
            </div>
          </div>
          <div class="flex flex-wrap gap-2">
            <label v-for="role in allRoles" :key="role"
              class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border cursor-pointer transition-colors text-xs"
              :class="isRoleEnabled(className, role)
                ? 'bg-accent-gold/10 border-accent-gold/40 text-accent-gold'
                : 'bg-bg-secondary border-border-default text-text-muted hover:border-border-gold/50'">
              <input type="checkbox" :checked="isRoleEnabled(className, role)"
                @change="toggleRole(className, role)" class="sr-only" />
              <span class="w-3 h-3 rounded border flex items-center justify-center flex-shrink-0"
                :class="isRoleEnabled(className, role)
                  ? 'bg-accent-gold border-accent-gold'
                  : 'border-border-default'">
                <svg v-if="isRoleEnabled(className, role)" class="w-2 h-2 text-bg-primary" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                </svg>
              </span>
              {{ roleLabels[role] || role }}
            </label>
          </div>
        </div>
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
import { useUiStore } from '@/stores/ui'
import * as guildsApi from '@/api/guilds'

import { ROLE_OPTIONS, ROLE_LABEL_MAP } from '@/constants'

const { t } = useI18n()
const uiStore = useUiStore()
const guildStore = useGuildStore()

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
    const { data } = await guildsApi.getClassRoleMatrix(guildId)
    matrix.value = data.matrix
    defaults.value = data.defaults
    overrides.value = data.overrides
    hasOverrides.value = data.has_overrides
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
    uiStore.showToast(t('guild.matrixSelectAtLeastOne'), 'error')
    return
  }
  savingClass.value = className
  try {
    await guildsApi.setClassRoleOverrides(guildId, className, roles)
    uiStore.showToast(t('guild.matrixSaved'), 'success')
    await loadMatrix()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || 'Error', 'error')
  }
  savingClass.value = null
}

async function doResetClass(className) {
  const guildId = guildStore.currentGuildId
  if (!guildId) return
  resettingClass.value = className
  try {
    await guildsApi.resetClassRoleOverrides(guildId, className)
    uiStore.showToast(t('guild.matrixReset'), 'success')
    await loadMatrix()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || 'Error', 'error')
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
    uiStore.showToast(t('guild.matrixAllReset'), 'success')
    await loadMatrix()
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error || 'Error', 'error')
  }
  resettingAll.value = false
}

onMounted(loadMatrix)
</script>
