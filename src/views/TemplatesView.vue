<template>
  <AppShell>
    <div class="p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6">
      <!-- Loading permissions -->
      <div v-if="!permissions.permissionsLoaded.value && !authStore.user?.is_admin" class="p-4 rounded-lg bg-bg-tertiary border border-border-default text-text-muted flex items-center gap-3">
        <div class="w-5 h-5 border-2 border-accent-gold/40 border-t-accent-gold rounded-full animate-spin" />
        {{ t('common.labels.loading') }}
      </div>
      <!-- No permission -->
      <div v-else-if="!hasViewAccess" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">
        {{ t('admin.noPermission') }}
      </div>
      <template v-else>
      <div class="flex items-center justify-between">
        <div>
          <h1 class="wow-heading text-xl sm:text-2xl">{{ t('templates.title') }}</h1>
          <p class="text-text-muted text-sm mt-0.5">{{ t('templates.subtitle') }}</p>
        </div>
        <WowButton @click="openAddModal">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          {{ t('templates.newTemplateTitle') }}
        </WowButton>
      </div>

      <div v-if="loading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="h-20 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      </div>
      <div v-else-if="noGuild" class="p-4 rounded-lg bg-blue-900/30 border border-blue-600 text-blue-300">
        {{ t('templates.noGuild') }}
      </div>
      <div v-else-if="error" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">{{ error }}</div>
      <div v-else-if="templates.length === 0" class="text-center py-12 text-text-muted">
        {{ t('templates.noTemplates') }}
      </div>
      <div v-else class="space-y-3">
        <WowCard v-for="tpl in templates" :key="tpl.id">
          <div class="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4">
            <img :src="getRaidIcon(tpl.raid_definition?.code || tpl.raid_type)" :alt="tpl.name" class="w-12 h-12 rounded border border-border-default bg-bg-tertiary flex-shrink-0 object-cover" />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-bold text-text-primary">{{ tpl.name }}</span>
                <RaidSizeBadge v-if="tpl.raid_size" :size="tpl.raid_size" />
                <span v-if="tpl.difficulty === 'heroic'" class="text-xs px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-300 border border-orange-600">Heroic</span>
              </div>
              <div class="text-xs text-text-muted mt-1">{{ tpl.default_instructions ?? t('templates.noInstructions') }}</div>
            </div>
            <div class="flex items-center gap-2 flex-wrap">
              <WowButton v-if="hasMultipleGuilds" variant="secondary" class="text-xs py-1.5" @click="openCopyModal(tpl)">
                📋 {{ t('common.buttons.copy') }}
              </WowButton>
              <WowButton variant="secondary" class="text-xs py-1.5" @click="openSeriesModal(tpl)">
                🔁 {{ t('templates.createRecurringRaid') }}
              </WowButton>
              <WowButton variant="secondary" class="text-xs py-1.5" @click="openApply(tpl)">
                {{ t('common.buttons.apply') }}
              </WowButton>
              <WowButton variant="secondary" class="text-xs py-1.5" @click="openEditModal(tpl)">
                {{ t('common.buttons.edit') }}
              </WowButton>
              <WowButton variant="danger" class="text-xs py-1.5 px-2" @click="confirmDelete(tpl)">✕</WowButton>
            </div>
          </div>
          <!-- Inline series for this template -->
          <div v-if="seriesForTemplate(tpl.id).length" class="mt-3 pt-3 border-t border-border-default space-y-2">
            <div class="text-xs font-semibold text-text-muted uppercase tracking-wide mb-1">🔁 Recurring Schedules</div>
            <div v-for="s in seriesForTemplate(tpl.id)" :key="s.id" class="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3 p-2 rounded bg-bg-tertiary/50 border border-border-default">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-sm font-medium text-text-primary">{{ s.title }}</span>
                  <span class="text-xs px-1.5 py-0.5 rounded border" :class="s.active ? 'bg-green-500/20 text-green-300 border-green-600' : 'bg-red-500/20 text-red-300 border-red-600'">
                    {{ s.active ? t('common.status.active') : t('common.status.inactive') }}
                  </span>
                </div>
                <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-text-muted mt-1">
                  <span v-if="s.recurrence_rule">📅 {{ formatRecurrence(s.recurrence_rule) }}</span>
                  <span v-if="s.days_of_week?.length">{{ formatSeriesDays(s.days_of_week) }}</span>
                  <span v-if="s.start_time_local">🕐 {{ s.start_time_local }}</span>
                  <span v-if="s.duration_minutes">⏱ {{ s.duration_minutes }}min</span>
                </div>
              </div>
              <div class="flex items-center gap-1.5 flex-wrap">
                <WowButton variant="primary" class="text-xs py-1 px-2" @click="openGenerate(s)">
                  {{ t('series.generateEvents') }}
                </WowButton>
                <WowButton variant="secondary" class="text-xs py-1 px-2" @click="openEditSeriesModal(s)">
                  {{ t('common.buttons.edit') }}
                </WowButton>
                <WowButton variant="danger" class="text-xs py-1 px-1.5" @click="confirmDeleteSeries(s)">✕</WowButton>
              </div>
            </div>
          </div>
        </WowCard>
      </div>

      <!-- Orphan Recurring Raids section -->
      <div v-if="!loading && orphanSeries.length" class="mt-6">
        <h2 class="wow-heading text-lg mb-3">🔁 {{ t('series.title') }}</h2>
        <p class="text-text-muted text-xs mb-3">Recurring schedules not linked to any template</p>
        <div class="space-y-2">
          <WowCard v-for="s in orphanSeries" :key="s.id">
            <div class="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4">
              <img :src="getRaidIcon(s.raid_definition?.code || s.raid_type)" :alt="s.title" class="w-10 h-10 rounded border border-border-default bg-bg-tertiary flex-shrink-0 object-cover" />
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-bold text-text-primary">{{ s.title }}</span>
                  <RaidSizeBadge v-if="s.default_raid_size" :size="s.default_raid_size" />
                  <span v-if="s.default_difficulty === 'heroic'" class="text-xs px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-300 border border-orange-600">Heroic</span>
                  <span class="text-xs px-1.5 py-0.5 rounded border" :class="s.active ? 'bg-green-500/20 text-green-300 border-green-600' : 'bg-red-500/20 text-red-300 border-red-600'">
                    {{ s.active ? t('common.status.active') : t('common.status.inactive') }}
                  </span>
                </div>
                <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-text-muted mt-1">
                  <span v-if="s.recurrence_rule">📅 {{ formatRecurrence(s.recurrence_rule) }}</span>
                  <span v-if="s.days_of_week?.length">{{ formatSeriesDays(s.days_of_week) }}</span>
                  <span v-if="s.start_time_local">🕐 {{ s.start_time_local }}</span>
                  <span v-if="s.duration_minutes">⏱ {{ s.duration_minutes }}min</span>
                </div>
              </div>
              <div class="flex items-center gap-2 flex-wrap">
                <WowButton variant="primary" class="text-xs py-1.5" @click="openGenerate(s)">
                  {{ t('series.generateEvents') }}
                </WowButton>
                <WowButton variant="secondary" class="text-xs py-1.5" @click="openEditSeriesModal(s)">
                  {{ t('common.buttons.edit') }}
                </WowButton>
                <WowButton variant="danger" class="text-xs py-1.5 px-2" @click="confirmDeleteSeries(s)">✕</WowButton>
              </div>
            </div>
          </WowCard>
        </div>
      </div>

      </template>
    </div>

    <!-- Add/Edit template modal -->
    <WowModal v-model="showModal" :title="editing ? t('templates.editTemplate') : t('templates.newTemplateTitle')" size="md">
      <form @submit.prevent="saveTemplate" class="space-y-4">
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('templates.templateName') }}</label>
          <input v-model="form.name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.raidDefinition') }}</label>
          <select v-model.number="form.raid_definition_id" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" @change="onTemplateRaidDefChange">
            <template v-for="group in templateRaidDefsByExpansion" :key="group.expansion">
              <optgroup :label="group.label">
                <option v-for="d in group.defs" :key="d.id" :value="d.id">{{ d.name }} ({{ d.default_raid_size ?? d.size }}-man)</option>
              </optgroup>
            </template>
          </select>
          <p v-if="raidDefinitions.length === 0" class="text-xs text-text-muted mt-1">{{ t('templates.noRaidDefs') }}</p>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.raidSize') }}</label>
            <select v-model.number="form.raid_size" :disabled="templateSelectedSizes.length <= 1" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none disabled:opacity-60 disabled:cursor-not-allowed">
              <option v-for="s in templateSelectedSizes" :key="s" :value="s">{{ s }}-man</option>
            </select>
            <span class="text-[10px] text-text-muted">{{ templateSelectedSizes.length > 1 ? t('calendar.selectSize') : t('calendar.sizeFromRaid') }}</span>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('calendar.difficulty') }}</label>
            <select v-model="form.difficulty" :disabled="!templateSelectedDef?.supports_heroic" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none disabled:opacity-60 disabled:cursor-not-allowed">
              <option value="normal">{{ t('calendar.normal') }}</option>
              <option v-if="templateSelectedDef?.supports_heroic" value="heroic">{{ t('calendar.heroic') }}</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('templates.closeRegistration') }}</label>
          <div class="flex items-center gap-2">
            <input v-model.number="form.close_registration_minutes" type="number" min="0" max="10080" step="30" class="w-32 bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" :placeholder="t('templates.minutesPlaceholder')" />
            <span class="text-xs text-text-muted">{{ t('templates.minutesBefore') }}</span>
          </div>
          <span class="text-[10px] text-text-muted">{{ t('templates.closeRegistrationHelp') }}</span>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('calendar.instructions') }}</label>
          <textarea v-model="form.default_instructions" rows="2" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none resize-none" />
        </div>
        <div v-if="formError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ formError }}</div>
        <!-- Multi-guild creation -->
        <div v-if="!editing && otherGuilds.length > 0" class="p-3 rounded bg-bg-tertiary border border-border-default">
          <label class="flex items-center gap-2 cursor-pointer">
            <input v-model="applyToOtherGuilds" type="checkbox" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
            <span class="text-sm text-text-primary">{{ t('common.copy.copyToOther') }}</span>
          </label>
          <div v-if="applyToOtherGuilds" class="mt-2 space-y-1 pl-6">
            <label class="flex items-center gap-2 cursor-pointer mb-1">
              <input type="checkbox" :checked="allOtherGuildsSelected" @change="toggleAllOtherGuilds" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
              <span class="text-xs text-accent-gold font-semibold">{{ t('common.copy.copyToAll') }}</span>
            </label>
            <label v-for="g in otherGuilds" :key="g.id" class="flex items-center gap-2 cursor-pointer">
              <input v-model="selectedGuildIds" :value="g.id" type="checkbox" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
              <span class="text-xs text-text-muted">{{ g.name }} <span class="text-text-muted/60">({{ g.realm_name }})</span></span>
            </label>
          </div>
        </div>
      </form>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton :loading="saving" @click="saveTemplate">{{ editing ? t('common.buttons.save') : t('common.buttons.create') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Copy to Guild modal -->
    <WowModal v-model="showCopyModal" :title="t('templates.copyTemplateToGuilds')" size="sm">
      <p class="text-text-muted text-sm mb-3">{{ t('common.copy.copyNameToGuilds', { name: copySource?.name }) }}</p>
      <div class="space-y-1">
        <label class="flex items-center gap-2 cursor-pointer mb-1">
          <input type="checkbox" :checked="allCopyGuildsSelected" @change="toggleAllCopyGuilds" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
          <span class="text-xs text-accent-gold font-semibold">{{ t('common.copy.copyToAll') }}</span>
        </label>
        <label v-for="g in otherGuilds" :key="g.id" class="flex items-center gap-2 cursor-pointer">
          <input v-model="copyGuildIds" :value="g.id" type="checkbox" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
          <span class="text-xs text-text-muted">{{ g.name }} <span class="text-text-muted/60">({{ g.realm_name }})</span></span>
        </label>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showCopyModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton :loading="saving" @click="doCopy" :disabled="copyGuildIds.length === 0">{{ t('common.buttons.copy') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Confirmation modal for no guilds selected -->
    <WowModal v-model="showNoGuildConfirm" :title="t('common.copy.noAdditionalGuilds')" size="sm">
      <p class="text-text-muted text-sm">{{ t('common.copy.onlyCreatedIn') }} <strong class="text-text-primary">{{ currentGuildLabel }}</strong>. {{ t('common.copy.goBackQuestion') }}</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="goBackToForm">{{ t('common.buttons.goBack') }}</WowButton>
          <WowButton @click="confirmSaveCurrentOnly">{{ t('common.buttons.continue') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Apply template modal -->
    <WowModal v-model="showApply" :title="t('templates.applyTemplate')" size="sm">
      <div class="space-y-4">
        <p class="text-text-muted text-sm">{{ t('templates.scheduleFromTemplate', { name: applyTarget?.name }) }}</p>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.startDateTime') }}</label>
          <input v-model="applyDate" type="datetime-local" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showApply = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton :loading="saving" @click="doApply">{{ t('common.buttons.schedule') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Delete confirmation -->
    <WowModal v-model="showDeleteConfirm" :title="t('templates.deleteTemplate')" size="sm">
      <p class="text-text-muted">{{ t('templates.deleteTemplateConfirm') }} <strong class="text-text-primary">{{ deleteTarget?.name }}</strong>?</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showDeleteConfirm = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="danger" :loading="saving" @click="doDelete">{{ t('common.buttons.delete') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Create Recurring Raid prompt after template creation -->
    <WowModal v-model="showRecurringPrompt" :title="t('templates.createRecurringRaid')" size="sm">
      <p class="text-text-muted text-sm">{{ t('templates.createRecurringPrompt') }}</p>
      <p class="text-text-muted text-xs mt-2">{{ t('templates.subtitle') }}</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showRecurringPrompt = false">{{ t('templates.skipRecurring') }}</WowButton>
          <WowButton @click="openRecurringFromPrompt">{{ t('templates.createRecurringRaid') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Series Add/Edit modal -->
    <WowModal v-model="showSeriesModal" :title="editingSeries ? t('series.editRecurringRaid') : t('series.newRecurringRaid')" size="md">
      <form @submit.prevent="saveSeries" class="space-y-4">
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('common.fields.titleRequired') }}</label>
          <input v-model="seriesForm.title" required :placeholder="t('series.titlePlaceholder')" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('series.recurrence') }}</label>
            <select v-model="seriesForm.recurrence_rule" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
              <option value="weekly">{{ t('series.weekly') }}</option>
              <option value="biweekly">{{ t('series.biweekly') }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('series.startTime') }}</label>
            <input v-model="seriesForm.start_time_local" type="time" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
        </div>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('series.selectDays') }}</label>
          <div class="flex flex-wrap gap-2">
            <label v-for="(dayName, dayKey) in dayLabels" :key="dayKey"
              class="flex items-center gap-1.5 px-3 py-1.5 rounded border cursor-pointer transition-colors text-sm"
              :class="seriesForm.days_of_week.includes(dayKey) ? 'bg-accent-gold/20 border-accent-gold text-accent-gold' : 'bg-bg-tertiary border-border-default text-text-muted hover:border-border-gold'"
            >
              <input type="checkbox" :value="dayKey" v-model="seriesForm.days_of_week" class="sr-only" />
              {{ dayName }}
            </label>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('series.durationMin') }}</label>
            <input v-model.number="seriesForm.duration_minutes" type="number" min="30" max="600" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
          </div>
          <div>
            <label class="block text-xs text-text-muted mb-1">{{ t('common.status.active') }}</label>
            <label class="flex items-center gap-2 mt-1 cursor-pointer">
              <input v-model="seriesForm.active" type="checkbox" class="rounded border-border-default bg-bg-tertiary text-accent-gold focus:ring-accent-gold" />
              <span class="text-sm text-text-primary">{{ seriesForm.active ? t('common.status.active') : t('common.status.inactive') }}</span>
            </label>
          </div>
        </div>
        <div v-if="seriesFormError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ seriesFormError }}</div>
      </form>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showSeriesModal = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton :loading="seriesSaving" @click="saveSeries">{{ editingSeries ? t('common.buttons.save') : t('common.buttons.create') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Generate events modal -->
    <WowModal v-model="showGenerateModal" :title="t('series.generateEventsTitle')" size="sm">
      <div class="space-y-4">
        <p class="text-text-muted text-sm">{{ t('series.generateFromSeries', { name: generateTarget?.title }) }}</p>
        <div>
          <label class="block text-xs text-text-muted mb-1">{{ t('series.howManyEvents') }}</label>
          <select v-model.number="generateCount" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
            <option :value="1">{{ t('series.oneWeek') }}</option>
            <option :value="2">{{ t('series.twoWeeks') }}</option>
            <option :value="4">{{ t('series.fourWeeks') }}</option>
            <option :value="8">{{ t('series.eightWeeks') }}</option>
            <option :value="12">{{ t('series.twelveWeeks') }}</option>
          </select>
        </div>
        <div v-if="generateResult" class="p-3 rounded bg-green-900/30 border border-green-600 text-green-300 text-sm">
          ✅ {{ t('series.created') }} {{ generateResult }} {{ t('series.eventsCreated') }}
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showGenerateModal = false">{{ t('common.buttons.close') }}</WowButton>
          <WowButton :loading="seriesSaving" @click="doGenerate">{{ t('common.buttons.generate') }}</WowButton>
        </div>
      </template>
    </WowModal>

    <!-- Delete series confirmation -->
    <WowModal v-model="showSeriesDeleteConfirm" :title="t('series.deleteSeries')" size="sm">
      <p class="text-text-muted">{{ t('series.deleteRecurring') }} <strong class="text-text-primary">{{ seriesDeleteTarget?.title }}</strong>? {{ t('series.existingNotAffected') }}</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showSeriesDeleteConfirm = false">{{ t('common.buttons.cancel') }}</WowButton>
          <WowButton variant="danger" :loading="seriesSaving" @click="doDeleteSeries">{{ t('common.buttons.delete') }}</WowButton>
        </div>
      </template>
    </WowModal>
  </AppShell>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import RaidSizeBadge from '@/components/common/RaidSizeBadge.vue'
import { useGuildStore } from '@/stores/guild'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { usePermissions } from '@/composables/usePermissions'
import { useTimezone } from '@/composables/useTimezone'
import * as templatesApi from '@/api/templates'
import * as raidDefsApi from '@/api/raidDefinitions'
import * as seriesApi from '@/api/series'
import { useConstantsStore } from '@/stores/constants'
import { groupRaidDefsByExpansion } from '@/constants'
import { useI18n } from 'vue-i18n'
import { useWowIcons } from '@/composables/useWowIcons'

const guildStore = useGuildStore()
const authStore = useAuthStore()
const uiStore = useUiStore()
const permissions = usePermissions()
const tzHelper = useTimezone()
const constantsStore = useConstantsStore()
const { t } = useI18n()
const { getRaidIcon } = useWowIcons()

const hasViewAccess = computed(() => permissions.can('create_events') || permissions.can('manage_templates'))
const hasMultipleGuilds = computed(() => guildStore.guilds.length > 1)

const templates = ref([])
const raidDefinitions = ref([])
const seriesList = ref([])
const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const noGuild = ref(false)
const formError = ref(null)
const showModal = ref(false)
const showApply = ref(false)
const showDeleteConfirm = ref(false)
const showCopyModal = ref(false)
const showNoGuildConfirm = ref(false)
const showRecurringPrompt = ref(false)
const showSeriesModal = ref(false)
const showSeriesDeleteConfirm = ref(false)
const showGenerateModal = ref(false)
const createdTemplateId = ref(null)
const editingSeries = ref(null)
const seriesDeleteTarget = ref(null)
const generateTarget = ref(null)
const generateCount = ref(4)
const generateResult = ref(null)
const seriesFormError = ref(null)
const seriesSaving = ref(false)
const editing = ref(null)
const applyTarget = ref(null)
const deleteTarget = ref(null)
const copySource = ref(null)
const applyDate = ref('')

const form = reactive({ name: '', raid_definition_id: '', raid_size: 25, difficulty: 'normal', default_instructions: '', close_registration_minutes: null })
const seriesForm = reactive({
  title: '',
  raid_definition_id: null,
  default_raid_size: 25,
  default_difficulty: 'normal',
  recurrence_rule: 'weekly',
  days_of_week: [],
  start_time_local: '19:00',
  duration_minutes: 180,
  template_id: null,
  active: true
})
const dayLabels = {
  monday: 'Mon', tuesday: 'Tue', wednesday: 'Wed', thursday: 'Thu',
  friday: 'Fri', saturday: 'Sat', sunday: 'Sun'
}
const applyToOtherGuilds = ref(false)
const selectedGuildIds = ref([])
const copyGuildIds = ref([])

const otherGuilds = computed(() =>
  guildStore.guilds.filter(g => g.id !== guildStore.currentGuild?.id)
)

const currentGuildLabel = computed(() => {
  const g = guildStore.currentGuild
  return g ? `${g.name} (${g.realm_name})` : ''
})

const templateSelectedDef = computed(() =>
  raidDefinitions.value.find(d => d.id === form.raid_definition_id) ?? null
)

const templateRaidDefsByExpansion = computed(() => {
  const builtins = raidDefinitions.value.filter(d => d.is_builtin)
  return groupRaidDefsByExpansion(builtins, constantsStore.expansionSlugsDesc, constantsStore.expansionLabelMap)
})

const templateSelectedSizes = computed(() => {
  const rd = templateSelectedDef.value
  if (!rd) return templateAvailableSizes.value
  if (rd.supported_sizes && Array.isArray(rd.supported_sizes) && rd.supported_sizes.length) {
    return [...rd.supported_sizes].sort((a, b) => a - b)
  }
  return [rd.default_raid_size ?? rd.size ?? 25]
})

const templateAvailableSizes = computed(() => {
  const sizes = new Set()
  for (const d of raidDefinitions.value) {
    sizes.add(d.default_raid_size ?? d.size ?? 25)
  }
  if (sizes.size === 0) { sizes.add(10); sizes.add(25) }
  return [...sizes].sort((a, b) => a - b)
})

const allOtherGuildsSelected = computed(() =>
  otherGuilds.value.length > 0 && otherGuilds.value.every(g => selectedGuildIds.value.includes(g.id))
)

const allCopyGuildsSelected = computed(() =>
  otherGuilds.value.length > 0 && otherGuilds.value.every(g => copyGuildIds.value.includes(g.id))
)

function toggleAllOtherGuilds(e) {
  selectedGuildIds.value = e.target.checked ? otherGuilds.value.map(g => g.id) : []
}

function toggleAllCopyGuilds(e) {
  copyGuildIds.value = e.target.checked ? otherGuilds.value.map(g => g.id) : []
}

let isActive = true
let loadVersion = 0

onUnmounted(() => { isActive = false })

async function loadData() {
  if (!guildStore.currentGuild || !isActive) return
  const version = ++loadVersion
  loading.value = true
  error.value = null
  noGuild.value = false
  try {
    const [tpls, defs, seriesData] = await Promise.all([
      templatesApi.getTemplates(guildStore.currentGuild.id),
      raidDefsApi.getRaidDefinitions(guildStore.currentGuild.id),
      seriesApi.getSeries(guildStore.currentGuild.id)
    ])
    if (version === loadVersion && isActive) {
      templates.value = tpls
      raidDefinitions.value = defs
      seriesList.value = seriesData
    }
  } catch {
    if (version === loadVersion && isActive) error.value = t('templates.failedToLoad')
  } finally {
    if (version === loadVersion && isActive) loading.value = false
  }
}

onMounted(async () => {
  if (!guildStore.currentGuild) await guildStore.fetchGuilds()
  if (!guildStore.currentGuild) {
    noGuild.value = true
    loading.value = false
    return
  }
  loadData()
})

// Reload when guild changes in sidebar
watch(() => guildStore.currentGuild?.id, (newId, oldId) => {
  if (newId && newId !== oldId) loadData()
})

function openAddModal() {
  editing.value = null
  const firstDef = raidDefinitions.value[0]
  const firstId = firstDef?.id ?? ''
  Object.assign(form, { name: '', raid_definition_id: firstId, raid_size: firstDef?.default_raid_size ?? 25, difficulty: 'normal', default_instructions: '', close_registration_minutes: null })
  if (firstId) onTemplateRaidDefChange()
  applyToOtherGuilds.value = false
  selectedGuildIds.value = []
  formError.value = null; showModal.value = true
}

function openEditModal(tpl) {
  editing.value = tpl
  Object.assign(form, { name: tpl.name, raid_definition_id: tpl.raid_definition_id ?? '', raid_size: tpl.raid_size ?? 25, difficulty: tpl.difficulty ?? 'normal', default_instructions: tpl.default_instructions ?? '', close_registration_minutes: tpl.close_registration_minutes ?? null })
  formError.value = null; showModal.value = true
}

function openApply(tpl) { applyTarget.value = tpl; applyDate.value = ''; showApply.value = true }
function confirmDelete(tpl) { deleteTarget.value = tpl; showDeleteConfirm.value = true }

function onTemplateRaidDefChange() {
  const rd = raidDefinitions.value.find(d => d.id === form.raid_definition_id)
  if (rd) {
    form.raid_size = rd.default_raid_size ?? rd.size ?? 25
    form.difficulty = rd.supports_heroic ? 'heroic' : 'normal'
  }
}

function openCopyModal(tpl) {
  copySource.value = tpl
  copyGuildIds.value = []
  showCopyModal.value = true
}

async function saveTemplate() {
  formError.value = null
  if (!form.name || !form.raid_definition_id) { formError.value = t('templates.toasts.nameRaidDefRequired'); return }

  // Check if multi-guild is checked but no guilds selected
  if (!editing.value && applyToOtherGuilds.value && selectedGuildIds.value.length === 0) {
    showNoGuildConfirm.value = true
    return
  }

  await doSave()
}

function goBackToForm() {
  showNoGuildConfirm.value = false
}

async function confirmSaveCurrentOnly() {
  showNoGuildConfirm.value = false
  applyToOtherGuilds.value = false
  await doSave()
}

async function doSave() {
  saving.value = true
  const payload = {
    name: form.name,
    raid_definition_id: form.raid_definition_id,
    raid_size: form.raid_size,
    difficulty: form.difficulty,
    default_instructions: form.default_instructions || undefined,
    close_registration_minutes: form.close_registration_minutes || undefined
  }
  try {
    if (editing.value) {
      const updated = await templatesApi.updateTemplate(guildStore.currentGuild.id, editing.value.id, payload)
      const idx = templates.value.findIndex(t => t.id === editing.value.id)
      if (idx !== -1) templates.value[idx] = updated
    } else {
      const created = await templatesApi.createTemplate(guildStore.currentGuild.id, payload)
      templates.value.push(created)
      createdTemplateId.value = created.id
      // Also create in other selected guilds
      if (applyToOtherGuilds.value && selectedGuildIds.value.length > 0) {
        let failed = 0
        for (const guildId of selectedGuildIds.value) {
          try { await templatesApi.createTemplate(guildId, payload) } catch { failed++ }
        }
        if (failed > 0) uiStore.showToast(t('common.copy.failedToCreateInGuilds', { count: failed }), 'warning')
      }
    }
    showModal.value = false
    const isNew = !editing.value
    const guildLabel = currentGuildLabel.value
    uiStore.showToast(editing.value ? t('templates.toasts.templateUpdated') : t('templates.toasts.templateCreated', { guild: guildLabel }), 'success')
    // Prompt to create recurring raid after new template creation
    if (isNew) {
      showRecurringPrompt.value = true
    }
  } catch (err) {
    formError.value = err?.response?.data?.message ?? t('common.toasts.failedToSave')
  } finally { saving.value = false }
}

async function doApply() {
  if (!applyDate.value) return
  saving.value = true
  try {
    await templatesApi.applyTemplate(guildStore.currentGuild.id, applyTarget.value.id, { start_time: tzHelper.guildLocalToUtc(applyDate.value) })
    showApply.value = false
    uiStore.showToast(t('templates.eventScheduled'), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.message ?? t('templates.toasts.failedToApply'), 'error')
  } finally { saving.value = false }
}

function openRecurringFromPrompt(templateId) {
  showRecurringPrompt.value = false
  const id = templateId || createdTemplateId.value
  if (id) {
    const tpl = templates.value.find(t => t.id === id)
    openSeriesModal(tpl || null)
  } else {
    openSeriesModal(null)
  }
}

async function doDelete() {
  saving.value = true
  try {
    await templatesApi.deleteTemplate(guildStore.currentGuild.id, deleteTarget.value.id)
    templates.value = templates.value.filter(t => t.id !== deleteTarget.value.id)
    showDeleteConfirm.value = false
    uiStore.showToast(t('templates.templateDeleted'), 'success')
  } catch { uiStore.showToast(t('common.toasts.failedToDelete'), 'error') }
  finally { saving.value = false }
}

async function doCopy() {
  if (copyGuildIds.value.length === 0) return
  saving.value = true
  let succeeded = 0, failed = 0
  for (const guildId of copyGuildIds.value) {
    try {
      await templatesApi.copyTemplate(guildId, copySource.value.id)
      succeeded++
    } catch { failed++ }
  }
  showCopyModal.value = false
  if (failed > 0) {
    uiStore.showToast(t('common.copy.copiedWithFailures', { succeeded, failed }), 'warning')
  } else {
    uiStore.showToast(t('common.copy.copiedSuccess', { name: copySource.value.name, count: succeeded }), 'success')
  }
  saving.value = false
}

function seriesForTemplate(tplId) {
  return seriesList.value.filter(s => s.template_id === tplId)
}

const orphanSeries = computed(() => {
  const templateIds = new Set(templates.value.map(t => t.id))
  return seriesList.value.filter(s => !s.template_id || !templateIds.has(s.template_id))
})

function formatRecurrence(rule) {
  if (!rule) return ''
  if (rule.toLowerCase().includes('biweekly')) return t('series.everyTwoWeeks')
  if (rule.toLowerCase().includes('weekly')) return t('series.everyWeek')
  return rule
}

function formatSeriesDays(days) {
  if (!Array.isArray(days) || !days.length) return ''
  return days.map(d => dayLabels[d] || d).join(', ')
}

function openSeriesModal(tpl) {
  editingSeries.value = null
  seriesFormError.value = null
  Object.assign(seriesForm, {
    title: tpl?.name || '',
    raid_definition_id: tpl?.raid_definition_id || null,
    default_raid_size: tpl?.raid_size || 25,
    default_difficulty: tpl?.difficulty || 'normal',
    recurrence_rule: 'weekly',
    days_of_week: [],
    start_time_local: '19:00',
    duration_minutes: 180,
    template_id: tpl?.id || null,
    active: true
  })
  showSeriesModal.value = true
}

function openEditSeriesModal(s) {
  editingSeries.value = s
  seriesFormError.value = null
  Object.assign(seriesForm, {
    title: s.title || '',
    raid_definition_id: s.raid_definition_id || null,
    default_raid_size: s.default_raid_size || 25,
    default_difficulty: s.default_difficulty || 'normal',
    recurrence_rule: s.recurrence_rule || 'weekly',
    days_of_week: Array.isArray(s.days_of_week) ? [...s.days_of_week] : [],
    start_time_local: s.start_time_local || '19:00',
    duration_minutes: s.duration_minutes || 180,
    template_id: s.template_id || null,
    active: s.active !== false
  })
  showSeriesModal.value = true
}

async function saveSeries() {
  seriesFormError.value = null
  if (!seriesForm.title) { seriesFormError.value = t('series.toasts.titleRequired'); return }
  seriesSaving.value = true
  const payload = { ...seriesForm }
  try {
    if (editingSeries.value) {
      const updated = await seriesApi.updateSeries(guildStore.currentGuild.id, editingSeries.value.id, payload)
      const idx = seriesList.value.findIndex(s => s.id === editingSeries.value.id)
      if (idx !== -1) seriesList.value[idx] = updated
      uiStore.showToast(t('series.toasts.seriesUpdated'), 'success')
    } else {
      const created = await seriesApi.createSeries(guildStore.currentGuild.id, payload)
      seriesList.value.push(created)
      uiStore.showToast(t('series.toasts.seriesCreated', { guild: currentGuildLabel.value }), 'success')
    }
    showSeriesModal.value = false
  } catch (err) {
    seriesFormError.value = err?.response?.data?.error ?? err?.response?.data?.message ?? t('common.toasts.failedToSave')
  } finally { seriesSaving.value = false }
}

function confirmDeleteSeries(s) {
  seriesDeleteTarget.value = s
  showSeriesDeleteConfirm.value = true
}

async function doDeleteSeries() {
  seriesSaving.value = true
  try {
    await seriesApi.deleteSeries(guildStore.currentGuild.id, seriesDeleteTarget.value.id)
    seriesList.value = seriesList.value.filter(s => s.id !== seriesDeleteTarget.value.id)
    showSeriesDeleteConfirm.value = false
    uiStore.showToast(t('series.seriesDeleted'), 'success')
  } catch { uiStore.showToast(t('common.toasts.failedToDelete'), 'error') }
  finally { seriesSaving.value = false }
}

function openGenerate(s) {
  generateTarget.value = s
  generateCount.value = 4
  generateResult.value = null
  showGenerateModal.value = true
}

async function doGenerate() {
  if (!generateTarget.value) return
  seriesSaving.value = true
  generateResult.value = null
  try {
    const events = await seriesApi.generateEvents(guildStore.currentGuild.id, generateTarget.value.id, { count: generateCount.value })
    generateResult.value = Array.isArray(events) ? events.length : generateCount.value
    uiStore.showToast(t('series.toasts.eventsGenerated', { count: generateResult.value }), 'success')
  } catch (err) {
    uiStore.showToast(err?.response?.data?.error ?? err?.response?.data?.message ?? t('series.toasts.failedToGenerate'), 'error')
  } finally { seriesSaving.value = false }
}
</script>
