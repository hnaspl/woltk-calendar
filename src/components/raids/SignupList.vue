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
                    <option value="tank">Tank</option>
                    <option value="main_tank">Main Tank</option>
                    <option value="off_tank">Off Tank</option>
                    <option value="healer">Healer</option>
                    <option value="dps">DPS</option>
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
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import ClassBadge from '@/components/common/ClassBadge.vue'
import RoleBadge from '@/components/common/RoleBadge.vue'
import SpecBadge from '@/components/common/SpecBadge.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import WowTooltip from '@/components/common/WowTooltip.vue'
import CharacterTooltip from '@/components/common/CharacterTooltip.vue'
import { useWowIcons } from '@/composables/useWowIcons'
import * as signupsApi from '@/api/signups'

const props = defineProps({
  signups: { type: Array, default: () => [] },
  isOfficer: { type: Boolean, default: false },
  guildId: { type: [Number, String], default: null },
  eventId: { type: [Number, String], default: null }
})

const emit = defineEmits(['signup-updated', 'signup-removed', 'signup-error'])

const { getClassIcon } = useWowIcons()

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

async function removeSignup(signup) {
  if (!props.guildId || !props.eventId) return
  try {
    await signupsApi.deleteSignup(props.guildId, props.eventId, signup.id)
    emit('signup-removed', signup.id)
  } catch (err) {
    emit('signup-error', err?.response?.data?.message ?? 'Failed to remove signup')
  }
}
</script>
