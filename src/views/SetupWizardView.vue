<template>
  <div class="min-h-screen bg-bg-primary flex items-start justify-center p-4 sm:p-8">
    <div class="w-full max-w-2xl">
      <!-- Progress bar -->
      <div class="mb-8">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs text-text-muted">{{ t('setup.stepOf', { current: currentStep, total: totalSteps }) }}</span>
          <span class="text-xs text-accent-gold font-medium">{{ stepTitle }}</span>
        </div>
        <div class="w-full h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
          <div
            class="h-full bg-accent-gold rounded-full transition-all duration-500"
            :style="{ width: `${(currentStep / totalSteps) * 100}%` }"
          />
        </div>
      </div>

      <!-- Step 1: Welcome (tenant path) — set tenant name & slug -->
      <WowCard v-if="currentStep === 1 && isTenantPath" gold>
        <div class="text-center mb-6">
          <div class="w-16 h-16 rounded-full bg-accent-gold/10 border-2 border-accent-gold/30 flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-accent-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
          </div>
          <h2 class="wow-heading text-xl sm:text-2xl mb-2">{{ t('setup.tenantTitle') }}</h2>
          <p class="text-sm text-text-muted">{{ t('setup.tenantDesc') }}</p>
        </div>

        <form @submit.prevent="saveTenantInfo" class="space-y-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('setup.panelName') }}</label>
            <input
              v-model="tenantForm.name"
              required
              :placeholder="t('setup.panelNamePlaceholder')"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
            />
            <p class="text-xs text-text-muted mt-1">{{ t('setup.panelNameHelp') }}</p>
          </div>

          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('setup.panelDescription') }}</label>
            <textarea
              v-model="tenantForm.description"
              rows="2"
              :placeholder="t('setup.panelDescPlaceholder')"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none resize-none placeholder:text-text-muted/50"
            />
          </div>

          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('setup.panelSlug') }}</label>
            <input
              v-model="tenantForm.slug"
              :placeholder="t('setup.panelSlugPlaceholder')"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
            />
            <p class="text-xs text-text-muted mt-1">{{ t('setup.panelSlugHelp') }}</p>
          </div>

          <p v-if="tenantError" class="text-sm text-red-400">{{ tenantError }}</p>

          <div class="flex justify-end pt-2">
            <WowButton type="submit" :loading="saving">
              {{ t('setup.continue') }}
              <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </WowButton>
          </div>
        </form>
      </WowCard>

      <!-- Step 1: Welcome (player path) — introduction -->
      <WowCard v-if="currentStep === 1 && !isTenantPath" gold>
        <div class="text-center mb-6">
          <div class="w-16 h-16 rounded-full bg-accent-gold/10 border-2 border-accent-gold/30 flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-accent-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <h2 class="wow-heading text-xl sm:text-2xl mb-2">{{ t('setup.playerTitle') }}</h2>
          <p class="text-sm text-text-muted">{{ t('setup.playerDesc') }}</p>
        </div>

        <div class="space-y-3 mb-6">
          <div class="flex items-start gap-3 p-3 rounded-lg bg-bg-tertiary border border-border-default">
            <svg class="w-5 h-5 text-accent-gold flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101" />
            </svg>
            <div>
              <p class="text-sm text-text-primary font-medium">{{ t('setup.playerTip1Title') }}</p>
              <p class="text-xs text-text-muted mt-0.5">{{ t('setup.playerTip1Desc') }}</p>
            </div>
          </div>
          <div class="flex items-start gap-3 p-3 rounded-lg bg-bg-tertiary border border-border-default">
            <svg class="w-5 h-5 text-accent-gold flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <div>
              <p class="text-sm text-text-primary font-medium">{{ t('setup.playerTip2Title') }}</p>
              <p class="text-xs text-text-muted mt-0.5">{{ t('setup.playerTip2Desc') }}</p>
            </div>
          </div>
          <div class="flex items-start gap-3 p-3 rounded-lg bg-bg-tertiary border border-border-default">
            <svg class="w-5 h-5 text-accent-gold flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
            </svg>
            <div>
              <p class="text-sm text-text-primary font-medium">{{ t('setup.playerTip3Title') }}</p>
              <p class="text-xs text-text-muted mt-0.5">{{ t('setup.playerTip3Desc') }}</p>
            </div>
          </div>
        </div>

        <div class="flex justify-end">
          <WowButton @click="currentStep = 2">
            {{ t('setup.continue') }}
            <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </WowButton>
        </div>
      </WowCard>

      <!-- Step 2 (tenant path): Create first guild -->
      <WowCard v-if="currentStep === 2 && isTenantPath" gold>
        <div class="text-center mb-6">
          <div class="w-16 h-16 rounded-full bg-accent-gold/10 border-2 border-accent-gold/30 flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-accent-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <h2 class="wow-heading text-xl sm:text-2xl mb-2">{{ t('setup.guildTitle') }}</h2>
          <p class="text-sm text-text-muted">{{ t('setup.guildDesc') }}</p>
        </div>

        <form @submit.prevent="createFirstGuild" class="space-y-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('setup.guildName') }}</label>
            <input
              v-model="guildForm.name"
              required
              :placeholder="t('setup.guildNamePlaceholder')"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
            />
          </div>

          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('setup.guildRealm') }}</label>
            <input
              v-model="guildForm.realm_name"
              required
              :placeholder="t('setup.guildRealmPlaceholder')"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('setup.guildFaction') }}</label>
              <select
                v-model="guildForm.faction"
                class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2.5 focus:border-border-gold outline-none"
              >
                <option value="Alliance">{{ t('setup.alliance') }}</option>
                <option value="Horde">{{ t('setup.horde') }}</option>
              </select>
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('setup.guildTimezone') }}</label>
              <select
                v-model="guildForm.timezone"
                class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2.5 focus:border-border-gold outline-none"
              >
                <option v-for="tz in timezones" :key="tz" :value="tz">{{ tz }}</option>
              </select>
            </div>
          </div>

          <p v-if="guildError" class="text-sm text-red-400">{{ guildError }}</p>

          <div class="flex justify-between pt-2">
            <WowButton variant="ghost" @click="currentStep = 1">
              <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
              </svg>
              {{ t('setup.back') }}
            </WowButton>
            <WowButton type="submit" :loading="saving">
              {{ t('setup.createGuild') }}
              <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </WowButton>
          </div>
        </form>
      </WowCard>

      <!-- Step 2 (player path): Create first character -->
      <WowCard v-if="currentStep === 2 && !isTenantPath" gold>
        <div class="text-center mb-6">
          <div class="w-16 h-16 rounded-full bg-accent-gold/10 border-2 border-accent-gold/30 flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-accent-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 class="wow-heading text-xl sm:text-2xl mb-2">{{ t('setup.characterTitle') }}</h2>
          <p class="text-sm text-text-muted">{{ t('setup.characterDesc') }}</p>
        </div>

        <form @submit.prevent="createFirstCharacter" class="space-y-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('setup.charName') }}</label>
            <input
              v-model="charForm.name"
              required
              :placeholder="t('setup.charNamePlaceholder')"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
            />
          </div>

          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('setup.charRealm') }}</label>
            <input
              v-model="charForm.realm"
              required
              :placeholder="t('setup.charRealmPlaceholder')"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
            />
          </div>

          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('setup.charClass') }}</label>
            <select
              v-model="charForm.class_name"
              required
              class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2.5 focus:border-border-gold outline-none"
            >
              <option value="">{{ t('setup.selectClass') }}</option>
              <option v-for="cls in wowClasses" :key="cls" :value="cls">{{ cls }}</option>
            </select>
          </div>

          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('setup.charRole') }}</label>
            <select
              v-model="charForm.role"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2.5 focus:border-border-gold outline-none"
            >
              <option value="">{{ t('setup.selectRole') }}</option>
              <option value="Tank">Tank</option>
              <option value="Healer">Healer</option>
              <option value="DPS">DPS</option>
            </select>
          </div>

          <p v-if="charError" class="text-sm text-red-400">{{ charError }}</p>

          <div class="flex justify-between pt-2">
            <WowButton variant="ghost" @click="currentStep = 1">
              <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
              </svg>
              {{ t('setup.back') }}
            </WowButton>
            <div class="flex gap-2">
              <WowButton variant="ghost" @click="skipAndFinish">
                {{ t('setup.skipForNow') }}
              </WowButton>
              <WowButton type="submit" :loading="saving">
                {{ t('setup.createCharacter') }}
              </WowButton>
            </div>
          </div>
        </form>
      </WowCard>

      <!-- Final step: Done! -->
      <WowCard v-if="currentStep === totalSteps + 1" gold>
        <div class="text-center py-4">
          <div class="w-20 h-20 rounded-full bg-green-900/30 border-2 border-green-500/30 flex items-center justify-center mx-auto mb-4">
            <svg class="w-10 h-10 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 class="wow-heading text-xl sm:text-2xl mb-2">{{ t('setup.doneTitle') }}</h2>
          <p class="text-sm text-text-muted mb-6">{{ t('setup.doneDesc') }}</p>
          <WowButton @click="goToDashboard">
            {{ t('setup.goToDashboard') }}
            <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </WowButton>
        </div>
      </WowCard>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import { useAuthStore } from '@/stores/auth'
