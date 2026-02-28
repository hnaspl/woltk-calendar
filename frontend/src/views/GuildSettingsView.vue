<template>
  <AppShell>
    <div class="p-4 md:p-6 space-y-6">
      <h1 class="wow-heading text-2xl">Guild Settings</h1>

      <div v-if="loading" class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="error" class="p-4 rounded-lg bg-red-900/30 border border-red-600 text-red-300">{{ error }}</div>

      <template v-else>
        <!-- Guild info form -->
        <WowCard>
          <h2 class="wow-heading text-base mb-4">Guild Information</h2>
          <form @submit.prevent="saveGuild" class="space-y-4 max-w-lg">
            <div>
              <label class="block text-xs text-text-muted mb-1">Guild Name *</label>
              <input v-model="form.name" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none" />
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">Realm *</label>
              <select v-model="form.realm" required class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none">
                <option value="">Select realm…</option>
                <option v-for="r in warmaneRealms" :key="r" :value="r">{{ r }}</option>
              </select>
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">Description</label>
              <textarea v-model="form.description" rows="3" class="w-full bg-bg-tertiary border border-border-default text-text-primary rounded px-3 py-2 text-sm focus:border-border-gold outline-none resize-none" />
            </div>
            <div v-if="saveError" class="p-3 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ saveError }}</div>
            <WowButton type="submit" :loading="saving">Save Changes</WowButton>
          </form>
        </WowCard>

        <!-- Members table -->
        <WowCard>
          <div class="flex items-center justify-between mb-4">
            <h2 class="wow-heading text-base">Members ({{ members.length }})</h2>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-bg-tertiary border-b border-border-default">
                  <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Username</th>
                  <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">Role</th>
                  <th class="text-right px-4 py-2.5 text-xs text-text-muted uppercase">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-default">
                <tr v-for="m in members" :key="m.id" class="hover:bg-bg-tertiary/50 transition-colors">
                  <td class="px-4 py-2.5 text-text-primary font-medium">{{ m.username ?? m.user?.username }}</td>
                  <td class="px-4 py-2.5">
                    <select
                      :value="m.role"
                      class="bg-bg-tertiary border border-border-default text-text-primary text-xs rounded px-2 py-1 focus:border-border-gold outline-none"
                      @change="updateRole(m, $event.target.value)"
                    >
                      <option value="member">Member</option>
                      <option value="officer">Officer</option>
                      <option value="admin">Admin</option>
                    </select>
                  </td>
                  <td class="px-4 py-2.5 text-right">
                    <WowButton variant="danger" class="text-xs py-1 px-2" @click="confirmKick(m)">
                      Remove
                    </WowButton>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </WowCard>
      </template>
    </div>

    <!-- Kick confirmation -->
    <WowModal v-model="showKickConfirm" title="Remove Member" size="sm">
      <p class="text-text-muted">Remove <strong class="text-text-primary">{{ kickTarget?.username ?? kickTarget?.user?.username }}</strong> from the guild?</p>
      <template #footer>
        <div class="flex justify-end gap-3">
          <WowButton variant="secondary" @click="showKickConfirm = false">Cancel</WowButton>
          <WowButton variant="danger" :loading="saving" @click="doKick">Remove</WowButton>
        </div>
      </template>
    </WowModal>
  </AppShell>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import { useGuildStore } from '@/stores/guild'
import { useUiStore } from '@/stores/ui'
import * as guildsApi from '@/api/guilds'

const guildStore = useGuildStore()
const uiStore = useUiStore()

const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const saveError = ref(null)
const members = ref([])
const showKickConfirm = ref(false)
const kickTarget = ref(null)

const form = reactive({ name: '', realm: '', description: '' })
const warmaneRealms = ['Icecrown', 'Lordaeron', 'Onyxia', 'Blackrock', 'Frostwolf', 'Frostmourne', 'Neltharion']

onMounted(async () => {
  loading.value = true
  try {
    if (!guildStore.currentGuild) await guildStore.fetchGuilds()
    const g = guildStore.currentGuild
    if (g) {
      Object.assign(form, { name: g.name ?? '', realm: g.realm ?? '', description: g.description ?? '' })
      await guildStore.fetchMembers(g.id)
      members.value = guildStore.members
    }
  } catch {
    error.value = 'Failed to load guild settings'
  } finally {
    loading.value = false
  }
})

async function saveGuild() {
  saveError.value = null
  saving.value = true
  try {
    const updated = await guildsApi.updateGuild(guildStore.currentGuild.id, form)
    guildStore.currentGuild = updated
    uiStore.showToast('Guild settings saved', 'success')
  } catch (err) {
    saveError.value = err?.response?.data?.message ?? 'Failed to save'
  } finally {
    saving.value = false
  }
}

async function updateRole(member, role) {
  try {
    await guildsApi.updateMemberRole(guildStore.currentGuild.id, member.id, role)
    member.role = role
    uiStore.showToast('Role updated', 'success')
  } catch {
    uiStore.showToast('Failed to update role', 'error')
  }
}

function confirmKick(member) {
  kickTarget.value = member
  showKickConfirm.value = true
}

async function doKick() {
  saving.value = true
  try {
    await guildsApi.removeMember(guildStore.currentGuild.id, kickTarget.value.id)
    members.value = members.value.filter(m => m.id !== kickTarget.value.id)
    showKickConfirm.value = false
    uiStore.showToast('Member removed', 'success')
  } catch {
    uiStore.showToast('Failed to remove member', 'error')
  } finally {
    saving.value = false
  }
}
</script>
