<template>
  <aside class="flex-col w-64 bg-[#0d111d] border-r border-[#2a3450] h-screen overflow-y-auto">
    <!-- Logo / Guild branding -->
    <div class="flex items-center gap-3 px-3 sm:px-5 py-3 sm:py-5 border-b border-[#2a3450]">
      <img
        :src="logoIcon"
        alt="WoW Calendar"
        class="w-9 h-9 rounded border border-border-gold"
      />
      <div>
        <div class="text-sm font-bold text-accent-gold font-wow leading-tight">{{ t('auth.appTitle') }}</div>
        <div class="text-xs text-text-muted">{{ t('auth.appSubtitle') }}</div>
      </div>
    </div>

    <!-- Tenant Switcher -->
    <TenantSwitcher />

    <!-- Guild Switcher -->
    <div class="px-4 py-3 border-b border-[#2a3450]">
      <label class="text-xs text-text-muted uppercase tracking-wider mb-1 block">{{ t('common.labels.guild') }}</label>
      <select
        :value="guildStore.currentGuild?.id ?? ''"
        class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-2 py-1.5 focus:border-border-gold outline-none"
        @change="onGuildChange"
      >
        <option v-if="!visibleGuilds.length" value="">{{ t('guild.noGuilds') }}</option>
        <!-- My created guilds -->
        <optgroup v-if="myCreatedGuilds.length" :label="t('guild.myCreatedGuilds')">
          <option
            v-for="g in myCreatedGuilds"
            :key="g.id"
            :value="g.id"
          >{{ g.name }} ({{ g.realm_name }})</option>
        </optgroup>
        <!-- Guilds I joined -->
        <optgroup v-if="joinedGuilds.length" :label="t('guild.joinedGuilds')">
          <option
            v-for="g in joinedGuilds"
            :key="g.id"
            :value="g.id"
          >{{ g.name }} ({{ g.realm_name }})</option>
        </optgroup>
        <!-- Flat list fallback (no role info available) -->
        <template v-if="!myCreatedGuilds.length && !joinedGuilds.length && visibleGuilds.length">
          <option
            v-for="g in visibleGuilds"
            :key="g.id"
            :value="g.id"
          >{{ g.name }} ({{ g.realm_name }})</option>
        </template>
      </select>

      <button
        v-if="canCreateGuild && hasTenant && !guildLimitReached"
        type="button"
        class="mt-2 w-full flex items-center justify-center gap-1 text-xs text-accent-gold hover:text-yellow-300 transition-colors py-1"
        @click="showCreateGuild = true; _initCreateGuild()"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        {{ t('guild.createGuild') }}
      </button>
      <RouterLink
        v-else-if="canCreateGuild && hasTenant && guildLimitReached"
        to="/tenant/settings"
        class="mt-2 w-full flex items-center justify-center gap-1 text-xs text-yellow-500/80 hover:text-yellow-400 transition-colors py-1"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
        </svg>
        {{ t('guild.guildLimitReached') }}
      </RouterLink>

      <!-- Upgrade to tenant (for users without a tenant) -->
      <button
        v-if="!hasTenant"
        type="button"
        class="mt-2 w-full flex items-center justify-center gap-1.5 text-xs text-accent-gold hover:text-yellow-300 bg-accent-gold/10 hover:bg-accent-gold/20 border border-accent-gold/30 rounded py-1.5 transition-colors"
        :disabled="upgradingToTenant"
        @click="handleUpgradeToTenant"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
        </svg>
        {{ upgradingToTenant ? t('common.labels.loading') : t('tenant.upgradeToTenant') }}
      </button>
    </div>

    <!-- Navigation links -->
    <nav class="flex-1 px-3 py-4 space-y-0.5">
      <template v-for="group in navGroups" :key="group.label">
        <div class="text-xs text-text-muted uppercase tracking-wider px-2 py-2 mt-2">{{ group.label }}</div>
        <RouterLink
          v-for="item in group.items"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-text-muted transition-colors hover:text-text-primary hover:bg-bg-tertiary"
          active-class="bg-bg-tertiary text-accent-gold border-l-2 border-accent-gold"
          @click="uiStore.closeSidebar()"
        >
          <component :is="item.icon" class="w-4 h-4 flex-shrink-0" />
          {{ item.label }}
        </RouterLink>
      </template>
    </nav>

    <!-- User info at bottom -->
    <div class="px-4 py-4 border-t border-[#2a3450]">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-full bg-bg-tertiary border border-border-default flex items-center justify-center text-xs text-accent-gold font-bold uppercase">
          {{ userInitial }}
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-sm text-text-primary truncate">{{ authStore.user?.username ?? t('common.labels.unknown') }}</div>
          <div class="text-xs text-text-muted truncate">{{ authStore.user?.email ?? '' }}</div>
        </div>
      </div>
    </div>
  </aside>

  <!-- Create Guild Modal -->
  <Teleport to="body">
    <div v-if="showCreateGuild" class="fixed inset-0 z-[100] flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60" @click="showCreateGuild = false" />
      <div class="relative bg-bg-secondary border border-border-default rounded-lg shadow-xl w-full max-w-md mx-4 p-6 z-10">
        <h3 class="wow-heading text-lg mb-4">{{ t('guild.createGuild') }}</h3>

        <!-- Step 1: Guild details & armory lookup -->
        <div v-if="!guildLookupDone" class="space-y-4">
          <p class="text-sm text-text-muted">{{ t('guild.createHelp') }}</p>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.guildName') }}</label>
            <input v-model="newGuild.name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" :placeholder="t('guild.guildNamePlaceholder')" @keydown.enter.prevent="canDoLookup ? lookupGuild() : enterManually()" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('guild.armoryUrl') }}</label>
            <input v-model="newGuild.armory_url" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" :placeholder="t('guild.armoryUrlPlaceholder')" @blur="onArmoryUrlChange" />
            <p class="text-xs text-text-muted mt-1">{{ t('guild.armoryUrlHelp') }}</p>
          </div>
          <!-- Realm discovery status -->
          <div v-if="newGuild.armory_url.trim()">
            <div v-if="discoveringRealms" class="flex items-center gap-2 text-xs text-text-muted">
              <div class="w-3 h-3 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin" />
              {{ t('guild.discoveringRealms') }}
            </div>
            <div v-else-if="discoveredRealms.length > 0" class="text-xs text-green-400">
              ✓ {{ t('guild.realmsDiscovered', { count: discoveredRealms.length }) }}
            </div>
          </div>
          <!-- Realm hint input (optional - shown when no realms auto-discovered, helps narrow search) -->
          <div v-if="newGuild.armory_url.trim() && !discoveringRealms && discoveredRealms.length === 0">
            <label class="block text-xs text-text-muted mb-1">{{ t('guild.realmHint') }}</label>
            <input v-model="lookupRealm" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" :placeholder="t('guild.realmHintPlaceholder')" @keydown.enter.prevent="lookupGuild()" />
            <p class="text-xs text-text-muted mt-1">{{ t('guild.realmHintHelp') }}</p>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('guild.expansion') }}</label>
            <select v-model="newGuild.expansion_id" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option v-for="exp in sortedExpansions" :key="exp.id" :value="exp.id">{{ exp.name }}</option>
            </select>
            <p class="text-xs text-text-muted mt-1">{{ t('guild.expansionHelp') }}</p>
            <div v-if="newGuild.expansion_id && sortedExpansions.length > 1" class="mt-2 flex flex-wrap gap-1">
              <span v-for="exp in includedExpansions" :key="exp.id"
                class="px-2 py-0.5 rounded text-xs font-medium bg-green-900/30 text-green-300 border border-green-700/50">
                ✓ {{ exp.name }}
              </span>
            </div>
          </div>
          <div v-if="guildLookupError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ guildLookupError }}</div>
          <div v-if="guildLookupNotFound" class="p-3 rounded bg-yellow-900/30 border border-yellow-600 text-yellow-300 text-sm">
            {{ t('guild.notFoundOnArmory') }}
          </div>
          <!-- Multiple realm matches -->
          <div v-if="guildLookupMatches.length > 1" class="space-y-2">
            <p class="text-sm text-green-300">{{ t('guild.foundOnRealms', { count: guildLookupMatches.length }) }}</p>
            <div v-for="m in guildLookupMatches" :key="m.realm" class="flex items-center gap-3 p-3 rounded border text-sm cursor-pointer transition-colors"
              :class="m.alreadyAdded ? 'border-border-default bg-bg-tertiary opacity-60 cursor-not-allowed' : 'border-border-default bg-bg-tertiary hover:border-border-gold'"
              @click="!m.alreadyAdded && selectGuildMatch(m)"
            >
              <div class="flex-1">
                <span class="text-text-primary font-medium">{{ m.realm }}</span>
                <span v-if="m.faction" class="ml-2 px-2 py-0.5 rounded text-xs font-medium"
                  :class="m.faction === 'Alliance' ? 'bg-blue-900/50 text-blue-300 border border-blue-600' : 'bg-red-900/50 text-red-300 border border-red-600'"
                >{{ m.faction }}</span>
                <span class="text-text-muted text-xs ml-2">{{ t('guild.memberCount', { count: m.member_count ?? 0 }) }}</span>
              </div>
              <span v-if="m.alreadyAdded" class="text-xs text-yellow-400">{{ t('guild.alreadyAdded') }}</span>
              <span v-else class="text-xs text-accent-gold">{{ t('guild.select') }}</span>
            </div>
          </div>
          <div class="flex justify-end gap-3">
            <button type="button" class="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors" @click="showCreateGuild = false">{{ t('common.buttons.cancel') }}</button>
            <button v-if="guildLookupNotFound" type="button" class="px-4 py-2 text-sm bg-bg-tertiary text-text-muted border border-border-default rounded hover:border-border-gold hover:text-text-primary transition-colors" @click="enterManually">{{ t('guild.enterManually') }}</button>
            <button v-if="canDoLookup" type="button" :disabled="lookingUpGuild || !newGuild.name.trim()" class="px-4 py-2 text-sm bg-accent-gold/20 text-accent-gold border border-accent-gold/50 rounded hover:bg-accent-gold/30 transition-colors disabled:opacity-50" @click="lookupGuild">
              {{ lookingUpGuild ? t('common.labels.searching') : t('guild.searchOnArmory') }}
            </button>
            <button v-else type="button" :disabled="!newGuild.name.trim()" class="px-4 py-2 text-sm bg-accent-gold/20 text-accent-gold border border-accent-gold/50 rounded hover:bg-accent-gold/30 transition-colors disabled:opacity-50" @click="enterManually">
              {{ t('common.buttons.continue') }}
            </button>
          </div>
        </div>

        <!-- Step 2: Confirm found guild or manual form -->
        <form v-else @submit.prevent="doCreateGuild" class="space-y-4">
          <!-- Show armory match info -->
          <div v-if="guildLookupMatch" class="p-3 rounded bg-green-900/20 border border-green-700 text-sm">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-green-300 font-medium">✓ {{ t('guild.foundOnArmory') }}</span>
              <span v-if="guildLookupMatch.faction" class="px-2 py-0.5 rounded text-xs font-medium"
                :class="guildLookupMatch.faction === 'Alliance' ? 'bg-blue-900/50 text-blue-300 border border-blue-600' : 'bg-red-900/50 text-red-300 border border-red-600'"
              >{{ guildLookupMatch.faction }}</span>
            </div>
            <span class="text-text-muted text-xs">{{ t('guild.membersOnRealm', { count: guildLookupMatch.member_count ?? 0, realm: newGuild.realm_name }) }}</span>
          </div>
          <div v-if="guildLookupMatch?.alreadyAdded" class="p-3 rounded bg-yellow-900/20 border border-yellow-700 text-sm text-yellow-300">
            ⚠ {{ t('guild.alreadyAddedWarning') }}
          </div>
          <div v-if="guildManualMode" class="p-3 rounded bg-yellow-900/20 border border-yellow-700 text-sm text-yellow-300">
            {{ t('guild.manualEntryInfo') }}
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.guildName') }}</label>
            <input v-model="newGuild.name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" :readonly="!!guildLookupMatch" :class="{ 'opacity-70': !!guildLookupMatch }" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.realmRequired') }}</label>
            <select v-if="selectedProviderRealms.length" v-model="newGuild.realm_name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" :disabled="!!guildLookupMatch" :class="{ 'opacity-70': !!guildLookupMatch }">
              <option value="">{{ t('common.fields.selectRealm') }}</option>
              <option v-for="r in selectedProviderRealms" :key="r" :value="r">{{ r }}</option>
            </select>
            <input v-else v-model="newGuild.realm_name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" :placeholder="t('guild.realmPlaceholder')" :readonly="!!guildLookupMatch" :class="{ 'opacity-70': !!guildLookupMatch }" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.faction') }}</label>
            <select v-model="newGuild.faction" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" :disabled="!!guildLookupMatch" :class="{ 'opacity-70': !!guildLookupMatch }">
              <option value="">{{ t('guild.selectFaction') }}</option>
              <option value="Alliance">Alliance</option>
              <option value="Horde">Horde</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.timezone') }}</label>
            <select v-model="newGuild.timezone" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option v-for="tz in GUILD_TIMEZONES" :key="tz" :value="tz">{{ tz }}</option>
            </select>
          </div>
          <div v-if="createGuildError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ createGuildError }}</div>
          <div class="flex justify-end gap-3">
            <button type="button" class="px-4 py-2 text-sm text-text-muted hover:text-text-primary transition-colors" @click="resetCreateGuild">{{ t('common.buttons.back') }}</button>
            <button type="submit" :disabled="creatingGuild || guildLookupMatch?.alreadyAdded" class="px-4 py-2 text-sm bg-accent-gold/20 text-accent-gold border border-accent-gold/50 rounded hover:bg-accent-gold/30 transition-colors disabled:opacity-50">
              {{ creatingGuild ? t('common.labels.creating') : t('guild.createGuild') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, h, ref, reactive, onMounted, onUnmounted } from 'vue'
import { RouterLink, useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useGuildStore } from '@/stores/guild'
import { useTenantStore } from '@/stores/tenant'
import { useUiStore } from '@/stores/ui'
import { useToast } from '@/composables/useToast'
import { useConstantsStore } from '@/stores/constants'
import { usePermissions } from '@/composables/usePermissions'
import { useWowIcons } from '@/composables/useWowIcons'
import { useSocket } from '@/composables/useSocket'
import * as guildsApi from '@/api/guilds'
import * as armoryLookupApi from '@/api/armory_lookup'
import * as tenantsApi from '@/api/tenants'
import TenantSwitcher from '@/components/layout/TenantSwitcher.vue'

const { t } = useI18n()

const { getRaidIcon } = useWowIcons()
const logoIcon = getRaidIcon('icc')
const { on, off } = useSocket()

const authStore = useAuthStore()
const guildStore = useGuildStore()
const tenantStore = useTenantStore()
const uiStore = useUiStore()
const toast = useToast()
const constantsStore = useConstantsStore()
const router = useRouter()
const route = useRoute()
const permissions = usePermissions()

const canManageGuild = computed(() => permissions.can('create_events'))
const canCreateGuild = computed(() => permissions.canTenant('create_guild'))
const hasTenant = computed(() => !!tenantStore.activeTenantId)

// Check if tenant guild limit is reached
const guildLimitReached = computed(() => {
  const tenant = tenantStore.activeTenant
  if (!tenant || !tenant.max_guilds) return false
  return guildStore.guilds.length >= tenant.max_guilds
})

// Show all guilds where user is a member; filter out hidden guilds from non-members
const visibleGuilds = computed(() => {
  return guildStore.guilds.filter(g => g.visibility !== 'hidden')
})

// Separate guilds into "My created" vs "Joined"
const myCreatedGuilds = computed(() => {
  const userId = authStore.user?.id
  if (!userId) return []
  return visibleGuilds.value.filter(g =>
    g.created_by === userId || g.my_role === 'owner'
  )
})

const joinedGuilds = computed(() => {
  const userId = authStore.user?.id
  if (!userId) return []
  return visibleGuilds.value.filter(g =>
    g.created_by !== userId && g.my_role !== 'owner'
  )
})

const upgradingToTenant = ref(false)

const userInitial = computed(() => authStore.user?.username?.[0]?.toUpperCase() ?? '?')

// Load guilds on mount and listen for real-time updates
onMounted(() => {
  on('guilds_changed', handleGuildsChanged)
  on('guild_changed', handleGuildChanged)
})

onUnmounted(() => {
  off('guilds_changed', handleGuildsChanged)
  off('guild_changed', handleGuildChanged)
})

function handleGuildsChanged() {
  guildStore.fetchGuilds()
}

function handleGuildChanged() {
  guildStore.fetchGuilds()
}

async function handleUpgradeToTenant() {
  upgradingToTenant.value = true
  try {
    await tenantsApi.upgradeToTenant()
    // Refresh tenants and user data
    await tenantStore.fetchTenants()
    // Set the new tenant as active
    if (tenantStore.tenants.length > 0) {
      const ownedTenant = tenantStore.tenants.find(t => t.owner_id === authStore.user?.id)
      if (ownedTenant) {
        await tenantStore.switchTenant(ownedTenant.id)
      }
    }
    // Re-fetch user to get updated active_tenant_id
    await authStore.fetchMe()
    toast.success(t('tenant.upgradeSuccess'))
  } catch (err) {
    toast.error(err?.response?.data?.error || t('tenant.upgradeFailed'))
  } finally {
    upgradingToTenant.value = false
  }
}

// Simple SVG icon components using render functions
const icons = {
  dashboard: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' })
  ]),
  calendar: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' })
  ]),
  chars: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' })
  ]),
  attendance: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4' })
  ]),
  settings: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' }),
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z' })
  ]),
  raids: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' })
  ]),
  templates: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z' })
  ]),
  series: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15' })
  ]),
  profile: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z' })
  ]),
  admin: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z' })
  ]),
  system: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01' })
  ]),
  search: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
    h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z' })
  ])
}

