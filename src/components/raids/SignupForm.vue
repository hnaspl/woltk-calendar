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
      </div>

      <!-- Role -->
      <div>
        <label class="text-xs text-text-muted mb-1 block">Role *</label>
        <div class="flex gap-2">
          <button
            v-for="r in roles"
            :key="r.value"
            type="button"
            class="flex-1 flex items-center justify-center gap-1.5 py-2 rounded border text-sm transition-all"
            :class="form.chosenRole === r.value
              ? 'bg-accent-gold/10 border-accent-gold text-accent-gold'
              : 'border-border-default text-text-muted hover:border-border-gold hover:text-text-primary'"
            :disabled="form.characterId !== ''"
            @click="form.chosenRole = r.value"
          >
            <RoleBadge :role="r.value" />
          </button>
        </div>
      </div>

      <!-- Spec -->
      <div>
        <label class="block text-xs text-text-muted mb-1">Spec</label>
        <div v-if="specOptions.length > 0" class="flex gap-2 mb-1">
          <button
            v-for="sp in specOptions"
            :key="sp"
            type="button"
            class="px-3 py-1.5 rounded border text-xs transition-all"
            :class="form.chosenSpec === sp
              ? 'bg-accent-gold/10 border-accent-gold text-accent-gold'
              : 'border-border-default text-text-muted hover:border-border-gold hover:text-text-primary'"
            @click="form.chosenSpec = sp"
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

      <WowButton type="submit" :loading="submitting" class="w-full">
        {{ existingSignup ? 'Update Signup' : 'Sign Up' }}
      </WowButton>
    </form>
  </WowCard>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import RoleBadge from '@/components/common/RoleBadge.vue'
import * as signupsApi from '@/api/signups'
import * as charactersApi from '@/api/characters'
import { ROLE_OPTIONS, CLASS_SPECS } from '@/constants'

const props = defineProps({
  eventId: { type: [Number, String], required: true },
  guildId: { type: [Number, String], required: true },
  existingSignup: { type: Object, default: null },
  signedUpCharacterIds: { type: Array, default: () => [] }
})

const emit = defineEmits(['signed-up', 'updated'])

const characters = ref([])
const submitting = ref(false)
const error = ref(null)
const success = ref(false)

const roles = ROLE_OPTIONS

/** Available spec options from the selected character's class */
const specOptions = computed(() => {
  if (!form.characterId) return []
  const selected = characters.value.find(c => String(c.id) === String(form.characterId))
  if (!selected) return []
  return CLASS_SPECS[selected.class_name] || []
})

/** Characters not yet signed up for this event (unless editing) */
const availableCharacters = computed(() => {
  if (props.existingSignup) return characters.value
  return characters.value.filter(c => !props.signedUpCharacterIds.includes(c.id))
})

const INITIAL_FORM = { characterId: '', chosenRole: 'dps', chosenSpec: '', status: 'going', note: '' }

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
    form.chosenRole = selected.default_role || 'dps'
    form.chosenSpec = selected.primary_spec || ''
  }
}

// Populate form if editing existing signup
watch(
  () => props.existingSignup,
  (s) => {
    if (s) {
      form.characterId = s.character_id ?? ''
      form.chosenRole  = s.chosen_role   ?? 'dps'
      form.chosenSpec  = s.chosen_spec   ?? ''
      form.status      = s.status        ?? 'going'
      form.note        = s.note          ?? ''
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
    error.value = err?.response?.data?.message ?? 'Failed to submit signup'
  } finally {
    submitting.value = false
  }
}
</script>
