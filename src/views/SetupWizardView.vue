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

          <div class="flex justify-between pt-2">
            <WowButton variant="ghost" class="text-red-400 hover:text-red-300" :loading="cancellingSetup" @click="cancelTenantSetup">
              <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
              {{ t('setup.cancelSetup') }}
            </WowButton>
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

      <!-- Step 2 (tenant path): Create first guild — matches manual guild creation flow -->
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

        <!-- Guild creation step 1: Armory lookup -->
        <div v-if="!guildLookupDone" class="space-y-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.guildName') }}</label>
            <input
              v-model="guildForm.name"
              required
              :placeholder="t('setup.guildNamePlaceholder')"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
              @keydown.enter.prevent="canDoLookup ? lookupGuild() : enterManualGuild()"
            />
          </div>

          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('guild.armoryUrl') }}</label>
            <input
              v-model="guildForm.armory_url"
              :placeholder="t('guild.armoryUrlPlaceholder')"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
              @blur="onArmoryUrlChange"
            />
            <p class="text-xs text-text-muted mt-1">{{ t('guild.armoryUrlHelp') }}</p>
          </div>

          <!-- Realm discovery status -->
          <div v-if="guildForm.armory_url.trim()">
            <div v-if="discoveringRealms" class="flex items-center gap-2 text-xs text-text-muted">
              <div class="w-3 h-3 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin" />
              {{ t('guild.discoveringRealms') }}
            </div>
            <div v-else-if="discoveredRealms.length > 0" class="text-xs text-green-400">
              ✓ {{ t('guild.realmsDiscovered', { count: discoveredRealms.length }) }}
            </div>
          </div>

          <!-- Realm hint input -->
          <div v-if="guildForm.armory_url.trim() && discoveredRealms.length === 0">
            <label class="block text-xs text-text-muted mb-1">{{ t('guild.realmHint') }}</label>
            <input
              v-model="lookupRealm"
              :placeholder="t('guild.realmHintPlaceholder')"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
              @keydown.enter.prevent="lookupGuild()"
            />
            <p class="text-xs text-text-muted mt-1">{{ t('guild.realmHintHelp') }}</p>
          </div>

          <!-- Expansion selector -->
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('guild.expansion') }}</label>
            <select
              v-model="guildForm.expansion_id"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2.5 focus:border-border-gold outline-none"
            >
              <option v-for="exp in sortedExpansions" :key="exp.id" :value="exp.id">{{ exp.name }}</option>
            </select>
            <p class="text-xs text-text-muted mt-1">{{ t('guild.expansionHelp') }}</p>
            <div v-if="guildForm.expansion_id && sortedExpansions.length > 1" class="mt-2 flex flex-wrap gap-1">
              <span v-for="exp in includedExpansions" :key="exp.id"
                class="px-2 py-0.5 rounded text-xs font-medium bg-green-900/30 text-green-300 border border-green-700/50">
                ✓ {{ exp.name }}
              </span>
            </div>
          </div>

          <!-- Lookup errors -->
          <div v-if="guildLookupError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ guildLookupError }}</div>
          <div v-if="guildLookupNotFound" class="p-3 rounded bg-yellow-900/30 border border-yellow-600 text-yellow-300 text-sm">
            {{ t('guild.notFoundOnArmory') }}
          </div>

          <!-- Multiple realm matches -->
          <div v-if="guildLookupMatches.length > 1" class="space-y-2">
            <p class="text-sm text-green-300">{{ t('guild.foundOnRealms', { count: guildLookupMatches.length }) }}</p>
            <div v-for="m in guildLookupMatches" :key="m.realm"
              class="flex items-center gap-3 p-3 rounded border text-sm cursor-pointer transition-colors"
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

          <p v-if="guildError" class="text-sm text-red-400">{{ guildError }}</p>

          <div class="flex justify-between pt-2">
            <WowButton variant="ghost" @click="currentStep = 1">
              <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
              </svg>
              {{ t('setup.back') }}
            </WowButton>
            <div class="flex gap-2">
              <WowButton v-if="guildLookupNotFound" variant="ghost" @click="enterManualGuild">
                {{ t('guild.enterManually') }}
              </WowButton>
              <WowButton v-if="canDoLookup" :loading="lookingUpGuild" :disabled="!guildForm.name.trim()" @click="lookupGuild">
                {{ lookingUpGuild ? t('common.labels.searching') : t('guild.searchOnArmory') }}
              </WowButton>
              <WowButton v-else :disabled="!guildForm.name.trim()" @click="enterManualGuild">
                {{ t('common.buttons.continue') }}
              </WowButton>
            </div>
          </div>
        </div>

        <!-- Guild creation step 2: Confirm found guild or manual entry -->
        <form v-else @submit.prevent="createFirstGuild" class="space-y-4">
          <!-- Armory match info -->
          <div v-if="guildLookupMatch" class="p-3 rounded bg-green-900/20 border border-green-700 text-sm">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-green-300 font-medium">✓ {{ t('guild.foundOnArmory') }}</span>
              <span v-if="guildLookupMatch.faction" class="px-2 py-0.5 rounded text-xs font-medium"
                :class="guildLookupMatch.faction === 'Alliance' ? 'bg-blue-900/50 text-blue-300 border border-blue-600' : 'bg-red-900/50 text-red-300 border border-red-600'"
              >{{ guildLookupMatch.faction }}</span>
            </div>
            <span class="text-text-muted text-xs">{{ t('guild.membersOnRealm', { count: guildLookupMatch.member_count ?? 0, realm: guildForm.realm_name }) }}</span>
          </div>
          <div v-if="guildManualMode" class="p-3 rounded bg-yellow-900/20 border border-yellow-700 text-sm text-yellow-300">
            {{ t('guild.manualEntryInfo') }}
          </div>

          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.guildName') }}</label>
            <input
              v-model="guildForm.name"
              required
              :readonly="!!guildLookupMatch"
              :class="{ 'opacity-70': !!guildLookupMatch }"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
            />
          </div>

          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.realmRequired') }}</label>
            <select v-if="selectedProviderRealms.length"
              v-model="guildForm.realm_name"
              required
              :disabled="!!guildLookupMatch"
              :class="{ 'opacity-70': !!guildLookupMatch }"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none"
            >
              <option value="">{{ t('common.fields.selectRealm') }}</option>
              <option v-for="r in selectedProviderRealms" :key="r" :value="r">{{ r }}</option>
            </select>
            <input v-else
              v-model="guildForm.realm_name"
              required
              :readonly="!!guildLookupMatch"
              :class="{ 'opacity-70': !!guildLookupMatch }"
              :placeholder="t('guild.realmPlaceholder')"
              class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.faction') }}</label>
              <select
                v-model="guildForm.faction"
                :disabled="!!guildLookupMatch"
                :class="{ 'opacity-70': !!guildLookupMatch }"
                class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2.5 focus:border-border-gold outline-none"
              >
                <option value="">{{ t('guild.selectFaction') }}</option>
                <option value="Alliance">Alliance</option>
                <option value="Horde">Horde</option>
              </select>
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.timezone') }}</label>
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
            <WowButton variant="ghost" @click="resetGuildLookup">
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

      <!-- Step 2 (player path): Create first character — matches manual character creation flow -->
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
          <!-- Armory import section (only before manual entry or lookup found) -->
          <div v-if="!charManualEntry && charLookupResult !== 'found'" class="p-4 rounded bg-accent-gold/5 border border-accent-gold/30 space-y-3">
            <div class="text-sm font-semibold text-accent-gold">{{ t('characters.importFromArmory') }}</div>
            <p class="text-xs text-text-muted">{{ t('characters.importHelp') }}</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-xs text-text-muted mb-1">{{ t('characters.nameRequired') }}</label>
                <input v-model="charForm.name" :placeholder="t('characters.characterName')"
                  class="w-full bg-bg-secondary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none" />
              </div>
              <div>
                <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.realmRequired') }}</label>
                <input v-model="charForm.realm" :placeholder="t('setup.charRealmPlaceholder')"
                  class="w-full bg-bg-secondary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none" />
              </div>
            </div>
            <div class="flex items-center gap-3">
              <WowButton variant="secondary" class="text-xs py-1.5" :loading="charLookingUp" :disabled="!charForm.name || !charForm.realm" @click="lookupCharFromArmory">
                {{ t('characters.lookupOnArmory') }}
              </WowButton>
              <span v-if="charLookupResult === 'not_found'" class="text-xs text-yellow-400">{{ t('characters.notFoundOnArmory') }}</span>
            </div>
          </div>

          <!-- Switch to manual entry link -->
          <div v-if="!charManualEntry && charLookupResult !== 'found'" class="text-center">
            <button type="button" class="text-xs text-text-muted hover:text-accent-gold transition-colors underline" @click="charManualEntry = true">
              {{ t('characters.fillManually') }}
            </button>
          </div>

          <!-- Manual form fields (shown after armory lookup or manual choice) -->
          <template v-if="charManualEntry || charLookupResult === 'found'">
            <div v-if="charLookupResult === 'found'" class="p-3 rounded bg-green-900/20 border border-green-700 text-sm text-green-300">
              ✓ {{ t('characters.foundOnArmory') }}
            </div>

            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('characters.nameRequired') }}</label>
              <input v-model="charForm.name" required :placeholder="t('setup.charNamePlaceholder')" :disabled="charLookupResult === 'found'"
                class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none disabled:opacity-50 disabled:cursor-not-allowed placeholder:text-text-muted/50" />
            </div>

            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.realmRequired') }}</label>
              <input v-model="charForm.realm" required :placeholder="t('setup.charRealmPlaceholder')" :disabled="charLookupResult === 'found'"
                class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2.5 text-sm focus:border-border-gold outline-none disabled:opacity-50 disabled:cursor-not-allowed placeholder:text-text-muted/50" />
            </div>

            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('setup.charClass') }}</label>
              <select v-model="charForm.class_name" required :disabled="charLookupResult === 'found'"
                class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2.5 focus:border-border-gold outline-none disabled:opacity-50 disabled:cursor-not-allowed">
                <option value="">{{ t('setup.selectClass') }}</option>
                <option v-for="cls in wowClasses" :key="cls" :value="cls">{{ cls }}</option>
              </select>
            </div>

            <div>
              <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.role') }}</label>
              <select v-model="charForm.role"
                class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2.5 focus:border-border-gold outline-none">
                <option value="">{{ t('setup.selectRole') }}</option>
                <option value="Tank">Tank</option>
                <option value="Healer">Healer</option>
                <option value="DPS">DPS</option>
              </select>
            </div>

            <div v-if="charFilteredSpecs.length > 0">
              <label class="block text-xs text-text-muted mb-1">{{ t('characters.spec') }}</label>
              <select v-model="charForm.spec" :disabled="charLookupResult === 'found'"
                class="w-full bg-bg-tertiary border border-border-default text-text-primary text-sm rounded px-3 py-2.5 focus:border-border-gold outline-none disabled:opacity-50 disabled:cursor-not-allowed">
                <option value="">{{ t('characters.selectSpec') }}</option>
                <option v-for="s in charFilteredSpecs" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>
          </template>

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
              <WowButton v-if="charManualEntry || charLookupResult === 'found'" type="submit" :loading="saving">
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

    <!-- Cancel tenant setup confirmation modal -->
    <WowModal v-model="showCancelConfirm" :title="t('setup.cancelSetupTitle')" size="sm">
      <div class="space-y-3">
        <p class="text-text-muted text-sm">{{ t('setup.cancelSetupWarning') }}</p>
        <div class="p-3 rounded bg-red-900/20 border border-red-600/40 text-red-300 text-xs flex items-start gap-2">
          <svg class="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
          {{ t('setup.cancelSetupDetail') }}
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showCancelConfirm = false">{{ t('setup.continueSetup') }}</WowButton>
          <WowButton variant="danger" :loading="cancellingSetup" @click="confirmCancelSetup">{{ t('setup.confirmCancel') }}</WowButton>
        </div>
      </template>
    </WowModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import { useAuthStore } from '@/stores/auth'
