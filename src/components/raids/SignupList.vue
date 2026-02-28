<template>
  <WowCard>
    <div class="flex items-center justify-between mb-4">
      <h3 class="wow-heading text-base">Signups</h3>
      <span class="text-sm text-text-muted">{{ signups.length }} total</span>
    </div>

    <div v-if="signups.length === 0" class="text-center py-6 text-text-muted text-sm">
      No signups yet.
    </div>

    <template v-for="group in groups" :key="group.status">
      <div v-if="group.items.length > 0" class="mb-5">
        <div class="flex items-center gap-2 mb-2">
          <StatusBadge :status="group.status" />
          <span class="text-xs text-text-muted">({{ group.items.length }})</span>
        </div>
        <div class="space-y-1.5">
          <template v-for="signup in group.items" :key="signup.id">
            <!-- Inline edit form (officer only) -->
            <div v-if="editingSignupId === signup.id" class="px-3 py-2 rounded-lg bg-bg-tertiary border border-border-gold space-y-2">
              <div class="flex items-center gap-2">
                <img
                  v-if="signup.character?.class_name"
                  :src="getClassIcon(signup.character.class_name)"
                  :alt="signup.character.class_name"
                  class="w-6 h-6 rounded border border-border-default flex-shrink-0"
                />
                <span class="text-sm font-medium text-text-primary">{{ signup.character?.name ?? 'Unknown' }}</span>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="text-[10px] text-text-muted">Role</label>
                  <select v-model="editForm.chosen_role" class="w-full bg-bg-secondary border border-border-default text-text-primary rounded px-2 py-1 text-xs focus:border-border-gold outline-none">
                    <option v-for="r in filteredRoleOptions" :key="r.value" :value="r.value">{{ r.label }}</option>
                  </select>
                </div>
                <div>
                  <label class="text-[10px] text-text-muted">Spec</label>
                  <input v-model="editForm.chosen_spec" class="w-full bg-bg-secondary border border-border-default text-text-primary rounded px-2 py-1 text-xs focus:border-border-gold outline-none" placeholder="Spec…" />
                </div>
              </div>
              <div>
                <label class="text-[10px] text-text-muted">Gear Score Note</label>
                <input v-model="editForm.gear_score_note" class="w-full bg-bg-secondary border border-border-default text-text-primary rounded px-2 py-1 text-xs focus:border-border-gold outline-none" placeholder="e.g. 5800 GS…" />
              </div>
              <div class="flex justify-end gap-2">
                <button class="text-xs text-text-muted hover:text-text-primary" @click="cancelEdit">Cancel</button>
                <button class="text-xs text-accent-gold hover:text-amber-300" @click="saveEdit(signup)">Save</button>
              </div>
            </div>

            <!-- Normal display -->
            <CharacterTooltip
              v-else
              :character="signup.character"
              position="left"
            >
              <div
                class="flex items-center gap-3 px-3 py-2 rounded-lg bg-bg-tertiary/60 hover:bg-bg-tertiary transition-colors cursor-default w-full"
              >
                <!-- Class icon -->
                <img
                  v-if="signup.character?.class_name"
                  :src="getClassIcon(signup.character.class_name)"
                  :alt="signup.character.class_name"
                  class="w-7 h-7 rounded border border-border-default flex-shrink-0"
                />
                <div class="w-7 h-7 rounded bg-bg-secondary flex-shrink-0" v-else />

                <!-- Name + badges -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-text-primary truncate">
                      {{ signup.character?.name ?? 'Unknown' }}
                    </span>
                    <span v-if="charLevel(signup)" class="text-[10px] text-text-muted">
                      Lv{{ charLevel(signup) }}
                    </span>
                  </div>
                  <div class="flex items-center gap-1.5 mt-0.5 flex-wrap">
                    <ClassBadge v-if="signup.character?.class_name" :class-name="signup.character.class_name" />
                    <RoleBadge v-if="signup.chosen_role" :role="signup.chosen_role" />
                    <SpecBadge v-if="signup.chosen_spec" :spec="signup.chosen_spec" />
                    <!-- Professions inline -->
                    <span
                      v-for="prof in charProfessions(signup)"
                      :key="prof.name"
                      class="text-[10px] px-1.5 py-0.5 bg-[#1c2333] border border-[#2a3450] rounded text-text-muted"
                    >
                      {{ prof.name }} {{ prof.skill }}
                    </span>
                  </div>
                  <!-- Gear score note -->
                  <div v-if="signup.gear_score_note" class="text-[10px] text-amber-300 mt-0.5">
                    GS: {{ signup.gear_score_note }}
                  </div>
                </div>

                <!-- Achievement points -->
                <span
                  v-if="charAchievements(signup)"
                  class="text-[10px] text-amber-400 flex-shrink-0"
                  title="Achievement Points"
                >
                  🏆 {{ charAchievements(signup) }}
                </span>

                <!-- Note -->
                <WowTooltip v-if="signup.note" :text="signup.note" position="left">
                  <svg class="w-4 h-4 text-text-muted flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"/>
                  </svg>
                </WowTooltip>

                <!-- Officer actions -->
                <div v-if="isOfficer" class="flex items-center gap-1 flex-shrink-0" @click.stop>
                  <button
                    class="text-amber-400 hover:text-amber-300 transition-colors p-0.5"
                    title="Edit role / spec"
                    @click="startEdit(signup)"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                    </svg>
                  </button>
                  <button
                    class="text-blue-400 hover:text-blue-300 transition-colors p-0.5"
                    title="Replace character"
                    @click="startReplaceCharacter(signup)"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
                    </svg>
                  </button>
                  <button
                    class="text-red-400 hover:text-red-300 transition-colors p-0.5"
                    title="Remove signup"
                    @click="removeSignup(signup)"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                  </button>
                </div>
              </div>
            </CharacterTooltip>
          </template>
        </div>
      </div>
    </template>
  </WowCard>

  <!-- Remove confirmation modal (officer only) -->
  <WowModal v-model="showRemoveModal" :title="'Remove ' + (removeTarget?.character?.name ?? 'Player')">
    <div class="space-y-4">
      <p class="text-sm text-text-muted">
        How would you like to remove <strong class="text-text-primary">{{ removeTarget?.character?.name ?? 'this player' }}</strong> from this raid?
      </p>
      <div class="space-y-2">
        <button
          class="w-full text-left px-4 py-3 rounded border border-border-default bg-bg-tertiary hover:border-border-gold transition-colors"
          @click="confirmRemove(false)"
        >
          <div class="text-sm font-medium text-text-primary">Remove this time</div>
          <div class="text-xs text-text-muted mt-0.5">The player can sign up again if they wish.</div>
        </button>
        <button
          class="w-full text-left px-4 py-3 rounded border border-red-800 bg-red-900/20 hover:border-red-500 transition-colors"
          @click="confirmRemove(true)"
        >
          <div class="text-sm font-medium text-red-400">Permanently kick from raid</div>
          <div class="text-xs text-red-300/70 mt-0.5">The player will be banned from signing up to this raid with this character.</div>
        </button>
      </div>
      <div class="flex justify-end">
        <button class="text-sm text-text-muted hover:text-text-primary transition-colors" @click="showRemoveModal = false">Cancel</button>
      </div>
    </div>
  </WowModal>

  <!-- Replace character modal (officer only) -->
  <WowModal v-model="showReplaceModal" :title="'Replace Character — ' + (replaceTarget?.character?.name ?? 'Player')">
    <div class="space-y-4">
      <p class="text-sm text-text-muted">
        Select a replacement character for <strong class="text-text-primary">{{ replaceTarget?.character?.name ?? 'this player' }}</strong>.
        The player will be notified and can confirm, decline, or leave the raid.
      </p>
      <div v-if="replaceCharsLoading" class="text-center py-4 text-text-muted text-sm">Loading characters…</div>
      <div v-else-if="replaceChars.length <= 1" class="text-center py-4 text-text-muted text-sm">
        This player has no other characters available for replacement.
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
          <label class="text-[10px] text-text-muted">Reason (optional)</label>
          <input v-model="replaceReason" class="w-full bg-bg-secondary border border-border-default text-text-primary rounded px-2 py-1 text-xs focus:border-border-gold outline-none" placeholder="e.g. Need a tank for this fight…" />
        </div>
      </template>
      <div class="flex justify-end gap-2">
        <button class="text-sm text-text-muted hover:text-text-primary transition-colors" @click="showReplaceModal = false">Cancel</button>
        <button
          v-if="selectedReplaceCharId"
          class="text-sm text-accent-gold hover:text-amber-300 font-medium transition-colors"
          @click="submitReplaceRequest"
        >Request Replacement</button>
      </div>
    </div>
  </WowModal>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import WowModal from '@/components/common/WowModal.vue'
