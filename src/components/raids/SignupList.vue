<template>
  <WowCard>
    <div class="flex items-center justify-between mb-4">
      <h3 class="wow-heading text-base">{{ t('signupList.title') }}</h3>
      <span class="text-sm text-text-muted">{{ t('signupList.total', { count: signups.length }) }}</span>
    </div>

    <div v-if="signups.length === 0" class="text-center py-6 text-text-muted text-sm">
      {{ t('common.labels.noSignups') }}
    </div>

    <!-- Side-by-side layout for In Lineup and Bench -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <template v-for="group in groups" :key="group.key">
        <div v-if="group.items.length > 0" :class="group.key === 'declined' ? 'lg:col-span-2' : ''">
          <div class="flex items-center gap-2 mb-2">
            <span
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border"
              :class="group.cls"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="group.dot" />
              {{ group.label }}
            </span>
            <span class="text-xs text-text-muted">({{ group.items.length }})</span>
          </div>
          <div class="space-y-4">
            <template v-for="signup in group.items" :key="signup.id">
            <!-- Inline edit form (officer only) -->
            <div v-if="editingSignupId === signup.id" class="px-4 py-4 rounded-lg bg-bg-tertiary border border-border-gold space-y-3">
              <div class="flex items-center gap-3">
                <img
                  v-if="signup.character?.class_name"
                  :src="getClassIcon(signup.character.class_name)"
                  :alt="signup.character.class_name"
                  class="w-8 h-8 rounded border border-border-default flex-shrink-0"
                />
                <span class="text-sm font-medium text-text-primary">{{ signup.character?.name ?? 'Unknown' }}</span>
                <ClassBadge v-if="signup.character?.class_name" :class-name="signup.character.class_name" />
              </div>

              <!-- Role icon buttons (same as SignupForm) -->
              <div>
                <label class="text-[10px] text-text-muted mb-1 block">Role</label>
                <div v-if="editRolesForClass(signup).length === 0" class="p-2 rounded bg-yellow-900/30 border border-yellow-600 text-yellow-300 text-[11px]">
                  ⚠ No available role slots for this class in this raid.
                </div>
                <div v-else class="flex gap-1.5">
                  <button
                    v-for="r in editRolesForClass(signup)"
                    :key="r.value"
                    type="button"
                    class="flex-1 flex flex-col items-center justify-center gap-0.5 py-1.5 rounded border text-xs transition-all"
                    :class="editForm.chosen_role === r.value
                      ? 'bg-accent-gold/10 border-accent-gold text-accent-gold'
                      : 'border-border-default text-text-muted hover:border-border-gold hover:text-text-primary'"
                    @click="editForm.chosen_role = r.value"
                  >
                    <RoleBadge :role="r.value" />
                  </button>
                </div>
              </div>

              <!-- Spec toggle buttons (same as SignupForm) -->
              <div v-if="editRolesForClass(signup).length > 0">
                <label class="text-[10px] text-text-muted mb-1 block">Spec</label>
                <div v-if="editSpecOptions(signup).length > 0" class="flex gap-1.5 mb-1">
                  <button
                    v-for="sp in editSpecOptions(signup)"
                    :key="sp"
                    type="button"
                    class="px-2.5 py-1 rounded border text-[11px] transition-all"
                    :class="editSelectedSpecs.includes(sp)
                      ? 'bg-accent-gold/10 border-accent-gold text-accent-gold'
                      : 'border-border-default text-text-muted hover:border-border-gold hover:text-text-primary'"
                    @click="toggleEditSpec(sp)"
                  >{{ sp }}</button>
                </div>
                <input
                  v-model="editForm.chosen_spec"
                  class="w-full bg-bg-secondary border border-border-default text-text-primary rounded px-2 py-1 text-xs focus:border-border-gold outline-none"
                  :placeholder="t('signupList.specPlaceholder')"
                />
              </div>

              <div class="flex justify-end gap-2 pt-1">
                <button class="px-3 py-1 text-xs text-text-muted hover:text-text-primary rounded border border-border-default hover:border-border-gold transition-colors" @click="cancelEdit">{{ t('common.buttons.cancel') }}</button>
                <button class="px-3 py-1 text-xs text-accent-gold hover:text-amber-300 rounded border border-accent-gold/50 hover:border-accent-gold transition-colors font-medium" @click="saveEdit(signup)">{{ t('common.buttons.save') }}</button>
              </div>
            </div>

            <!-- Normal display -->
            <div
              v-else
              class="rounded-lg border border-border-default bg-bg-tertiary/60 hover:border-border-gold/40 transition-colors overflow-hidden"
            >
              <!-- Card body -->
              <div class="p-5 sm:p-6">
                <div class="flex items-start gap-5">
                  <!-- Class icon (larger, prominent) -->
                  <img
                    v-if="signup.character?.class_name"
                    :src="getClassIcon(signup.character.class_name)"
                    :alt="signup.character.class_name"
                    class="w-16 h-16 rounded-lg border border-border-default flex-shrink-0"
                  />
                  <div class="w-16 h-16 rounded-lg bg-bg-secondary border border-border-default flex-shrink-0" v-else />

                  <!-- Main info -->
                  <div class="flex-1 min-w-0">
                    <!-- Name row -->
                    <div class="flex items-center gap-2.5 flex-wrap mb-3">
                      <span class="text-lg sm:text-xl font-bold text-text-primary">
                        {{ signup.character?.name ?? 'Unknown' }}
                      </span>
                      <span v-if="charLevel(signup)" class="text-xs font-semibold text-accent-gold bg-accent-gold/10 px-2.5 py-0.5 rounded-full border border-accent-gold/20">
                        {{ charLevel(signup) }}
                      </span>
                      <span
                        v-if="charAchievements(signup)"
                        class="text-xs text-amber-400"
                        :title="t('signupList.achievementPoints')"
                      >{{ charAchievements(signup) }} AP</span>
                    </div>

                    <!-- Class + Role badges -->
                    <div class="flex items-center gap-2.5 flex-wrap mb-3">
                      <ClassBadge v-if="signup.character?.class_name" :class-name="signup.character.class_name" />
                      <RoleBadge v-if="signup.chosen_role" :role="signup.chosen_role" />
                    </div>

                    <!-- Specs -->
                    <div v-if="signup.chosen_spec" class="flex items-center gap-2.5 flex-wrap mb-3">
                      <SpecBadge v-for="sp in signup.chosen_spec.split(',').map(s => s.trim()).filter(Boolean)" :key="sp" :spec="sp" :class-name="signup.character?.class_name" />
                    </div>

                    <!-- Professions -->
                    <div v-if="charProfessions(signup).length > 0" class="flex items-center gap-2.5 flex-wrap mb-3">
                      <span
                        v-for="prof in charProfessions(signup)"
                        :key="prof.name"
                        class="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 bg-bg-secondary border border-border-default rounded text-text-muted"
                      >
                        <img :src="getProfessionIcon(prof.name)" :alt="prof.name" class="w-4 h-4 rounded-sm" />
                        {{ prof.name }} {{ prof.skill }}
                      </span>
                    </div>

                    <!-- Note -->
                    <p v-if="signup.note" class="text-sm text-text-muted italic mb-3" :title="signup.note">{{ signup.note }}</p>

                    <!-- Bench queue info -->
                    <div v-if="signup.bench_info" class="mb-2">
                      <span class="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 bg-yellow-400/10 border border-yellow-500/30 rounded text-yellow-400 font-medium">
                        <img :src="getRoleIcon(signup.bench_info.waiting_for)" class="w-4 h-4 rounded-sm" alt="" />
                        Queue #{{ signup.bench_info.queue_position }} · {{ ROLE_LABEL_MAP[signup.bench_info.waiting_for] || signup.bench_info.waiting_for }}
                      </span>
                    </div>
                  </div>

                  <!-- Right: Attendance status badge (read-only) -->
                  <div class="flex-shrink-0">
                    <div class="flex items-center gap-2">
                      <img :src="getAttendanceStatusIcon(signup.attendance_status || 'going')" class="w-5 h-5 rounded-sm" :alt="ATTENDANCE_STATUS_LABEL_MAP[signup.attendance_status || 'going']" />
                      <span class="text-sm px-3 py-1.5 rounded-md" :class="(ATTENDANCE_STATUS_STYLE[signup.attendance_status || 'going'] || {}).badge">
                        {{ t(ATTENDANCE_STATUS_I18N_MAP[signup.attendance_status || 'going']) }}
                      </span>
                    </div>
                    <span v-if="signup.attendance_status === 'late' && signup.late_minutes" class="block text-xs text-amber-300 text-right mt-1">
                      ~{{ signup.late_minutes }} {{ t('signup.minutesLate') }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Card footer: Action buttons -->
              <div class="px-5 sm:px-6 py-3.5 bg-bg-secondary/40 border-t border-border-default/40 flex items-center gap-3 flex-wrap">
                <WowButton variant="secondary" class="text-xs !py-2 !px-4" @click.stop="openCharacterModal(signup.character)">
                  {{ t('signupList.viewDetails') }}
                </WowButton>
                <template v-if="canManage">
                  <WowButton variant="secondary" class="text-xs !py-2 !px-4" @click.stop="startEdit(signup)">
                    {{ t('common.buttons.edit') }}
                  </WowButton>
                  <WowButton variant="secondary" class="text-xs !py-2 !px-4" @click.stop="startReplaceCharacter(signup)">
                    {{ t('signupList.replace') }}
                  </WowButton>
                  <WowButton variant="danger" class="text-xs !py-2 !px-4" @click.stop="removeSignup(signup)">
                    {{ t('common.buttons.remove') }}
                  </WowButton>
                </template>
              </div>
            </div>
          </template>
        </div>
      </div>
    </template>
    </div>
  </WowCard>

  <!-- Character detail modal -->
  <CharacterDetailModal
    v-model="showCharacterModal"
    :character="characterModalTarget"
    :use-wowhead="wowheadEnabled"
  />

  <!-- Remove confirmation modal (officer only) -->
  <WowModal v-model="showRemoveModal" :title="t('signupList.removeTitle', { name: removeTarget?.character?.name ?? 'Player' })">
    <div class="space-y-4">
      <p class="text-sm text-text-muted">
        {{ t('signupList.removeQuestion', { name: removeTarget?.character?.name ?? t('signupList.thisPlayer') }) }}
      </p>
      <div class="space-y-2">
        <button
          class="w-full text-left px-4 py-3 rounded border border-border-default bg-bg-tertiary hover:border-border-gold transition-colors"
          @click="confirmRemove(false)"
        >
          <div class="text-sm font-medium text-text-primary">{{ t('signupList.removeThisTime') }}</div>
          <div class="text-xs text-text-muted mt-0.5">{{ t('signupList.removeThisTimeDesc') }}</div>
        </button>
        <button
          class="w-full text-left px-4 py-3 rounded border border-red-800 bg-red-900/20 hover:border-red-500 transition-colors"
          @click="confirmRemove(true)"
        >
          <div class="text-sm font-medium text-red-400">{{ t('signupList.permanentKick') }}</div>
          <div class="text-xs text-red-300/70 mt-0.5">{{ t('signupList.permanentKickDesc') }}</div>
        </button>
      </div>
      <div class="flex justify-end">
        <button class="text-sm text-text-muted hover:text-text-primary transition-colors" @click="showRemoveModal = false">{{ t('common.buttons.cancel') }}</button>
      </div>
    </div>
  </WowModal>

  <!-- Replace character modal (officer only) -->
  <WowModal v-model="showReplaceModal" :title="t('signupList.replaceTitle', { name: replaceTarget?.character?.name ?? 'Player' })">
    <div class="space-y-4">
      <p class="text-sm text-text-muted">
        {{ t('signupList.replaceDescription', { name: replaceTarget?.character?.name ?? t('signupList.thisPlayer') }) }}
      </p>
      <div v-if="replaceCharsLoading" class="text-center py-4 text-text-muted text-sm">{{ t('common.labels.loadingCharacters') }}</div>
      <div v-else-if="replaceChars.filter(ch => ch.id !== replaceTarget?.character_id).length === 0" class="text-center py-4 text-text-muted text-sm">
        {{ t('signupList.noReplacementChars') }}
      </div>
      <template v-else>
        <div class="space-y-2">
          <button
            v-for="c in replaceChars.filter(ch => ch.id !== replaceTarget?.character_id)"
            :key="c.id"
            class="w-full text-left px-4 py-3 rounded border transition-colors"
            :class="selectedReplaceCharId === c.id
              ? 'border-accent-gold bg-accent-gold/10'
              : 'border-border-default bg-bg-tertiary hover:border-border-gold'"
            @click="selectedReplaceCharId = c.id"
          >
            <div class="flex items-center gap-2">
              <img
                v-if="c.class_name"
                :src="getClassIcon(c.class_name)"
                :alt="c.class_name"
                class="w-6 h-6 rounded border border-border-default"
              />
              <span class="text-sm font-medium text-text-primary">{{ c.name }}</span>
              <span class="text-xs text-text-muted">{{ c.class_name }}</span>
              <span v-if="c.is_main" class="text-[10px] text-accent-gold bg-accent-gold/10 px-1.5 py-0.5 rounded">Main</span>
            </div>
          </button>
        </div>
        <div>
          <label class="text-[10px] text-text-muted">{{ t('signupList.reasonOptional') }}</label>
          <input v-model="replaceReason" class="w-full bg-bg-secondary border border-border-default text-text-primary rounded px-2 py-1 text-xs focus:border-border-gold outline-none" :placeholder="t('signupList.reasonPlaceholder')" />
        </div>
      </template>
      <div class="flex justify-end gap-2">
        <button class="text-sm text-text-muted hover:text-text-primary transition-colors" @click="showReplaceModal = false">{{ t('common.buttons.cancel') }}</button>
        <button
          v-if="selectedReplaceCharId"
          class="text-sm text-accent-gold hover:text-amber-300 font-medium transition-colors"
          @click="submitReplaceRequest"
        >{{ t('signupList.requestReplacement') }}</button>
      </div>
    </div>
  </WowModal>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import ClassBadge from '@/components/common/ClassBadge.vue'
import RoleBadge from '@/components/common/RoleBadge.vue'
import SpecBadge from '@/components/common/SpecBadge.vue'
import WowTooltip from '@/components/common/WowTooltip.vue'
import CharacterDetailModal from '@/components/common/CharacterDetailModal.vue'
import { useWowIcons } from '@/composables/useWowIcons'
import { useGuildStore } from '@/stores/guild'
import { useSystemSettings } from '@/composables/useSystemSettings'
import * as signupsApi from '@/api/signups'
import { ROLE_OPTIONS, ROLE_LABEL_MAP, ROLE_VALUES, ATTENDANCE_STATUS_LABEL_MAP, ATTENDANCE_STATUS_I18N_MAP, ATTENDANCE_STATUS_STYLE } from '@/constants'
import { useExpansionData } from '@/composables/useExpansionData'

const { t } = useI18n()
const { classRoles } = useExpansionData()

const guildStore = useGuildStore()
const systemSettings = useSystemSettings()
systemSettings.fetchSettings()
const wowheadEnabled = computed(() => systemSettings.wowheadEnabled())

const props = defineProps({
  signups: { type: Array, default: () => [] },
  canManage: { type: Boolean, default: false },
  guildId: { type: [Number, String], default: null },
  eventId: { type: [Number, String], default: null },
  availableRoles: { type: Array, default: () => ROLE_VALUES }
})

const emit = defineEmits(['signup-updated', 'signup-removed', 'signup-error'])

const { getClassIcon, getProfessionIcon, getRoleIcon, getAttendanceStatusIcon } = useWowIcons()

// --- Character detail modal ---
const showCharacterModal = ref(false)
const characterModalTarget = ref(null)

function openCharacterModal(character) {
  characterModalTarget.value = character
  showCharacterModal.value = true
}

const LINEUP_GROUPS = computed(() => [
  { key: 'going',    label: t('common.labels.inLineup'), cls: 'text-green-300 bg-green-500/10 border-green-500/30',  dot: 'bg-green-400' },
  { key: 'bench',    label: t('common.labels.bench'),     cls: 'text-yellow-300 bg-yellow-500/10 border-yellow-500/30', dot: 'bg-yellow-400' },
  { key: 'declined', label: t('common.labels.declined'),  cls: 'text-red-300 bg-red-500/10 border-red-500/30',        dot: 'bg-red-400' },
])

const groups = computed(() =>
  LINEUP_GROUPS.value.map(g => ({
    ...g,
    items: props.signups.filter(s => (s.lineup_status || 'going') === g.key)
  }))
)

// --- Officer inline edit ---
const editingSignupId = ref(null)
const editForm = reactive({ chosen_role: '', chosen_spec: '' })

/** Get allowed roles for a signup's character class, filtered by event available roles */
function editRolesForClass(signup) {
  const className = signup.character?.class_name
  if (!className) return []
  const classRolesForClass = classRoles.value[className] ?? []
  return ROLE_OPTIONS.filter(r => props.availableRoles.includes(r.value) && classRolesForClass.includes(r.value))
}

/** Get spec options for a signup's character */
function editSpecOptions(signup) {
  const specs = []
  if (signup.character?.primary_spec) specs.push(signup.character.primary_spec)
  if (signup.character?.secondary_spec) specs.push(signup.character.secondary_spec)
  return specs
}

/** Parse the comma-separated chosenSpec into an array for toggle button state */
const editSelectedSpecs = computed(() => {
  if (!editForm.chosen_spec) return []
  return editForm.chosen_spec.split(',').map(s => s.trim()).filter(Boolean)
})

/** Toggle a spec on/off in the edit form */
function toggleEditSpec(sp) {
  const current = editSelectedSpecs.value.slice()
  const idx = current.indexOf(sp)
  if (idx >= 0) {
    current.splice(idx, 1)
  } else {
    current.push(sp)
  }
  editForm.chosen_spec = current.join(', ')
}

function startEdit(signup) {
  editingSignupId.value = signup.id
  const validRoles = editRolesForClass(signup)
  const currentRole = signup.chosen_role ?? ''
  editForm.chosen_role = validRoles.some(r => r.value === currentRole) ? currentRole : (validRoles[0]?.value ?? '')
  editForm.chosen_spec = signup.chosen_spec ?? ''
}

function cancelEdit() {
  editingSignupId.value = null
}

async function saveEdit(signup) {
  if (!props.guildId || !props.eventId) return
  try {
    const updated = await signupsApi.updateSignup(props.guildId, props.eventId, signup.id, {
      chosen_role: editForm.chosen_role,
      chosen_spec: editForm.chosen_spec,
    })
    editingSignupId.value = null
    emit('signup-updated', updated)
  } catch (err) {
    emit('signup-error', err?.response?.data?.message ?? 'Failed to update signup')
  }
}

function charLevel(signup) {
  return signup.character?.metadata?.level ?? null
}

function charProfessions(signup) {
  return (signup.character?.metadata?.professions ?? []).slice(0, 2)
}

function charAchievements(signup) {
  return signup.character?.metadata?.achievement_points ?? null
}

// --- Officer remove with confirmation ---
const showRemoveModal = ref(false)
const removeTarget = ref(null)

function removeSignup(signup) {
  removeTarget.value = signup
  showRemoveModal.value = true
}

async function confirmRemove(permanent) {
  const signup = removeTarget.value
  if (!signup || !props.guildId || !props.eventId) return
  showRemoveModal.value = false
  try {
    await signupsApi.deleteSignup(props.guildId, props.eventId, signup.id, permanent ? { permanent: true } : undefined)
    emit('signup-removed', signup.id)
  } catch (err) {
    emit('signup-error', err?.response?.data?.message ?? 'Failed to remove signup')
  } finally {
    removeTarget.value = null
  }
}

// --- Officer character replacement ---
const showReplaceModal = ref(false)
const replaceTarget = ref(null)
const replaceChars = ref([])
const replaceCharsLoading = ref(false)
const selectedReplaceCharId = ref(null)
const replaceReason = ref('')

async function startReplaceCharacter(signup) {
  replaceTarget.value = signup
  showReplaceModal.value = true
  replaceChars.value = []
  replaceCharsLoading.value = true
  selectedReplaceCharId.value = null
  replaceReason.value = ''
  try {
    replaceChars.value = await signupsApi.getSignupUserCharacters(props.guildId, props.eventId, signup.id)
  } catch (err) {
    emit('signup-error', err?.response?.data?.message ?? 'Failed to load player characters')
    showReplaceModal.value = false
  } finally {
    replaceCharsLoading.value = false
  }
}

async function submitReplaceRequest() {
  if (!replaceTarget.value || !selectedReplaceCharId.value || !props.guildId || !props.eventId) return
  try {
    await signupsApi.createReplaceRequest(props.guildId, props.eventId, replaceTarget.value.id, {
      new_character_id: selectedReplaceCharId.value,
      reason: replaceReason.value || undefined,
    })
    showReplaceModal.value = false
    emit('signup-updated', null)
  } catch (err) {
    emit('signup-error', err?.response?.data?.message ?? 'Failed to create replacement request')
  }
}
</script>