import { useTenantStore } from '@/stores/tenant'
import { useGuildStore } from '@/stores/guild'
import { useConstantsStore } from '@/stores/constants'
import { useToast } from '@/composables/useToast'
import { useExpansionData } from '@/composables/useExpansionData'
import * as tenantsApi from '@/api/tenants'
import * as guildsApi from '@/api/guilds'
import * as armoryLookupApi from '@/api/armory_lookup'
import api from '@/api/index'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const tenantStore = useTenantStore()
const guildStore = useGuildStore()
const constantsStore = useConstantsStore()
const toast = useToast()
const { classSpecs: systemSpecs } = useExpansionData()

const currentStep = ref(1)
const saving = ref(false)
const showCancelConfirm = ref(false)
const cancellingSetup = ref(false)

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

// Guild form — matches manual guild creation in AppSidebar
const guildForm = ref({
  name: '', realm_name: '', faction: '', timezone: 'Europe/Warsaw',
  armory_url: '', expansion_id: null,
})
const guildError = ref(null)
const lookupRealm = ref('')
const lookingUpGuild = ref(false)
const guildLookupDone = ref(false)
const guildLookupError = ref(null)
const guildLookupNotFound = ref(false)
const guildLookupMatch = ref(null)
const guildLookupMatches = ref([])
const guildManualMode = ref(false)