const hasGuildAdminAccess = computed(() =>
  permissions.can('update_member_roles') ||
  permissions.can('manage_guild_roles') ||
  permissions.can('update_guild_settings')
)

const isGlobalAdmin = computed(() => !!authStore.user?.is_admin)

const navGroups = computed(() => {
  const groups = [
    {
      label: t('nav.overview'),
      items: [
        { label: t('common.labels.dashboard'), to: '/dashboard', icon: icons.dashboard },
        { label: t('common.labels.calendar'), to: '/calendar', icon: icons.calendar },
        { label: t('common.labels.characters'), to: '/characters', icon: icons.chars },
        { label: t('common.labels.attendance'), to: '/attendance', icon: icons.attendance }
      ]
    }
  ]

  // Guild management visible to users with relevant permissions (requires a guild)
  if ((canManageGuild.value || hasGuildAdminAccess.value) && guildStore.currentGuild) {
    const guildItems = []
    if (canManageGuild.value) {
      guildItems.push(
        { label: t('nav.raidDefinitions'), to: '/guild/raid-definitions', icon: icons.raids },
        { label: t('nav.raidPlanning'), to: '/guild/templates', icon: icons.templates }
      )
    }
    if (hasGuildAdminAccess.value) {
      guildItems.push({ label: t('nav.guildAdmin'), to: '/admin', icon: icons.admin })
    }
    groups.push({
      label: t('nav.guildManagement'),
      items: guildItems
    })
  }

  // Global admin section (only for site admins)
  if (isGlobalAdmin.value) {
    groups.push({
      label: t('nav.administration'),
      items: [
        { label: t('nav.globalAdmin'), to: '/admin/global', icon: icons.system }
      ]
    })
  }

  groups.push({
    label: t('nav.account'),
    items: [
      { label: t('nav.profile'), to: '/profile', icon: icons.profile }
    ]
  })

  return groups
})

