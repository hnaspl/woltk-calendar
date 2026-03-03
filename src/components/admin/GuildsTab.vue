<template>
  <div class="space-y-6">
    <!-- Guilds table -->
    <WowCard>
      <div class="flex items-center justify-between mb-4">
        <h2 class="wow-heading text-base">{{ t('admin.guilds.title', { count: guilds.length }) }}</h2>
      </div>

      <div v-if="loading" class="h-48 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="error" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ error }}</div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-bg-tertiary border-b border-border-default">
              <th class="hidden sm:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.users.id') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.guilds.name') }}</th>
              <th class="hidden md:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.guilds.realm') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.guilds.members') }}</th>
              <th class="hidden lg:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.guilds.owner') }}</th>
              <th class="hidden lg:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.guilds.created') }}</th>
              <th class="text-right px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.labels.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-default">
            <tr v-for="g in guilds" :key="g.id" class="hover:bg-bg-tertiary/50 transition-colors">
              <td class="hidden sm:table-cell px-4 py-2.5 text-text-muted">{{ g.id }}</td>
              <td class="px-4 py-2.5">
                <div class="text-text-primary font-medium">{{ g.name }}</div>
                <div v-if="g.faction" class="text-xs text-text-muted">{{ g.faction }}</div>
              </td>
              <td class="hidden md:table-cell px-4 py-2.5 text-text-muted">{{ g.realm_name }}</td>
              <td class="px-4 py-2.5">
                <span class="text-accent-gold font-medium">{{ g.member_count }}</span>
              </td>
              <td class="hidden lg:table-cell px-4 py-2.5 text-text-muted">{{ g.creator_username || '—' }}</td>
              <td class="hidden lg:table-cell px-4 py-2.5 text-text-muted text-xs">{{ formatDate(g.created_at) }}</td>
              <td class="px-4 py-2.5 text-right">
                <WowButton variant="secondary" class="text-xs py-1 px-2" @click="viewMembers(g)">{{ t('admin.guilds.viewMembers') }}</WowButton>
              </td>
            </tr>
            <tr v-if="!guilds.length">
              <td colspan="7" class="px-4 py-8 text-center text-text-muted">{{ t('admin.guilds.noGuilds') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </WowCard>

    <!-- Guild Members Modal -->
    <WowModal v-model="showMembersModal" :title="selectedGuild ? `${selectedGuild.name} — ${t('common.labels.members')}` : t('common.labels.members')" size="lg">
      <div v-if="membersLoading" class="h-32 rounded-lg bg-bg-secondary border border-border-default loading-pulse" />
      <div v-else-if="membersError" class="p-4 rounded bg-red-900/30 border border-red-600 text-red-300 text-sm">{{ membersError }}</div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-bg-tertiary border-b border-border-default">
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.username') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.role') }}</th>
              <th class="text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('common.fields.status') }}</th>
              <th class="hidden sm:table-cell text-left px-4 py-2.5 text-xs text-text-muted uppercase">{{ t('admin.guilds.joined') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-default">
            <tr v-for="m in guildMembers" :key="m.user_id" class="hover:bg-bg-tertiary/50 transition-colors">
              <td class="px-4 py-2.5 text-text-primary font-medium">{{ m.username || `User #${m.user_id}` }}</td>
              <td class="px-4 py-2.5">
                <span class="inline-block px-2 py-0.5 text-xs rounded-full font-medium bg-bg-tertiary border border-border-default text-text-muted">
                  {{ m.role }}
                </span>
              </td>
              <td class="px-4 py-2.5">
                <span
                  class="inline-block px-2 py-0.5 text-xs rounded-full font-medium"
                  :class="m.status === 'active' ? 'bg-green-900/50 text-green-300 border border-green-600' : 'bg-yellow-900/50 text-yellow-300 border border-yellow-600'"
                >{{ m.status }}</span>
              </td>
              <td class="hidden sm:table-cell px-4 py-2.5 text-text-muted text-xs">{{ formatDate(m.joined_at) }}</td>
            </tr>
            <tr v-if="!guildMembers.length">
              <td colspan="4" class="px-4 py-4 text-center text-text-muted">{{ t('admin.guilds.noMembers') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <template #footer>
        <WowButton variant="secondary" @click="showMembersModal = false">{{ t('common.buttons.close') }}</WowButton>
      </template>
    </WowModal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import WowButton from '@/components/common/WowButton.vue'
import WowModal from '@/components/common/WowModal.vue'
import { useUiStore } from '@/stores/ui'
import * as guildsApi from '@/api/guilds'

const { t } = useI18n()
const uiStore = useUiStore()

const guilds = ref([])
const loading = ref(true)
const error = ref(null)

const showMembersModal = ref(false)
const selectedGuild = ref(null)
const guildMembers = ref([])
const membersLoading = ref(false)
const membersError = ref(null)

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

onMounted(async () => {
  loading.value = true
  try {
    guilds.value = await guildsApi.adminGetAllGuilds()
  } catch (err) {
    error.value = err?.response?.data?.message ?? t('admin.guilds.loadError')
  } finally {
    loading.value = false
  }
})

async function viewMembers(guild) {
  selectedGuild.value = guild
  guildMembers.value = []
  membersError.value = null
  membersLoading.value = true
  showMembersModal.value = true
  try {
    guildMembers.value = await guildsApi.adminGetGuildMembers(guild.id)
  } catch (err) {
    membersError.value = err?.response?.data?.message ?? t('admin.guilds.loadError')
  } finally {
    membersLoading.value = false
  }
}
</script>