// Realm discovery
const discoveringRealms = ref(false)
const discoveredRealms = ref([])
let _lastDiscoveredUrl = ''

// Character form — matches manual character creation in CharacterManagerView
const charForm = ref({ name: '', realm: '', class_name: '', role: '', spec: '' })
const charError = ref(null)
const charManualEntry = ref(false)
const charLookingUp = ref(false)
const charLookupResult = ref(null)
const charArmoryData = ref(null)

const timezones = [
  'Europe/Warsaw', 'Europe/London', 'Europe/Paris', 'Europe/Berlin',
  'Europe/Madrid', 'Europe/Rome', 'Europe/Amsterdam', 'Europe/Brussels',
  'Europe/Vienna', 'Europe/Prague', 'Europe/Budapest', 'Europe/Bucharest',
  'Europe/Sofia', 'Europe/Athens', 'Europe/Helsinki', 'Europe/Stockholm',
  'Europe/Oslo', 'Europe/Copenhagen', 'Europe/Lisbon', 'Europe/Dublin',
  'Europe/Moscow', 'Europe/Istanbul',
  'US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific',
  'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
  'America/Sao_Paulo',
  'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Seoul', 'Asia/Singapore',
  'Australia/Sydney', 'Pacific/Auckland',
  'UTC',
]

