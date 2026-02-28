<template>
  <WowCard>
    <h3 class="wow-heading text-base mb-4">Sign Up</h3>

    <div v-if="error" class="mb-4 p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">
      {{ error }}
    </div>
    <div v-if="success" class="mb-4 p-3 rounded bg-green-900/30 border border-green-600 text-green-300 text-sm">
      Signed up successfully!
    </div>

    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Character select -->
      <div>
        <label class="block text-xs text-text-muted mb-1">Character *</label>
        <select
          v-model="form.characterId"
          class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
          required
          @change="onCharacterChange"
        >
          <option value="">Select character…</option>
          <option
            v-for="char in availableCharacters"
            :key="char.id"
            :value="char.id"
          >
            {{ char.name }} ({{ char.class_name }} – {{ char.realm_name }})
          </option>
        </select>
        <span v-if="!existingSignup && signedUpCharacterIds.length > 0" class="text-[10px] text-text-muted">
          Already signed up characters are hidden. Select another character to add.
        </span>
        <div v-if="bannedCharacterIds.length > 0" class="text-[10px] text-red-400 mt-1">
          ⛔ Some characters are hidden because they have been permanently kicked from this raid.
        </div>
      </div>

      <!-- Role -->
      <div>
        <label class="text-xs text-text-muted mb-1 block">Role *</label>
        <div v-if="form.characterId && roles.length === 0" class="p-3 rounded bg-yellow-900/30 border border-yellow-600 text-yellow-300 text-sm">
          ⚠ There are no available role slots for this character's class in this raid. This character cannot sign up for this event.
        </div>
        <div v-else class="flex gap-2">
          <button
            v-for="r in roles"
            :key="r.value"
            type="button"
            class="flex-1 flex flex-col items-center justify-center gap-0.5 py-2 rounded border text-sm transition-all"
            :class="form.chosenRole === r.value
              ? 'bg-accent-gold/10 border-accent-gold text-accent-gold'
              : 'border-border-default text-text-muted hover:border-border-gold hover:text-text-primary'"
            :disabled="form.characterId === ''"
            @click="form.chosenRole = r.value"
          >
            <RoleBadge :role="r.value" />
            <span v-if="roleSlotInfo[r.value]" class="text-[10px]" :class="isRoleFull(r.value) ? 'text-yellow-400' : 'text-text-muted'">
              {{ roleSlotInfo[r.value].current }}/{{ roleSlotInfo[r.value].max }}{{ isRoleFull(r.value) ? ' Full' : '' }}
            </span>
          </button>
        </div>
        <p v-if="form.chosenRole && isRoleFull(form.chosenRole)" class="mt-1.5 text-xs text-yellow-400/90">
          ⚠ All {{ ROLE_LABEL_MAP[form.chosenRole] || form.chosenRole }} slots are full. You will be placed on the <strong>bench</strong> as the next candidate when a slot opens up.
        </p>
      </div>

      <!-- Spec (multi-select, only when character selected) -->
      <div v-if="form.characterId">
        <label class="block text-xs text-text-muted mb-1">Spec (select one or more)</label>
        <div v-if="specOptions.length > 0" class="flex gap-2 mb-1">
          <button
            v-for="sp in specOptions"
            :key="sp"
            type="button"
            class="px-3 py-1.5 rounded border text-xs transition-all"
            :class="selectedSpecs.includes(sp)
              ? 'bg-accent-gold/10 border-accent-gold text-accent-gold'
              : 'border-border-default text-text-muted hover:border-border-gold hover:text-text-primary'"
            @click="toggleSpec(sp)"
          >{{ sp }}</button>
        </div>
        <input
          v-model="form.chosenSpec"
          type="text"
          placeholder="e.g. Holy, Frost, Balance…"
          class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
        />
      </div>

      <!-- Status (only for editing existing signup) -->
      <div v-if="existingSignup">
        <label class="block text-xs text-text-muted mb-1">Status *</label>
        <select
          v-model="form.status"
          class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none"
          required
        >
          <option value="going">Going ✓</option>
          <option value="tentative">Tentative ?</option>
          <option value="declined">Declined ✗</option>
          <option value="late">Late ⧖</option>
        </select>
      </div>

      <!-- Note -->
      <div>
        <label class="block text-xs text-text-muted mb-1">Note</label>
        <textarea
          v-model="form.note"
          rows="2"
          placeholder="Optional note…"
          class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none resize-none placeholder:text-text-muted/50"
        />
      </div>

      <WowButton type="submit" :loading="submitting" :disabled="form.characterId && roles.length === 0" class="w-full">
        {{ existingSignup ? 'Update Signup' : 'Sign Up' }}
      </WowButton>
    </form>

    <!-- Role Full dialog -->
    <WowModal v-model="showRoleFullModal" title="Role Slots Full" size="sm">
      <div class="space-y-3">
        <p class="text-text-muted text-sm">
          All <strong class="text-accent-gold">{{ roleFullLabel }}</strong> slots are full for this raid.
        </p>
        <p v-if="roleFullIsOfficer" class="text-text-muted text-sm">
          As an officer you can remove someone from this role in the Signups list, move them to bench, or select a different role below. You may also join the <strong class="text-yellow-400">bench</strong> yourself and wait for a slot to open.
        </p>
        <p v-else class="text-text-muted text-sm">
          You can join the <strong class="text-yellow-400">bench</strong> and you will be automatically moved in when a slot opens up, or select a different role.
        </p>
        <div v-if="alternativeRoles.length > 0" class="mt-2">
          <p class="text-xs text-text-muted mb-1">Available roles:</p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="r in alternativeRoles"
              :key="r.value"
              type="button"
              class="flex items-center gap-1.5 px-3 py-1.5 rounded border border-border-default text-xs text-text-muted hover:border-accent-gold hover:text-accent-gold transition-all"
              @click="switchRoleAndRetry(r.value)"
            >
              <RoleBadge :role="r.value" /> {{ r.label }}
            </button>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showRoleFullModal = false">Cancel</WowButton>
          <WowButton variant="primary" :loading="submitting" @click="forceBenchSignup">Join Bench</WowButton>
        </div>
      </template>
    </WowModal>
  </WowCard>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import RoleBadge from '@/components/common/RoleBadge.vue'