function onGuildChange(e) {
  const id = e.target.value
  const guild = guildStore.guilds.find(g => String(g.id) === String(id))
  if (guild) {
    guildStore.setCurrentGuild(guild)
    // Navigate to calendar when switching guilds from a guild-specific view (e.g., raid detail)
    if (route.path.startsWith('/raids/') || route.path.startsWith('/events/')) {
      router.push('/calendar')
    }
  }
}

// Create Guild
const showCreateGuild = ref(false)
const creatingGuild = ref(false)
const createGuildError = ref(null)
const lookupRealm = ref('')
const newGuild = reactive({ name: '', realm_name: '', faction: '', timezone: 'Europe/Warsaw', armory_url: '', expansion_id: null })

const GUILD_TIMEZONES = [
  'Europe/Warsaw', 'Europe/London', 'Europe/Paris', 'Europe/Berlin',
  'Europe/Madrid', 'Europe/Rome', 'Europe/Amsterdam', 'Europe/Brussels',
  'Europe/Vienna', 'Europe/Prague', 'Europe/Budapest', 'Europe/Bucharest',
  'Europe/Sofia', 'Europe/Athens', 'Europe/Helsinki', 'Europe/Stockholm',
  'Europe/Oslo', 'Europe/Copenhagen', 'Europe/Lisbon', 'Europe/Dublin',
  'Europe/Moscow', 'Europe/Kiev', 'Europe/Istanbul',
  'US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific',
  'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
  'America/Sao_Paulo', 'America/Argentina/Buenos_Aires',
  'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Seoul', 'Asia/Singapore',
  'Asia/Kolkata', 'Asia/Dubai',
  'Australia/Sydney', 'Australia/Melbourne', 'Pacific/Auckland',
  'UTC',
]