const wowClasses = [
  'Death Knight', 'Druid', 'Hunter', 'Mage', 'Paladin',
  'Priest', 'Rogue', 'Shaman', 'Warlock', 'Warrior',
]

// Specs for selected class
const charFilteredSpecs = computed(() => {
  if (!charForm.value.class_name) return []
  const specs = systemSpecs.value ?? constantsStore.classSpecs ?? {}
  return specs[charForm.value.class_name] ?? []
})

// Expansions sorted by sort_order descending
const sortedExpansions = computed(() => {
  return [...constantsStore.expansions].sort((a, b) => (b.sort_order ?? 0) - (a.sort_order ?? 0))
})

// Included expansions when selected expansion is chosen
const includedExpansions = computed(() => {
  const selected = sortedExpansions.value.find(e => e.id === guildForm.value.expansion_id)
  if (!selected) return []
  const selectedOrder = selected.sort_order ?? 0
  return [...constantsStore.expansions]
    .filter(e => (e.sort_order ?? 0) <= selectedOrder)
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
})

// Auto-detect armory provider from URL
const detectedProvider = computed(() => {
  const url = guildForm.value.armory_url.trim().toLowerCase()
  if (!url) return null
  for (const provider of Object.keys(constantsStore.providerRealms)) {
    if (url.includes(provider)) return provider
  }
  return null
})

