<template>
  <div class="space-y-6">
    <div v-if="eventSections.length === 0" class="px-4 py-8 text-center text-text-muted">
      No attendance data available.
    </div>

    <div v-for="section in eventSections" :key="section.eventId">
      <!-- Event date header -->
      <div class="flex items-center gap-3 mb-2">
        <h3 class="text-base font-semibold text-border-gold">{{ formatDate(section.date) }}</h3>
        <span class="text-sm text-text-muted">{{ section.title }}</span>
      </div>

      <WowCard :padded="false">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-bg-tertiary border-b border-border-default">
                <th class="text-left px-4 py-3 text-xs text-text-muted uppercase tracking-wider">Character</th>
                <th class="text-left px-4 py-3 text-xs text-text-muted uppercase tracking-wider">Class</th>
                <th class="text-left px-4 py-3 text-xs text-text-muted uppercase tracking-wider">Status</th>
                <th class="text-left px-4 py-3 text-xs text-text-muted uppercase tracking-wider">Note</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border-default">
              <tr
                v-for="row in section.rows"
                :key="row.characterId"
                class="hover:bg-bg-tertiary/50 transition-colors"
              >
                <td class="px-4 py-2.5 font-medium text-text-primary">{{ row.characterName }}</td>
                <td class="px-4 py-2.5">
                  <ClassBadge :class-name="row.className" />
                </td>
                <td class="px-4 py-2.5">
                  <span
                    class="inline-flex items-center gap-1 text-xs font-semibold"
                    :class="outcomeClass(row.outcome)"
                  >{{ outcomeLabel(row.outcome) }}</span>
                </td>
                <td class="px-4 py-2.5 text-text-muted text-xs">{{ row.note || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </WowCard>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import ClassBadge from '@/components/common/ClassBadge.vue'

const props = defineProps({
  records: { type: Array, default: () => [] },
  events:  { type: Array, default: () => [] }
})

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-GB', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
}

function outcomeLabel(o) {
  if (o === 'attended') return 'Attended'
  if (o === 'late') return 'Late'
  return 'Unattended'
}

function outcomeClass(o) {
  if (o === 'attended') return 'text-green-400'
  if (o === 'late') return 'text-yellow-400'
  return 'text-red-400'
}

const eventSections = computed(() => {
  // Build a lookup for events by id
  const eventMap = new Map()
  props.events.forEach(ev => eventMap.set(ev.id, ev))

  // Group records by event
  const grouped = new Map()
  props.records.forEach(r => {
    const eid = r.raid_event_id ?? r.event_id
    if (!grouped.has(eid)) grouped.set(eid, [])
    grouped.get(eid).push(r)
  })

  // Build sections sorted by event date (most recent first)
  return Array.from(grouped.entries())
    .map(([eid, recs]) => {
      const ev = eventMap.get(eid)
      return {
        eventId: eid,
        title: ev?.title ?? 'Raid',
        date: ev?.starts_at_utc ?? null,
        rows: recs.map(r => ({
          characterId: r.character_id,
          characterName: r.character?.name ?? 'Unknown',
          className: r.character?.class_name ?? '',
          outcome: r.outcome,
          note: r.note
        }))
      }
    })
    .sort((a, b) => {
      if (!a.date || !b.date) return 0
      return new Date(b.date) - new Date(a.date)
    })
})
</script>