// Auto-detect armory provider from the URL
const detectedProvider = computed(() => {
  const url = newGuild.armory_url.trim().toLowerCase()
  if (!url) return null
  for (const provider of Object.keys(constantsStore.providerRealms)) {
    if (url.includes(provider)) return provider
  }
  return null
})

// Realms for the detected provider (from constants store)
const detectedProviderRealms = computed(() => {
  if (!detectedProvider.value) return []
  return constantsStore.providerRealms[detectedProvider.value] || []
})

// Realms for step 2 (uses discovered realms, then detected provider, then empty for manual)
const selectedProviderRealms = computed(() => {
  if (discoveredRealms.value.length > 0) return discoveredRealms.value
  return detectedProviderRealms.value
})

// Dynamic realm discovery from armory URL
const discoveringRealms = ref(false)
const discoveredRealms = ref([])
let _lastDiscoveredUrl = ''

async function onArmoryUrlChange() {
  const url = newGuild.armory_url.trim()
  if (!url || url === _lastDiscoveredUrl) return
  _lastDiscoveredUrl = url
  discoveringRealms.value = true
  discoveredRealms.value = []
  try {
    const result = await armoryLookupApi.discoverRealms(url)
    discoveredRealms.value = result.realms || []
  } catch {
    discoveredRealms.value = []
  } finally {
    discoveringRealms.value = false
  }
}