import { useTenantStore } from '@/stores/tenant'
import { useToast } from '@/composables/useToast'
import * as tenantsApi from '@/api/tenants'
import * as guildsApi from '@/api/guilds'
import api from '@/api/index'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const tenantStore = useTenantStore()
const toast = useToast()

const currentStep = ref(1)
const saving = ref(false)

// Determine path: tenant creation or player-only
const isTenantPath = computed(() => route.query.mode === 'tenant')
const totalSteps = 2

const stepTitle = computed(() => {
  if (currentStep.value > totalSteps) return t('setup.complete')
  if (isTenantPath.value) {
    return currentStep.value === 1 ? t('setup.tenantStepName') : t('setup.guildStepName')
  }
  return currentStep.value === 1 ? t('setup.welcomeStepName') : t('setup.characterStepName')
})

// Tenant form
const tenantForm = ref({ name: '', description: '', slug: '' })
const tenantError = ref(null)

// Guild form
const guildForm = ref({ name: '', realm_name: '', faction: 'Alliance', timezone: 'Europe/Warsaw' })
const guildError = ref(null)

// Character form
const charForm = ref({ name: '', realm: '', class_name: '', role: '' })
const charError = ref(null)

const timezones = [
  'Europe/Warsaw', 'Europe/London', 'Europe/Berlin', 'Europe/Paris',
  'Europe/Moscow', 'America/New_York', 'America/Chicago',
  'America/Denver', 'America/Los_Angeles', 'Asia/Tokyo',
  'Asia/Shanghai', 'Australia/Sydney', 'Pacific/Auckland',
]

