<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="wow-heading text-lg">{{ t('admin.functions.title') }}</h2>
        <p class="text-sm text-text-muted mt-1">{{ t('admin.functions.description') }}</p>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="text-center py-8 text-text-muted">
      <svg class="animate-spin h-6 w-6 mx-auto mb-2" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    </div>

    <!-- Features table -->
    <div v-else-if="features.length" class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-border-default text-left">
            <th class="px-4 py-3 text-text-muted font-medium">{{ t('admin.functions.feature') }}</th>
            <th class="px-4 py-3 text-text-muted font-medium">{{ t('admin.functions.description') }}</th>
            <th class="px-4 py-3 text-text-muted font-medium text-center">{{ t('admin.functions.globallyEnabled') }}</th>
            <th class="px-4 py-3 text-text-muted font-medium text-center">{{ t('admin.functions.requiresPlan') }}</th>
            <th class="px-4 py-3 text-text-muted font-medium text-center">{{ t('common.buttons.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="feat in features" :key="feat.feature_key" class="border-b border-border-default/50 hover:bg-bg-tertiary/50 transition-colors">
            <td class="px-4 py-3">
              <span class="font-medium text-text-primary">{{ feat.display_name }}</span>
              <span class="ml-2 text-xs text-text-muted font-mono">({{ feat.feature_key }})</span>
            </td>
            <td class="px-4 py-3 text-text-muted text-xs max-w-xs">{{ feat.description }}</td>
            <td class="px-4 py-3 text-center">
              <button
                @click="toggleGlobal(feat)"
                class="inline-flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium transition-colors"
                :class="feat.globally_enabled
                  ? 'bg-green-900/30 text-green-300 border border-green-700/50 hover:bg-green-900/50'
                  : 'bg-red-900/30 text-red-300 border border-red-700/50 hover:bg-red-900/50'"
              >
                {{ feat.globally_enabled ? t('common.labels.enabled') : t('common.labels.disabled') }}
              </button>
            </td>
            <td class="px-4 py-3 text-center">
              <button
                @click="togglePaywall(feat)"
                class="inline-flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium transition-colors"
                :class="feat.requires_plan
                  ? 'bg-yellow-900/30 text-yellow-300 border border-yellow-700/50 hover:bg-yellow-900/50'
                  : 'bg-bg-tertiary text-text-muted border border-border-default hover:border-border-gold'"
              >
                {{ feat.requires_plan ? t('admin.functions.paid') : t('admin.functions.free') }}
              </button>
            </td>
            <td class="px-4 py-3 text-center">
              <span v-if="saving === feat.feature_key" class="text-xs text-text-muted">{{ t('common.labels.saving') }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty state -->
    <div v-else class="text-center py-12 text-text-muted">
      <p>{{ t('admin.functions.empty') }}</p>
    </div>

    <!-- Error -->
    <div v-if="error" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/index'

const { t } = useI18n()

const features = ref([])
const loading = ref(true)
const error = ref(null)
const saving = ref(null)

async function loadFeatures() {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get('/admin/platform-features')
    features.value = data
  } catch (err) {
    error.value = err?.response?.data?.error || 'Failed to load features'
  } finally {
    loading.value = false
  }
}

async function toggleGlobal(feat) {
  saving.value = feat.feature_key
  try {
    const { data } = await api.put(`/admin/platform-features/${feat.feature_key}`, {
      globally_enabled: !feat.globally_enabled
    })
    Object.assign(feat, data)
  } catch (err) {
    error.value = err?.response?.data?.error || 'Failed to update feature'
  } finally {
    saving.value = null
  }
}

async function togglePaywall(feat) {
  saving.value = feat.feature_key
  try {
    const { data } = await api.put(`/admin/platform-features/${feat.feature_key}`, {
      requires_plan: !feat.requires_plan
    })
    Object.assign(feat, data)
  } catch (err) {
    error.value = err?.response?.data?.error || 'Failed to update feature'
  } finally {
    saving.value = null
  }
}

onMounted(loadFeatures)
</script>
