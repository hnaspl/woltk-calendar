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
            v-for="char in characters"
            :key="char.id"
            :value="char.id"
          >
            {{ char.name }} ({{ char.class_name }} – {{ char.realm_name }})
          </option>
        </select>
      </div>

      <!-- Role -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <label class="text-xs text-text-muted">Role *</label>
          <button
            v-if="!editingRoleSpec && form.characterId"
            type="button"
            class="text-xs text-accent-gold hover:text-yellow-300 transition-colors"
            @click="editingRoleSpec = true"
          >Edit</button>
          <span v-if="editingRoleSpec" class="text-xs text-text-muted italic">Custom role/spec</span>
        </div>
        <div class="flex gap-2">
          <button
            v-for="r in roles"
            :key="r.value"
            type="button"
            class="flex-1 flex items-center justify-center gap-1.5 py-2 rounded border text-sm transition-all"
            :class="form.chosenRole === r.value
              ? 'bg-accent-gold/10 border-accent-gold text-accent-gold'
              : 'border-border-default text-text-muted hover:border-border-gold hover:text-text-primary'"
            :disabled="!editingRoleSpec && form.characterId !== ''"
            @click="form.chosenRole = r.value"
          >
            <RoleBadge :role="r.value" />
          </button>
        </div>
      </div>

      <!-- Spec -->
      <div>
        <label class="block text-xs text-text-muted mb-1">Spec</label>
        <input
          v-model="form.chosenSpec"
          type="text"
          placeholder="e.g. Holy, Frost, Balance…"
          class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none placeholder:text-text-muted/50"
          :disabled="!editingRoleSpec && form.characterId !== ''"
        />
      </div>

      <!-- Status -->
      <div>
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
          <option value="bench">Bench</option>
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
import { ref, reactive, watch, onMounted } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import RoleBadge from '@/components/common/RoleBadge.vue'
import * as signupsApi from '@/api/signups'
import * as charactersApi from '@/api/characters'

const props = defineProps({
  eventId: { type: [Number, String], required: true },
  guildId: { type: [Number, String], required: true },
  existingSignup: { type: Object, default: null }
})

const emit = defineEmits(['signed-up', 'updated'])

const characters = ref([])
const submitting = ref(false)
const error = ref(null)
const success = ref(false)
const editingRoleSpec = ref(false)

const roles = [
  { value: 'tank' },
  { value: 'healer' },
  { value: 'dps' }
]

const form = reactive({
  characterId: '',
  chosenRole: 'dps',
  chosenSpec: '',
  status: 'going',
  note: ''
})

onMounted(async () => {
  try {
    characters.value = await charactersApi.getMyCharacters(props.guildId)
  } catch {
    // ignore – user may have no characters yet
  }
})

// Auto-fill role & spec from selected character
function onCharacterChange() {
  const selected = characters.value.find(c => c.id === Number(form.characterId))
  if (selected && !props.existingSignup) {
    form.chosenRole = selected.default_role || 'dps'
    form.chosenSpec = selected.primary_spec || ''
    editingRoleSpec.value = false
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
      editingRoleSpec.value = true
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
    status:       form.status,
    note:         form.note || undefined
  }

  try {
    if (props.existingSignup) {
      const updated = await signupsApi.updateSignup(props.guildId, props.eventId, props.existingSignup.id, payload)
      emit('updated', updated)
    } else {
      const created = await signupsApi.createSignup(props.guildId, props.eventId, payload)
      emit('signed-up', created)
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
