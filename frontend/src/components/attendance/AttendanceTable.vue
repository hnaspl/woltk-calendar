<template>
  <WowCard :padded="false">
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="bg-bg-tertiary border-b border-border-default">
            <th class="text-left px-4 py-3 text-xs text-text-muted uppercase tracking-wider">Character</th>
            <th class="text-left px-4 py-3 text-xs text-text-muted uppercase tracking-wider">Class</th>
            <th
              v-for="ev in events"
              :key="ev.id"
              class="text-center px-2 py-3 text-xs text-text-muted min-w-[80px]"
            >
              <WowTooltip :text="ev.title" position="bottom">
                <div class="truncate max-w-[70px] mx-auto">{{ formatDate(ev.date ?? ev.start_time) }}</div>
              </WowTooltip>
            </th>
            <th class="text-center px-4 py-3 text-xs text-text-muted uppercase tracking-wider">%</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border-default">
          <tr
            v-for="row in tableRows"
            :key="row.characterId"
            class="hover:bg-bg-tertiary/50 transition-colors"
          >
            <td class="px-4 py-2.5 font-medium text-text-primary">{{ row.characterName }}</td>
            <td class="px-4 py-2.5">
              <ClassBadge :class-name="row.class" />
            </td>
            <td
              v-for="ev in events"
              :key="ev.id"
              class="px-2 py-2.5 text-center"
            >
              <span
                v-if="row.attended.has(ev.id)"
                class="inline-block w-5 h-5 rounded-full bg-green-500/20 border border-green-500 text-green-400 text-xs leading-5"
                title="Present"
              >✓</span>
              <span
                v-else-if="row.signedUp.has(ev.id)"
                class="inline-block w-5 h-5 rounded-full bg-red-500/20 border border-red-500 text-red-400 text-xs leading-5"
                title="Absent"
              >✗</span>
              <span v-else class="text-border-default">–</span>
            </td>
            <td class="px-4 py-2.5 text-center">
              <span
                class="font-semibold"
                :class="row.pct >= 75 ? 'text-green-400' : row.pct >= 50 ? 'text-yellow-400' : 'text-red-400'"
              >{{ row.pct }}%</span>
            </td>
          </tr>
          <tr v-if="tableRows.length === 0">
            <td :colspan="events.length + 3" class="px-4 py-8 text-center text-text-muted">
              No attendance data available.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </WowCard>
</template>

<script setup>
import { computed } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import ClassBadge from '@/components/common/ClassBadge.vue'
import WowTooltip from '@/components/common/WowTooltip.vue'

const props = defineProps({
  records: { type: Array, default: () => [] }, // attendance records
  events:  { type: Array, default: () => [] }, // raid events
  signups: { type: Array, default: () => [] }  // all signups across events
})

function formatDate(d) {
  if (!d) return '?'
  return new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
}

const tableRows = computed(() => {
  // Build a map: characterId → { name, class, attended: Set<eventId>, signedUp: Set<eventId> }
  const charMap = new Map()

  props.signups.forEach(su => {
    const cid = su.character_id ?? su.character?.id
    if (!cid) return
    if (!charMap.has(cid)) {
      charMap.set(cid, {
        characterId: cid,
        characterName: su.character?.name ?? '?',
        class: su.character?.class ?? '',
        attended: new Set(),
        signedUp: new Set()
      })
    }
    charMap.get(cid).signedUp.add(su.event_id)
  })

  props.records.forEach(r => {
    const cid = r.character_id
    if (!cid) return
    if (!charMap.has(cid)) {
      charMap.set(cid, {
        characterId: cid,
        characterName: r.character?.name ?? '?',
        class: r.character?.class ?? '',
        attended: new Set(),
        signedUp: new Set()
      })
    }
    if (r.attended) charMap.get(cid).attended.add(r.event_id)
  })

  return Array.from(charMap.values()).map(row => {
    const total = row.signedUp.size || 1
    const pct = Math.round((row.attended.size / total) * 100)
    return { ...row, pct }
  }).sort((a, b) => b.pct - a.pct)
})
</script>
