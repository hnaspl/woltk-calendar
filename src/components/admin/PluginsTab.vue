<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="wow-heading text-lg">{{ t('plugin.title') }}</h2>
        <p class="text-sm text-text-muted mt-1">{{ t('plugin.description') }}</p>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="text-center py-8 text-text-muted">
      <svg class="animate-spin h-6 w-6 mx-auto mb-2" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    </div>

    <!-- Plugin list -->
    <div v-else-if="plugins.length" class="grid gap-4">
      <div
        v-for="plugin in plugins"
        :key="plugin.key"
        class="rounded-lg border border-border-default bg-bg-secondary p-4"
      >
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-3">
            <!-- Plugin type badge -->
            <span
              class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
              :class="plugin.plugin_type === 'integration'
                ? 'bg-blue-900/40 text-blue-300 border border-blue-700'
                : 'bg-purple-900/40 text-purple-300 border border-purple-700'"
            >
              {{ plugin.plugin_type === 'integration' ? t('plugin.integration') : t('plugin.expansion') }}
            </span>
            <h3 class="text-base font-semibold text-text-primary">{{ plugin.display_name }}</h3>
          </div>
          <span class="text-xs text-text-muted">v{{ plugin.version }}</span>
        </div>

        <p v-if="plugin.description" class="text-sm text-text-muted mb-3">{{ plugin.description }}</p>

        <!-- Feature flags -->
        <div v-if="Object.keys(plugin.feature_flags || {}).length" class="mb-3">
          <p class="text-xs font-medium text-text-muted mb-1.5">{{ t('plugin.featureFlags') }}</p>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="(enabled, flag) in plugin.feature_flags"
              :key="flag"
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs"
              :class="enabled
                ? 'bg-green-900/30 text-green-300 border border-green-700'
                : 'bg-gray-800 text-gray-400 border border-gray-600'"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="enabled ? 'bg-green-400' : 'bg-gray-500'" />
              {{ flag }}
            </span>
          </div>
        </div>

        <!-- Dependencies -->
        <div v-if="plugin.dependencies && plugin.dependencies.length" class="text-xs text-text-muted">
          <span class="font-medium">{{ t('plugin.dependencies') }}:</span>
          {{ plugin.dependencies.join(', ') }}
        </div>
        <div v-else class="text-xs text-text-muted">
          <span class="font-medium">{{ t('plugin.dependencies') }}:</span>
          {{ t('plugin.noDependencies') }}
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="text-center py-8 text-text-muted">
      {{ t('plugin.noPlugins') }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import * as pluginsApi from '@/api/plugins'

const { t } = useI18n()

const plugins = ref([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    plugins.value = await pluginsApi.listPlugins()
  } catch {
    // silently degrade
  } finally {
    loading.value = false
  }
})
</script>
