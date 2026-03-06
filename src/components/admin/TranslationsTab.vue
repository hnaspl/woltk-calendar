<template>
  <div class="space-y-6">
    <!-- Stats Summary -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="wow-card p-4">
        <div class="text-text-muted text-xs uppercase tracking-wide mb-1">{{ t('admin.translations.totalKeys') }}</div>
        <div class="flex items-baseline gap-3">
          <span v-for="locale in locales" :key="locale" class="text-lg font-bold text-text-primary">
            <span class="text-accent-gold">{{ locale.toUpperCase() }}</span>:
            {{ stats?.locales?.[locale]?.total_keys ?? '—' }}
          </span>
        </div>
      </div>
      <div class="wow-card p-4">
        <div class="text-text-muted text-xs uppercase tracking-wide mb-1">{{ t('admin.translations.overrides') }}</div>
        <div class="flex items-baseline gap-3">
          <span v-for="locale in locales" :key="locale" class="text-lg font-bold text-text-primary">
            <span class="text-accent-gold">{{ locale.toUpperCase() }}</span>:
            {{ stats?.locales?.[locale]?.override_count ?? 0 }}
          </span>
        </div>
      </div>
      <div class="wow-card p-4">
        <div class="text-text-muted text-xs uppercase tracking-wide mb-1">{{ t('admin.translations.missingKeys') }}</div>
        <div class="text-lg font-bold" :class="(stats?.total_missing ?? 0) > 0 ? 'text-red-400' : 'text-green-400'">
          {{ stats?.total_missing ?? 0 }}
          <span v-if="(stats?.total_missing ?? 0) === 0" class="text-sm font-normal">✓</span>
        </div>
      </div>
    </div>

    <!-- Controls -->
    <div class="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
      <!-- Locale selector -->
      <div class="flex gap-2">
        <button
          v-for="locale in locales"
          :key="locale"
          type="button"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="selectedLocale === locale
            ? 'bg-accent-gold text-bg-primary'
            : 'bg-bg-tertiary text-text-muted hover:text-text-primary border border-border-default'"
          @click="selectLocale(locale)"
        >
          {{ locale.toUpperCase() }}
        </button>
      </div>

      <!-- Section filter -->
      <select
        v-model="selectedSection"
        class="wow-input text-sm flex-1 max-w-xs"
        @change="loadTranslations"
      >
        <option value="">{{ t('admin.translations.allSections') }}</option>
        <option v-for="section in sections" :key="section" :value="section">
          {{ section }}
        </option>
      </select>

      <!-- Search -->
      <div class="relative flex-1 max-w-md">
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="t('admin.translations.searchPlaceholder')"
          class="wow-input text-sm w-full pl-8"
        />
        <svg class="absolute left-2.5 top-2.5 w-4 h-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>

      <!-- View mode toggle -->
      <div class="flex gap-1 bg-bg-tertiary rounded-lg p-0.5">
        <button
          type="button"
          class="px-3 py-1.5 rounded text-xs font-medium transition-colors"
          :class="viewMode === 'all' ? 'bg-accent-gold text-bg-primary' : 'text-text-muted hover:text-text-primary'"
          @click="viewMode = 'all'"
        >
          {{ t('admin.translations.viewAll') }}
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded text-xs font-medium transition-colors"
          :class="viewMode === 'missing' ? 'bg-red-600 text-white' : 'text-text-muted hover:text-text-primary'"
          @click="viewMode = 'missing'; loadMissing()"
        >
          {{ t('admin.translations.viewMissing') }}
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded text-xs font-medium transition-colors"
          :class="viewMode === 'overrides' ? 'bg-blue-600 text-white' : 'text-text-muted hover:text-text-primary'"
          @click="viewMode = 'overrides'; loadOverrides()"
        >
          {{ t('admin.translations.viewOverrides') }}
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-8">
      <div class="animate-spin w-6 h-6 border-2 border-accent-gold border-t-transparent rounded-full mx-auto"></div>
      <p class="text-text-muted text-sm mt-2">{{ t('common.labels.loading') }}</p>
    </div>

    <!-- Missing translations view -->
    <template v-else-if="viewMode === 'missing'">
      <div v-if="Object.keys(missingKeys).length === 0" class="wow-card p-6 text-center">
        <p class="text-green-400 text-lg font-medium">{{ t('admin.translations.noMissing') }}</p>
        <p class="text-text-muted text-sm mt-1">{{ t('admin.translations.allSynced') }}</p>
      </div>
      <div v-else class="space-y-4">
        <div v-for="(keys, group) in missingKeys" :key="group" class="wow-card overflow-hidden">
          <div class="px-4 py-3 bg-red-900/20 border-b border-border-default">
            <h3 class="text-sm font-medium text-red-400">
              {{ group.replace('missing_in_', '').toUpperCase() }} — {{ keys.length }} {{ t('admin.translations.keysMissing') }}
            </h3>
          </div>
          <div class="divide-y divide-border-default max-h-96 overflow-y-auto">
            <div
              v-for="key in keys"
              :key="key"
              class="px-4 py-2 flex items-center justify-between gap-4 hover:bg-bg-tertiary"
            >
              <code class="text-xs text-text-muted font-mono break-all">{{ key }}</code>
              <button
                type="button"
                class="text-xs px-2 py-1 rounded bg-accent-gold/20 text-accent-gold hover:bg-accent-gold/30 whitespace-nowrap"
                @click="startAddMissing(group.replace('missing_in_', ''), key)"
              >
                {{ t('admin.translations.addTranslation') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Overrides view -->
    <template v-else-if="viewMode === 'overrides'">
      <div v-if="overrides.length === 0" class="wow-card p-6 text-center">
        <p class="text-text-muted">{{ t('admin.translations.noOverrides') }}</p>
      </div>
      <div v-else class="wow-card overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-bg-tertiary">
              <tr>
                <th class="px-4 py-2 text-left text-text-muted font-medium text-xs">{{ t('admin.translations.locale') }}</th>
                <th class="px-4 py-2 text-left text-text-muted font-medium text-xs">{{ t('admin.translations.key') }}</th>
                <th class="px-4 py-2 text-left text-text-muted font-medium text-xs">{{ t('admin.translations.value') }}</th>
                <th class="px-4 py-2 text-right text-text-muted font-medium text-xs">{{ t('admin.translations.actions') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border-default">
              <tr v-for="override in overrides" :key="override.id" class="hover:bg-bg-tertiary">
                <td class="px-4 py-2">
                  <span class="px-2 py-0.5 rounded text-xs font-medium bg-accent-gold/20 text-accent-gold">
                    {{ override.locale.toUpperCase() }}
                  </span>
                </td>
                <td class="px-4 py-2">
                  <code class="text-xs font-mono text-text-muted break-all">{{ override.key }}</code>
                </td>
                <td class="px-4 py-2 text-text-primary max-w-md truncate">{{ override.value }}</td>
                <td class="px-4 py-2 text-right">
                  <div class="flex gap-1 justify-end">
                    <button
                      type="button"
                      class="text-xs px-2 py-1 rounded bg-blue-600/20 text-blue-400 hover:bg-blue-600/30"
                      @click="startEdit(override.locale, override.key, override.value)"
                    >
                      {{ t('common.buttons.edit') }}
                    </button>
                    <button
                      type="button"
                      class="text-xs px-2 py-1 rounded bg-red-600/20 text-red-400 hover:bg-red-600/30"
                      @click="revertOverride(override.locale, override.key)"
                    >
                      {{ t('admin.translations.revert') }}
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- All translations view -->
    <template v-else>
      <div v-if="filteredTranslations.length === 0" class="wow-card p-6 text-center">
        <p class="text-text-muted">{{ t('admin.translations.noResults') }}</p>
      </div>
      <div v-else class="wow-card overflow-hidden">
        <div class="px-4 py-2 bg-bg-tertiary border-b border-border-default text-xs text-text-muted">
          {{ t('admin.translations.showing') }} {{ filteredTranslations.length }} / {{ Object.keys(translations).length }} {{ t('admin.translations.keys') }}
        </div>
        <div class="divide-y divide-border-default max-h-[600px] overflow-y-auto">
          <div
            v-for="[key, value] in filteredTranslations"
            :key="key"
            class="px-4 py-2.5 hover:bg-bg-tertiary group"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 min-w-0">
                <code class="text-xs font-mono text-accent-gold break-all">{{ key }}</code>
                <div
                  v-if="editingKey !== key"
                  class="text-sm text-text-primary mt-0.5 break-words cursor-pointer hover:text-accent-gold transition-colors"
                  @click="startEdit(selectedLocale, key, value)"
                >
                  {{ value || '—' }}
                </div>
                <!-- Inline edit -->
                <div v-else class="mt-1 flex gap-2">
                  <textarea
                    ref="editTextarea"
                    v-model="editValue"
                    class="wow-input text-sm flex-1 min-h-[36px]"
                    rows="2"
                    @keydown.meta.enter="saveEdit"
                    @keydown.ctrl.enter="saveEdit"
                    @keydown.escape="cancelEdit"
                  ></textarea>
                  <div class="flex flex-col gap-1">
                    <button
                      type="button"
                      class="px-3 py-1 rounded bg-accent-gold text-bg-primary text-xs font-medium hover:bg-accent-gold/80"
                      :disabled="saving"
                      @click="saveEdit"
                    >
                      {{ t('common.buttons.save') }}
                    </button>
                    <button
                      type="button"
                      class="px-3 py-1 rounded bg-bg-tertiary text-text-muted text-xs hover:text-text-primary"
                      @click="cancelEdit"
                    >
                      {{ t('common.buttons.cancel') }}
                    </button>
                  </div>
                </div>
              </div>
              <button
                v-if="editingKey !== key"
                type="button"
                class="opacity-0 group-hover:opacity-100 text-xs px-2 py-1 rounded bg-bg-tertiary text-text-muted hover:text-text-primary transition-opacity"
                @click="startEdit(selectedLocale, key, value)"
              >
                {{ t('common.buttons.edit') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Add missing translation modal -->
    <WowModal v-if="showAddModal" :title="t('admin.translations.addTranslation')" size="lg" @close="showAddModal = false">
      <div class="space-y-4">
        <div>
          <label class="text-sm text-text-muted">{{ t('admin.translations.locale') }}</label>
          <div class="mt-1 px-3 py-2 rounded bg-bg-tertiary text-sm font-medium text-accent-gold">
            {{ addLocale.toUpperCase() }}
          </div>
        </div>
        <div>
          <label class="text-sm text-text-muted">{{ t('admin.translations.key') }}</label>
          <div class="mt-1 px-3 py-2 rounded bg-bg-tertiary">
            <code class="text-sm font-mono text-text-primary">{{ addKey }}</code>
          </div>
        </div>
        <!-- Show reference value from other locale -->
        <div v-if="addReferenceValue">
          <label class="text-sm text-text-muted">{{ t('admin.translations.referenceValue') }}</label>
          <div class="mt-1 px-3 py-2 rounded bg-bg-tertiary text-sm text-text-muted italic">
            {{ addReferenceValue }}
          </div>
        </div>
        <div>
          <label class="text-sm text-text-muted">{{ t('admin.translations.value') }}</label>
          <textarea
            v-model="addValue"
            class="wow-input w-full text-sm mt-1"
            rows="3"
            :placeholder="t('admin.translations.enterTranslation')"
          ></textarea>
        </div>
        <div class="flex justify-end gap-2">
          <button
            type="button"
            class="px-4 py-2 rounded-lg bg-bg-tertiary text-text-muted hover:text-text-primary text-sm"
            @click="showAddModal = false"
          >
            {{ t('common.buttons.cancel') }}
          </button>
          <button
            type="button"
            class="px-4 py-2 rounded-lg bg-accent-gold text-bg-primary font-medium text-sm hover:bg-accent-gold/80"
            :disabled="!addValue.trim() || saving"
            @click="saveAddMissing"
          >
            {{ t('common.buttons.save') }}
          </button>
        </div>
      </div>
    </WowModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  getTranslationStats,
  getTranslations,
  getMissingTranslations,
  getTranslationOverrides,
  updateTranslation,
  deleteTranslationOverride,
} from '@/api/admin'
import WowModal from '@/components/common/WowModal.vue'
import { useToast } from '@/composables/useToast'

const { t } = useI18n()
const toast = useToast()

const locales = ['en', 'pl']
const selectedLocale = ref('en')
const selectedSection = ref('')
const searchQuery = ref('')
const viewMode = ref('all')
const loading = ref(false)
const saving = ref(false)

const stats = ref(null)
const translations = ref({})
const sections = ref([])
const missingKeys = ref({})
const overrides = ref([])

// Edit state
const editingKey = ref(null)
const editValue = ref('')
const editTextarea = ref(null)

// Add missing modal
const showAddModal = ref(false)
const addLocale = ref('')
const addKey = ref('')
const addValue = ref('')
const addReferenceValue = ref('')

const filteredTranslations = computed(() => {
  const entries = Object.entries(translations.value)
  if (!searchQuery.value.trim()) return entries
  const q = searchQuery.value.toLowerCase()
  return entries.filter(([key, value]) =>
    key.toLowerCase().includes(q) || (value && value.toLowerCase().includes(q))
  )
})

async function loadStats() {
  try {
    const data = await getTranslationStats()
    stats.value = data
  } catch (e) {
    console.error('Failed to load translation stats:', e)
  }
}

async function selectLocale(locale) {
  selectedLocale.value = locale
  await loadTranslations()
}

async function loadTranslations() {
  loading.value = true
  try {
    const data = await getTranslations(selectedLocale.value, selectedSection.value || undefined)
    translations.value = data.translations || {}
    sections.value = data.sections || []
  } catch (e) {
    toast.error(t('common.errors.generic'))
    console.error('Failed to load translations:', e)
  } finally {
    loading.value = false
  }
}

async function loadMissing() {
  loading.value = true
  try {
    missingKeys.value = await getMissingTranslations()
  } catch (e) {
    toast.error(t('common.errors.generic'))
  } finally {
    loading.value = false
  }
}

async function loadOverrides() {
  loading.value = true
  try {
    const data = await getTranslationOverrides()
    overrides.value = data.overrides || []
  } catch (e) {
    toast.error(t('common.errors.generic'))
  } finally {
    loading.value = false
  }
}

function startEdit(locale, key, value) {
  selectedLocale.value = locale
  editingKey.value = key
  editValue.value = value || ''
  nextTick(() => {
    if (editTextarea.value) {
      const el = Array.isArray(editTextarea.value) ? editTextarea.value[0] : editTextarea.value
      if (el) el.focus()
    }
  })
}

function cancelEdit() {
  editingKey.value = null
  editValue.value = ''
}

async function saveEdit() {
  if (!editingKey.value) return
  saving.value = true
  try {
    await updateTranslation(selectedLocale.value, editingKey.value, editValue.value)
    translations.value[editingKey.value] = editValue.value
    toast.success(t('admin.translations.saved'))
    cancelEdit()
    await loadStats()
  } catch (e) {
    toast.error(e.response?.data?.error || t('common.errors.generic'))
  } finally {
    saving.value = false
  }
}

async function revertOverride(locale, key) {
  if (!confirm(t('admin.translations.confirmRevert'))) return
  try {
    await deleteTranslationOverride(locale, key)
    toast.success(t('admin.translations.reverted'))
    await loadOverrides()
    await loadStats()
  } catch (e) {
    toast.error(t('common.errors.generic'))
  }
}

async function startAddMissing(locale, key) {
  addLocale.value = locale
  addKey.value = key
  addValue.value = ''

  // Try to get reference value from other locale
  const otherLocale = locale === 'en' ? 'pl' : 'en'
  try {
    const data = await getTranslations(otherLocale)
    addReferenceValue.value = data.translations?.[key] || ''
  } catch {
    addReferenceValue.value = ''
  }
  showAddModal.value = true
}

async function saveAddMissing() {
  if (!addValue.value.trim()) return
  saving.value = true
  try {
    await updateTranslation(addLocale.value, addKey.value, addValue.value.trim())
    toast.success(t('admin.translations.saved'))
    showAddModal.value = false
    await loadMissing()
    await loadStats()
  } catch (e) {
    toast.error(e.response?.data?.error || t('common.errors.generic'))
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadStats(), loadTranslations()])
})
</script>