// Can perform armory lookup: armory URL + either discovered/known realms or manual realm input
const canDoLookup = computed(() => {
  const url = newGuild.armory_url.trim()
  if (!url) return false
  // Always allow lookup when armory URL is present — the backend will
  // discover realms automatically or use realm hints
  return true
})

// Expansions sorted by sort_order descending (highest first)
const sortedExpansions = computed(() => {
  return [...constantsStore.expansions].sort((a, b) => (b.sort_order ?? 0) - (a.sort_order ?? 0))
})

// Expansions that will be included when the selected expansion is chosen
const includedExpansions = computed(() => {
  const selected = sortedExpansions.value.find(e => e.id === newGuild.expansion_id)
  if (!selected) return []
  const selectedOrder = selected.sort_order ?? 0
  return [...constantsStore.expansions]
    .filter(e => (e.sort_order ?? 0) <= selectedOrder)
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
})

// Set default expansion to highest sort_order
const _initCreateGuild = () => {
  if (sortedExpansions.value.length > 0 && !newGuild.expansion_id) {
    newGuild.expansion_id = sortedExpansions.value[0].id
  }
}

// Guild armory lookup state
const lookingUpGuild = ref(false)
const guildLookupDone = ref(false)
const guildLookupError = ref(null)
const guildLookupNotFound = ref(false)
const guildLookupMatch = ref(null)
const guildLookupMatches = ref([])  // all realm matches
const guildManualMode = ref(false)