const detectedProviderRealms = computed(() => {
  if (!detectedProvider.value) return []
  return constantsStore.providerRealms[detectedProvider.value] || []
})

const selectedProviderRealms = computed(() => {
  if (discoveredRealms.value.length > 0) return discoveredRealms.value
  return detectedProviderRealms.value
})

const canDoLookup = computed(() => {
  return !!guildForm.value.armory_url.trim()
})

// ---------------------------------------------------------------------------
// Tenant step
// ---------------------------------------------------------------------------

async function saveTenantInfo() {
  saving.value = true
  tenantError.value = null
  try {
    if (tenantStore.activeTenantId) {
      await tenantsApi.updateTenant(tenantStore.activeTenantId, tenantForm.value)
    }
    currentStep.value = 2
    // Set default expansion
    if (sortedExpansions.value.length > 0 && !guildForm.value.expansion_id) {
      guildForm.value.expansion_id = sortedExpansions.value[0].id
    }
  } catch (err) {
    tenantError.value = err?.response?.data?.error || err?.response?.data?.message || t('setup.tenantSaveError')
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------------------
// Cancel tenant setup — delete tenant and return to dashboard
// ---------------------------------------------------------------------------

function cancelTenantSetup() {
  showCancelConfirm.value = true
}

async function confirmCancelSetup() {
  cancellingSetup.value = true
  try {
    if (tenantStore.activeTenantId) {
      await tenantsApi.deleteTenant(tenantStore.activeTenantId)
    }
    // Refresh stores to reflect tenant removal
    await tenantStore.fetchTenants()
    await authStore.fetchMe()
    toast.success(t('setup.setupCancelled'))
    router.push('/dashboard')
  } catch (err) {
    toast.error(err?.response?.data?.error || t('setup.cancelError'))
  } finally {
    cancellingSetup.value = false
    showCancelConfirm.value = false
  }
}

async function onArmoryUrlChange() {
  let url = guildForm.value.armory_url.trim()
  if (!url || url === _lastDiscoveredUrl) return
  if (url && !url.match(/^https?:\/\//i)) {
    url = 'https://' + url
    guildForm.value.armory_url = url
  }
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

async function lookupGuild() {
  const name = guildForm.value.name.trim()
  if (!name) return

  lookingUpGuild.value = true
  guildLookupError.value = null
  guildLookupNotFound.value = false
  guildLookupMatch.value = null
  guildLookupMatches.value = []

  const armoryUrl = guildForm.value.armory_url.trim()
  if (!armoryUrl) {
    lookingUpGuild.value = false
    guildLookupError.value = t('guild.armoryUrlRequired')
    return
  }

  const realmHints = []
  const manualRealm = lookupRealm.value.trim()
  if (manualRealm) realmHints.push(manualRealm)
  if (detectedProviderRealms.value.length > 0) {
    realmHints.push(...detectedProviderRealms.value)
  }

  try {
    const result = await armoryLookupApi.searchGuild(armoryUrl, name, realmHints)
    const serverMatches = result.matches || []
    const matches = serverMatches.map(m => ({
      ...m,
      alreadyAdded: guildStore.allGuilds?.some(
        g => g.name.toLowerCase() === name.toLowerCase() && g.realm_name.toLowerCase() === m.realm.toLowerCase()
      ) || false,
    }))

    lookingUpGuild.value = false

    if (matches.length === 0) {
      guildLookupNotFound.value = true
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
  guildForm.value.realm_name = match.realm
  guildForm.value.faction = match.faction || ''
  guildLookupDone.value = true
}

function enterManualGuild() {
  guildLookupDone.value = true
  guildLookupMatch.value = null
  guildManualMode.value = true
  guildLookupNotFound.value = false
  guildLookupError.value = null
}

function resetGuildLookup() {
  guildLookupDone.value = false
  guildLookupError.value = null
  guildLookupNotFound.value = false
  guildLookupMatch.value = null
  guildLookupMatches.value = []
  guildManualMode.value = false
  guildError.value = null
  lookupRealm.value = ''
  discoveredRealms.value = []
  _lastDiscoveredUrl = ''
  guildForm.value.realm_name = ''
  guildForm.value.faction = ''
}

async function createFirstGuild() {
  saving.value = true
  guildError.value = null
  try {
    const provider = detectedProvider.value || ''
    await guildsApi.createGuild({
      name: guildForm.value.name,
      realm_name: guildForm.value.realm_name,
      faction: guildForm.value.faction || null,
      timezone: guildForm.value.timezone,
      armory_source: !!guildLookupMatch.value,
      armory_provider: provider,
      armory_url: guildForm.value.armory_url.trim() || null,
      expansion_id: guildForm.value.expansion_id,
    })
    toast.success(t('setup.guildCreated'))
    currentStep.value = totalSteps + 1
  } catch (err) {
    guildError.value = err?.response?.data?.error || err?.response?.data?.message || t('setup.guildCreateError')
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------------------
// Character step — armory lookup (mirrors CharacterManagerView logic)
// ---------------------------------------------------------------------------

async function lookupCharFromArmory() {
  const name = charForm.value.name.trim()
  const realm = charForm.value.realm.trim()
  if (!name || !realm) return

  charLookingUp.value = true
  charLookupResult.value = null
  charArmoryData.value = null

  try {
    const data = await armoryLookupApi.lookupCharacter(realm, name, guildStore.currentGuildId || null)
    if (data && data.name) {
      charArmoryData.value = data
      charForm.value.name = data.name
      charForm.value.class_name = data.class_name || ''
      charForm.value.realm = data.realm || realm
      charForm.value.spec = data.talents?.[0]?.tree || ''
      charLookupResult.value = 'found'
    } else {
      charLookupResult.value = 'not_found'
    }
  } catch {
    charLookupResult.value = 'not_found'
  } finally {
    charLookingUp.value = false
  }
}

async function createFirstCharacter() {
  saving.value = true
  charError.value = null
  try {
    const payload = {
      name: charForm.value.name,
      realm: charForm.value.realm,
      class_name: charForm.value.class_name,
      role: charForm.value.role || undefined,
      spec: charForm.value.spec || undefined,
      is_main: true,
    }
    // Include armory metadata if found
    if (charArmoryData.value) {
      payload.metadata = {
        level: charArmoryData.value.level,
        race: charArmoryData.value.race,
        gender: charArmoryData.value.gender,
        faction: charArmoryData.value.faction,
        guild: charArmoryData.value.guild,
        achievement_points: charArmoryData.value.achievement_points,
        honorable_kills: charArmoryData.value.honorable_kills,
        professions: charArmoryData.value.professions || [],
        talents: charArmoryData.value.talents || [],
        equipment: charArmoryData.value.equipment || [],
        last_synced: new Date().toISOString(),
      }
      payload.armory_url = charArmoryData.value.armory_url || ''
    }
    await api.post('/characters', payload)
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
  // Set default expansion
  if (sortedExpansions.value.length > 0 && !guildForm.value.expansion_id) {
    guildForm.value.expansion_id = sortedExpansions.value[0].id
  }
})
</script>