import ClassBadge from '@/components/common/ClassBadge.vue'
import RoleBadge from '@/components/common/RoleBadge.vue'
import SpecBadge from '@/components/common/SpecBadge.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import WowTooltip from '@/components/common/WowTooltip.vue'
import CharacterTooltip from '@/components/common/CharacterTooltip.vue'
import { useWowIcons } from '@/composables/useWowIcons'
import * as signupsApi from '@/api/signups'
import { ROLE_OPTIONS } from '@/constants'

const props = defineProps({
  signups: { type: Array, default: () => [] },
  isOfficer: { type: Boolean, default: false },
  guildId: { type: [Number, String], default: null },
  eventId: { type: [Number, String], default: null },
  availableRoles: { type: Array, default: () => ['main_tank', 'off_tank', 'tank', 'healer', 'dps'] }
})

const emit = defineEmits(['signup-updated', 'signup-removed', 'signup-error'])

const { getClassIcon } = useWowIcons()

const filteredRoleOptions = computed(() =>
  ROLE_OPTIONS.filter(r => props.availableRoles.includes(r.value))
)

const STATUS_ORDER = ['going', 'tentative', 'late', 'bench', 'declined']

const groups = computed(() =>
  STATUS_ORDER.map(status => ({
    status,
    items: props.signups.filter(s => s.status === status)
  }))
)

// --- Officer inline edit ---
const editingSignupId = ref(null)
const editForm = reactive({ chosen_role: '', chosen_spec: '', gear_score_note: '' })

function startEdit(signup) {
  editingSignupId.value = signup.id
  editForm.chosen_role = signup.chosen_role ?? 'dps'
  editForm.chosen_spec = signup.chosen_spec ?? ''
  editForm.gear_score_note = signup.gear_score_note ?? ''
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
      gear_score_note: editForm.gear_score_note || undefined
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