function resetCreateGuild() {
  guildLookupDone.value = false
  guildLookupError.value = null
  guildLookupNotFound.value = false
  guildLookupMatch.value = null
  guildLookupMatches.value = []
  guildManualMode.value = false
  createGuildError.value = null
  lookupRealm.value = ''
  discoveredRealms.value = []
  _lastDiscoveredUrl = ''
  newGuild.realm_name = ''
  newGuild.faction = ''
}

function enterManually() {
  guildLookupDone.value = true
  guildLookupMatch.value = null
  guildManualMode.value = true
  guildLookupNotFound.value = false
  guildLookupError.value = null
}

async function lookupGuild() {
  const name = newGuild.name.trim()
  if (!name) return

  lookingUpGuild.value = true
  guildLookupError.value = null
  guildLookupNotFound.value = false
  guildLookupMatch.value = null
  guildLookupMatches.value = []

  const armoryUrl = newGuild.armory_url.trim()
  if (!armoryUrl) {
    lookingUpGuild.value = false
    guildLookupError.value = t('guild.armoryUrlRequired')
    return
  }

  // Collect realm hints from manual input and detected provider realms
  const realmHints = []
  const manualRealm = lookupRealm.value.trim()
  if (manualRealm) realmHints.push(manualRealm)
  if (detectedProviderRealms.value.length > 0) {
    realmHints.push(...detectedProviderRealms.value)
  }

  try {
    // Use the unified search-guild endpoint which discovers realms + searches
    const result = await armoryLookupApi.searchGuild(armoryUrl, name, realmHints)
    const serverMatches = result.matches || []

    // Mark already-added guilds
    const matches = serverMatches.map(m => ({
      ...m,
      alreadyAdded: guildStore.allGuilds.some(
        g => g.name.toLowerCase() === name.toLowerCase() && g.realm_name.toLowerCase() === m.realm.toLowerCase()
      )
    }))

    lookingUpGuild.value = false

    if (matches.length === 0) {
      guildLookupNotFound.value = true
      // If no realms were available and no manual hint given, prompt for realm
      if (!result.realms_available && !manualRealm) {
        guildLookupError.value = t('guild.noRealmsToSearch')
      }
      return
    }

    guildLookupMatches.value = matches

    if (matches.length === 1) {
      selectGuildMatch(matches[0])
    }
  } catch (err) {
    lookingUpGuild.value = false
    guildLookupError.value = err?.response?.data?.error ?? err?.response?.data?.message ?? t('guild.toasts.failedToSearchArmory')
  }
}