import * as signupsApi from '@/api/signups'
import * as charactersApi from '@/api/characters'
import { ROLE_OPTIONS, CLASS_ROLES } from '@/constants'

const ROLE_LABEL_MAP = { tank: 'Melee DPS', main_tank: 'Main Tank', off_tank: 'Off Tank', healer: 'Heal', dps: 'Range DPS' }

const props = defineProps({
  eventId: { type: [Number, String], required: true },
  guildId: { type: [Number, String], required: true },
  existingSignup: { type: Object, default: null },
  signedUpCharacterIds: { type: Array, default: () => [] },
  bannedCharacterIds: { type: Array, default: () => [] },
  availableRoles: { type: Array, default: () => ['main_tank', 'off_tank', 'tank', 'healer', 'dps'] },
  roleSlotInfo: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['signed-up', 'updated'])

const characters = ref([])
const submitting = ref(false)
const error = ref(null)
const success = ref(false)

// Role full modal state
const showRoleFullModal = ref(false)
const roleFullRole = ref('')
const roleFullSlots = ref({})
const roleFullCounts = ref({})
const roleFullIsOfficer = ref(false)

const roleFullLabel = computed(() => ROLE_LABEL_MAP[roleFullRole.value] || roleFullRole.value)

const alternativeRoles = computed(() => {
  // Show only roles that have available slots (not full) and are valid for the character's class
  return ROLE_OPTIONS.filter(r => {
    if (r.value === roleFullRole.value) return false
    if (!props.availableRoles.includes(r.value)) return false
    // Filter by class constraint
    if (classAllowedRoles.value && !classAllowedRoles.value.includes(r.value)) return false
    const maxSlots = roleFullSlots.value[r.value] ?? 0
    const currentCount = roleFullCounts.value[r.value] ?? 0
    return maxSlots > 0 && currentCount < maxSlots
  })
})

/** Allowed roles for the selected character's class */
const classAllowedRoles = computed(() => {
  if (!form.characterId) return null
  const selected = characters.value.find(c => String(c.id) === String(form.characterId))
  if (!selected || !selected.class_name) return null
  return CLASS_ROLES[selected.class_name] ?? null
})

const roles = computed(() =>
  ROLE_OPTIONS.filter(r => {
    if (!props.availableRoles.includes(r.value)) return false
    // If a character is selected, only show roles valid for their class
    if (classAllowedRoles.value && !classAllowedRoles.value.includes(r.value)) return false
    return true
  })
)

function isRoleFull(role) {
  const info = props.roleSlotInfo[role]
  return info ? info.remaining <= 0 : false
}

/** Available spec options from the selected character's own specs (max 2) */
const specOptions = computed(() => {
  if (!form.characterId) return []
  const selected = characters.value.find(c => String(c.id) === String(form.characterId))
  if (!selected) return []
  const specs = []
  if (selected.primary_spec) specs.push(selected.primary_spec)
  if (selected.secondary_spec) specs.push(selected.secondary_spec)
  return specs
})

/** Parse the comma-separated chosenSpec into an array for toggle button state */
const selectedSpecs = computed(() => {
  if (!form.chosenSpec) return []
  return form.chosenSpec.split(',').map(s => s.trim()).filter(Boolean)
})

/** Toggle a spec on/off in the multi-select list */
function toggleSpec(sp) {
  const current = selectedSpecs.value.slice()
  const idx = current.indexOf(sp)
  if (idx >= 0) {
    current.splice(idx, 1)
  } else {
    current.push(sp)
  }
  form.chosenSpec = current.join(', ')
}

/** Characters not yet signed up for this event (unless editing), excluding banned */
const availableCharacters = computed(() => {
  if (props.existingSignup) return characters.value
  return characters.value.filter(c =>
    !props.signedUpCharacterIds.includes(c.id) && !props.bannedCharacterIds.includes(c.id)
  )
})

/** Check if selected character is banned (for edge cases) */
const isCharBanned = computed(() => {
  return form.characterId && props.bannedCharacterIds.includes(Number(form.characterId))
})

const INITIAL_FORM = { characterId: '', chosenRole: '', chosenSpec: '', status: 'going', note: '' }

const form = reactive({ ...INITIAL_FORM })

onMounted(async () => {
  try {
    characters.value = await charactersApi.getMyCharacters(props.guildId)
  } catch {
    // ignore – user may have no characters yet
  }
})

// Auto-fill role & spec from selected character
function onCharacterChange() {
  const charId = form.characterId
  if (!charId) return
  const selected = characters.value.find(c => String(c.id) === String(charId))
  if (selected && !props.existingSignup) {
    // Only auto-fill role if it's valid for the character's class
    const allowed = CLASS_ROLES[selected.class_name] ?? []
    const defaultRole = selected.default_role || ''
    form.chosenRole = allowed.includes(defaultRole) ? defaultRole : ''
    form.chosenSpec = selected.primary_spec || ''
  }
}

// Populate form if editing existing signup
watch(
  () => props.existingSignup,
  (s) => {
    if (s) {
      form.characterId = s.character_id ?? ''
      form.chosenRole  = s.chosen_role   ?? ''
      form.chosenSpec  = s.chosen_spec   ?? ''
      form.status      = s.status        ?? 'going'
      form.note        = s.note          ?? ''
    } else {
      // Reset form when editing ends so spec doesn't persist from previous character
      Object.assign(form, INITIAL_FORM)
    }
  },
  { immediate: true }
)

async function handleSubmit() {
  if (!form.characterId) { error.value = 'Please select a character'; return }
  if (!form.chosenRole)  { error.value = 'Please select a role'; return }

  error.value = null
  success.value = false
  submitting.value = true

  const payload = {
    character_id: form.characterId,
    chosen_role:  form.chosenRole,
    chosen_spec:  form.chosenSpec || undefined,
    note:         form.note || undefined
  }

  // Auto-bench when player knowingly selects a full role
  if (!props.existingSignup && isRoleFull(form.chosenRole)) {
    payload.force_bench = true
  }

  // Only include status when updating an existing signup
  if (props.existingSignup) {
    payload.status = form.status
  }

  try {
    if (props.existingSignup) {
      const updated = await signupsApi.updateSignup(props.guildId, props.eventId, props.existingSignup.id, payload)
      emit('updated', updated)
    } else {
      const created = await signupsApi.createSignup(props.guildId, props.eventId, payload)
      emit('signed-up', created)
      // Reset form for adding another character
      Object.assign(form, INITIAL_FORM)
    }
    success.value = true
    setTimeout(() => { success.value = false }, 3000)
  } catch (err) {
    const data = err?.response?.data
    if (err?.response?.status === 409 && data?.error === 'role_full') {
      // Role is full — show modal with bench/change options
      roleFullRole.value = data.role
      roleFullSlots.value = data.role_slots || {}
      roleFullCounts.value = data.role_counts || {}
      roleFullIsOfficer.value = !!data.is_officer
      showRoleFullModal.value = true
    } else {
      error.value = data?.message ?? 'Failed to submit signup'
    }
  } finally {
    submitting.value = false
  }
}

/** User chose to go to bench despite role being full */
async function forceBenchSignup() {
  error.value = null
  submitting.value = true

  const payload = {
    character_id: form.characterId,
    chosen_role:  form.chosenRole,
    chosen_spec:  form.chosenSpec || undefined,
    note:         form.note || undefined,
    force_bench:  true,
  }

  try {
    const created = await signupsApi.createSignup(props.guildId, props.eventId, payload)
    emit('signed-up', created)
    Object.assign(form, INITIAL_FORM)
    showRoleFullModal.value = false
    success.value = true
    setTimeout(() => { success.value = false }, 3000)
  } catch (err) {
    error.value = err?.response?.data?.message ?? 'Failed to submit signup'
    showRoleFullModal.value = false
  } finally {
    submitting.value = false
  }
}

/** User chose to switch role and retry signup */
function switchRoleAndRetry(newRole) {
  form.chosenRole = newRole
  showRoleFullModal.value = false
  handleSubmit()
}
</script>