const wowClasses = [
  'Death Knight', 'Druid', 'Hunter', 'Mage', 'Paladin',
  'Priest', 'Rogue', 'Shaman', 'Warlock', 'Warrior',
]

async function saveTenantInfo() {
  saving.value = true
  tenantError.value = null
  try {
    if (tenantStore.activeTenantId) {
      await tenantsApi.updateTenant(tenantStore.activeTenantId, tenantForm.value)
    }
    currentStep.value = 2
  } catch (err) {
    tenantError.value = err?.response?.data?.error || err?.response?.data?.message || t('setup.tenantSaveError')
  } finally {
    saving.value = false
  }
}

async function createFirstGuild() {
  saving.value = true
  guildError.value = null
  try {
    await guildsApi.createGuild({
      name: guildForm.value.name,
      realm_name: guildForm.value.realm_name,
      faction: guildForm.value.faction,
      timezone: guildForm.value.timezone,
    })
    toast.success(t('setup.guildCreated'))
    currentStep.value = totalSteps + 1
  } catch (err) {
    guildError.value = err?.response?.data?.error || err?.response?.data?.message || t('setup.guildCreateError')
  } finally {
    saving.value = false
  }
}

async function createFirstCharacter() {
  saving.value = true
  charError.value = null
  try {
    await api.post('/characters', {
      name: charForm.value.name,
      realm: charForm.value.realm,
      class_name: charForm.value.class_name,
      role: charForm.value.role || undefined,
      is_main: true,
    })
    toast.success(t('setup.characterCreated'))
    currentStep.value = totalSteps + 1
  } catch (err) {
    charError.value = err?.response?.data?.error || err?.response?.data?.message || t('setup.characterCreateError')
  } finally {
    saving.value = false
  }
}

function skipAndFinish() {
  currentStep.value = totalSteps + 1
}

function goToDashboard() {
  router.push('/dashboard')
}

onMounted(async () => {
  // Pre-populate tenant form if tenant exists
  if (isTenantPath.value && tenantStore.activeTenantId) {
    try {
      const tenant = await tenantsApi.getTenant(tenantStore.activeTenantId)
      tenantForm.value.name = tenant.name || ''
      tenantForm.value.description = tenant.description || ''
      tenantForm.value.slug = tenant.slug || ''
    } catch {
      // ignore
    }
  }
})
</script>