function selectGuildMatch(match) {
  guildLookupMatch.value = match
  newGuild.realm_name = match.realm
  newGuild.faction = match.faction || ''
  guildLookupDone.value = true
}

async function doCreateGuild() {
  createGuildError.value = null
  creatingGuild.value = true
  try {
    const provider = detectedProvider.value || ''
    const guild = await guildsApi.createGuild({
      name: newGuild.name,
      realm_name: newGuild.realm_name,
      faction: newGuild.faction || null,
      armory_source: !!guildLookupMatch.value,
      armory_provider: provider,
      armory_url: newGuild.armory_url.trim() || null,
      expansion_id: newGuild.expansion_id,
      timezone: newGuild.timezone,
    })
    await guildStore.fetchGuilds()
    guildStore.setCurrentGuild(guild)
    showCreateGuild.value = false
    newGuild.name = ''
    newGuild.realm_name = ''
    newGuild.faction = ''
    newGuild.timezone = 'Europe/Warsaw'
    newGuild.armory_url = ''
    newGuild.expansion_id = sortedExpansions.value[0]?.id ?? null
    guildLookupDone.value = false
    guildLookupMatch.value = null
    guildLookupMatches.value = []
    guildManualMode.value = false
    guildLookupError.value = null
    guildLookupNotFound.value = false
    toast.success(t('guild.guildCreated'))
  } catch (err) {
    createGuildError.value = err?.response?.data?.message ?? t('guild.toasts.failedToCreate')
  } finally {
    creatingGuild.value = false
  }
}
</script>
