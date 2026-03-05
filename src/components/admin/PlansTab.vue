<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="wow-heading text-lg">{{ t('admin.plans.title') }}</h2>
        <p class="text-sm text-text-muted mt-1">{{ t('admin.plans.description') }}</p>
      </div>
      <button
        type="button"
        class="px-3 py-1.5 rounded-lg bg-accent-gold/20 text-accent-gold text-sm font-medium hover:bg-accent-gold/30 transition-colors"
        @click="showCreate = true"
      >{{ t('admin.plans.create') }}</button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-8 text-text-muted">
      <svg class="animate-spin h-6 w-6 mx-auto mb-2" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    </div>

    <!-- Plans grid -->
    <div v-else-if="plans.length" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="plan in plans"
        :key="plan.id"
        class="rounded-lg border bg-bg-secondary p-4"
        :class="plan.is_active ? 'border-border-default' : 'border-red-800 opacity-60'"
      >
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-base font-semibold text-text-primary">{{ plan.name }}</h3>
          <div class="flex gap-1.5">
            <span v-if="plan.is_free" class="px-2 py-0.5 rounded text-xs font-medium bg-gray-700 text-gray-300">
              {{ t('admin.plans.free') }}
            </span>
            <span v-if="!plan.is_active" class="px-2 py-0.5 rounded text-xs font-medium bg-red-900/30 text-red-400">
              {{ t('admin.plans.inactive') }}
            </span>
          </div>
        </div>

        <p v-if="plan.description" class="text-sm text-text-muted mb-3">{{ plan.description }}</p>

        <div class="space-y-1 text-sm text-text-muted mb-3">
          <div class="flex justify-between">
            <span>{{ t('admin.plans.maxGuilds') }}</span>
            <span class="text-text-primary">{{ plan.max_guilds ?? '∞' }}</span>
          </div>
          <div class="flex justify-between">
            <span>{{ t('admin.plans.maxMembers') }}</span>
            <span class="text-text-primary">{{ plan.max_members ?? '∞' }}</span>
          </div>
          <div class="flex justify-between">
            <span>{{ t('admin.plans.maxEvents') }}</span>
            <span class="text-text-primary">{{ plan.max_events_per_month ?? '∞' }}</span>
          </div>
        </div>

        <div v-if="plan.price_info" class="text-xs text-text-muted mb-3">
          <span class="font-medium">{{ t('admin.plans.price') }}:</span> {{ plan.price_info }}
        </div>

        <div class="flex gap-2 pt-2 border-t border-border-default">
          <button
            type="button"
            class="text-xs text-accent-gold hover:text-accent-gold/80 transition-colors"
            @click="startEdit(plan)"
          >{{ t('common.buttons.edit') }}</button>
          <button
            type="button"
            class="text-xs text-red-400 hover:text-red-300 transition-colors"
            @click="doDelete(plan)"
          >{{ t('common.buttons.delete') }}</button>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="text-center py-8 text-text-muted">
      {{ t('admin.plans.noPlans') }}
    </div>

    <!-- Platform Features Section -->
    <div class="border-t border-border-default pt-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="wow-heading text-lg">{{ t('admin.functions.title') }}</h2>
          <p class="text-sm text-text-muted mt-1">{{ t('admin.functions.description') }}</p>
        </div>
      </div>

      <div v-if="featuresLoading" class="text-center py-8 text-text-muted">
        <svg class="animate-spin h-6 w-6 mx-auto mb-2" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>

      <div v-else-if="features.length" class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border-default text-left">
              <th class="px-4 py-3 text-text-muted font-medium">{{ t('admin.functions.feature') }}</th>
              <th class="px-4 py-3 text-text-muted font-medium">{{ t('admin.functions.description') }}</th>
              <th class="px-4 py-3 text-text-muted font-medium text-center">{{ t('admin.functions.globallyEnabled') }}</th>
              <th class="px-4 py-3 text-text-muted font-medium text-center">{{ t('admin.functions.requiresPlan') }}</th>
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
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="text-center py-8 text-text-muted">
        <p>{{ t('admin.functions.empty') }}</p>
      </div>

      <div v-if="featuresError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm mt-3">{{ featuresError }}</div>
    </div>

    <!-- Create / Edit modal -->
    <div v-if="showCreate || editingPlan" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div class="bg-bg-secondary border border-border-default rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div class="p-4 border-b border-border-default">
          <h3 class="text-lg font-semibold text-text-primary">
            {{ editingPlan ? t('admin.plans.editTitle') : t('admin.plans.createTitle') }}
          </h3>
        </div>
        <form class="p-4 space-y-4" @submit.prevent="savePlan">
          <div>
            <label class="block text-sm font-medium text-text-muted mb-1">{{ t('admin.plans.nameLabel') }}</label>
            <input v-model="form.name" type="text" required
              class="w-full px-3 py-2 rounded-lg bg-bg-primary border border-border-default text-text-primary text-sm focus:border-accent-gold focus:outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-text-muted mb-1">{{ t('admin.plans.slugLabel') }}</label>
            <input v-model="form.slug" type="text" required
              class="w-full px-3 py-2 rounded-lg bg-bg-primary border border-border-default text-text-primary text-sm focus:border-accent-gold focus:outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-text-muted mb-1">{{ t('admin.plans.descriptionLabel') }}</label>
            <textarea v-model="form.description" rows="2"
              class="w-full px-3 py-2 rounded-lg bg-bg-primary border border-border-default text-text-primary text-sm focus:border-accent-gold focus:outline-none" />
          </div>
          <div class="grid grid-cols-3 gap-3">
            <div>
              <label class="block text-sm font-medium text-text-muted mb-1">{{ t('admin.plans.maxGuilds') }}</label>
              <input v-model.number="form.max_guilds" type="number" min="1"
                class="w-full px-3 py-2 rounded-lg bg-bg-primary border border-border-default text-text-primary text-sm focus:border-accent-gold focus:outline-none" />
            </div>
            <div>
              <label class="block text-sm font-medium text-text-muted mb-1">{{ t('admin.plans.maxMembers') }}</label>
              <input v-model.number="form.max_members" type="number" min="1"
                class="w-full px-3 py-2 rounded-lg bg-bg-primary border border-border-default text-text-primary text-sm focus:border-accent-gold focus:outline-none" />
            </div>
            <div>
              <label class="block text-sm font-medium text-text-muted mb-1">{{ t('admin.plans.maxEvents') }}</label>
              <input v-model.number="form.max_events_per_month" type="number" min="1"
                class="w-full px-3 py-2 rounded-lg bg-bg-primary border border-border-default text-text-primary text-sm focus:border-accent-gold focus:outline-none" />
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-text-muted mb-1">{{ t('admin.plans.price') }}</label>
            <input v-model="form.price_info" type="text"
              class="w-full px-3 py-2 rounded-lg bg-bg-primary border border-border-default text-text-primary text-sm focus:border-accent-gold focus:outline-none" />
          </div>
          <div class="flex gap-4">
            <label class="flex items-center gap-2 text-sm text-text-muted cursor-pointer">
              <input v-model="form.is_free" type="checkbox"
                class="rounded border-border-default bg-bg-primary text-accent-gold focus:ring-accent-gold" />
              {{ t('admin.plans.isFree') }}
            </label>
            <label class="flex items-center gap-2 text-sm text-text-muted cursor-pointer">
              <input v-model="form.is_active" type="checkbox"
                class="rounded border-border-default bg-bg-primary text-accent-gold focus:ring-accent-gold" />
              {{ t('admin.plans.isActive') }}
            </label>
          </div>
          <div v-if="formError" class="text-sm text-red-400">{{ formError }}</div>
          <div class="flex justify-end gap-2 pt-2">
            <button type="button" class="px-3 py-1.5 rounded-lg text-sm text-text-muted hover:text-text-primary transition-colors"
              @click="closeModal">{{ t('common.buttons.cancel') }}</button>
            <button type="submit" class="px-3 py-1.5 rounded-lg bg-accent-gold/20 text-accent-gold text-sm font-medium hover:bg-accent-gold/30 transition-colors"
              :disabled="saving">{{ saving ? t('common.labels.loading') : t('common.buttons.save') }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import * as plansApi from '@/api/plans'
import api from '@/api/index'

const { t } = useI18n()

const plans = ref([])
const loading = ref(false)
const showCreate = ref(false)
const editingPlan = ref(null)
const saving = ref(false)
const formError = ref('')

// Platform features state
const features = ref([])
const featuresLoading = ref(true)
const featuresError = ref(null)

const emptyForm = () => ({
  name: '', slug: '', description: '', max_guilds: 3, max_members: null,
  max_events_per_month: null, price_info: '', is_free: false, is_active: true
})
const form = ref(emptyForm())

async function fetchPlans() {
  loading.value = true
  try {
    plans.value = await plansApi.listPlans()
  } catch {
    // silently degrade
  } finally {
    loading.value = false
  }
}

async function loadFeatures() {
  featuresLoading.value = true
  featuresError.value = null
  try {
    features.value = await api.get('/admin/platform-features')
  } catch (err) {
    featuresError.value = err?.response?.data?.error || 'Failed to load features'
  } finally {
    featuresLoading.value = false
  }
}

async function toggleGlobal(feat) {
  try {
    const updated = await api.put(`/admin/platform-features/${feat.feature_key}`, {
      globally_enabled: !feat.globally_enabled
    })
    Object.assign(feat, updated)
  } catch (err) {
    featuresError.value = err?.response?.data?.error || 'Failed to update feature'
  }
}

async function togglePaywall(feat) {
  try {
    const updated = await api.put(`/admin/platform-features/${feat.feature_key}`, {
      requires_plan: !feat.requires_plan
    })
    Object.assign(feat, updated)
  } catch (err) {
    featuresError.value = err?.response?.data?.error || 'Failed to update feature'
  }
}

function startEdit(plan) {
  editingPlan.value = plan
  form.value = {
    name: plan.name,
    slug: plan.slug,
    description: plan.description || '',
    max_guilds: plan.max_guilds,
    max_members: plan.max_members,
    max_events_per_month: plan.max_events_per_month,
    price_info: plan.price_info || '',
    is_free: plan.is_free,
    is_active: plan.is_active
  }
  formError.value = ''
}

function closeModal() {
  showCreate.value = false
  editingPlan.value = null
  form.value = emptyForm()
  formError.value = ''
}

async function savePlan() {
  saving.value = true
  formError.value = ''
  try {
    if (editingPlan.value) {
      await plansApi.updatePlan(editingPlan.value.id, form.value)
    } else {
      await plansApi.createPlan(form.value)
    }
    closeModal()
    await fetchPlans()
  } catch (err) {
    formError.value = err.response?.data?.error || err.response?.data?.message || t('common.labels.error')
  } finally {
    saving.value = false
  }
}

async function doDelete(plan) {
  if (!confirm(t('admin.plans.confirmDelete', { name: plan.name }))) return
  try {
    await plansApi.deletePlan(plan.id)
    await fetchPlans()
  } catch {
    // ignore
  }
}

onMounted(() => {
  fetchPlans()
  loadFeatures()
})
</script>
