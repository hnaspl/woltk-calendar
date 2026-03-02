<template>
  <div class="space-y-6">
    <div v-if="eventSections.length === 0" class="px-4 py-8 text-center text-text-muted">
      No attendance data available.
    </div>

    <div v-for="section in eventSections" :key="section.eventId">
      <!-- Event date header -->
      <div class="flex items-center gap-3 mb-2 flex-wrap">
        <h3 class="text-base font-semibold text-border-gold">{{ formatDate(section.date) }}</h3>
        <span class="text-sm text-text-muted">{{ section.title }}</span>
      </div>

      <WowCard :padded="false">
        <!-- Desktop table (hidden on small screens) -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="w-full text-sm table-fixed">
            <thead>
              <tr class="bg-bg-tertiary border-b border-border-default">
                <th class="text-left px-4 py-3 text-xs text-text-muted uppercase tracking-wider w-[35%]">Character</th>
                <th class="text-left px-4 py-3 text-xs text-text-muted uppercase tracking-wider w-[20%]">Class</th>
                <th class="text-left px-4 py-3 text-xs text-text-muted uppercase tracking-wider w-[15%]">Status</th>
                <th class="text-left px-4 py-3 text-xs text-text-muted uppercase tracking-wider w-[30%]">Note</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border-default">
              <tr
                v-for="row in section.rows"
                :key="row.characterId"
                class="hover:bg-bg-tertiary/50 transition-colors"
              >
                <td class="px-4 py-2.5">
                  <div class="flex items-center gap-2">
                    <img
                      :src="getClassIcon(row.className)"
                      :alt="row.className"
                      class="w-5 h-5 rounded flex-shrink-0"
                    />
                    <span class="font-medium truncate" :style="{ color: getClassColor(row.className) }">{{ row.characterName }}</span>
                  </div>
                </td>
                <td class="px-4 py-2.5">
                  <ClassBadge :class-name="row.className" />
                </td>
                <td class="px-4 py-2.5">
                  <span
                    class="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded"
                    :class="outcomeClasses(row.outcome)"
                  >{{ outcomeLabel(row.outcome) }}</span>
                </td>
                <td class="px-4 py-2.5 text-text-muted text-xs truncate">{{ row.note || '—' }}</td>
              </tr>
              <tr class="bg-bg-tertiary/30">
                <td colspan="4" class="px-4 py-2.5 text-right">
                  <router-link
                    :to="`/raids/${section.eventId}`"
                    class="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded border border-accent-gold/40 bg-accent-gold/10 text-accent-gold hover:bg-accent-gold/20 hover:border-accent-gold transition-colors whitespace-nowrap"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                    </svg>
                    View Raid Details
                  </router-link>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Mobile card layout (hidden on larger screens) -->
        <div class="sm:hidden divide-y divide-border-default">
          <div
            v-for="row in section.rows"
            :key="row.characterId"
            class="px-4 py-3 flex items-center gap-3"
          >
            <img
              :src="getClassIcon(row.className)"
              :alt="row.className"
              class="w-7 h-7 rounded flex-shrink-0"
            />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-medium text-sm truncate" :style="{ color: getClassColor(row.className) }">{{ row.characterName }}</span>
                <span
                  class="text-[10px] font-semibold px-1.5 py-0.5 rounded"
                  :class="outcomeClasses(row.outcome)"
                >{{ outcomeLabel(row.outcome) }}</span>
              </div>
              <div class="text-text-muted text-xs mt-0.5">{{ row.className }}</div>
              <div v-if="row.note" class="text-text-muted text-[10px] italic mt-0.5">{{ row.note }}</div>
            </div>
          </div>
          <div class="px-4 py-3 bg-bg-tertiary/30 text-right">
            <router-link
              :to="`/raids/${section.eventId}`"
              class="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded border border-accent-gold/40 bg-accent-gold/10 text-accent-gold hover:bg-accent-gold/20 hover:border-accent-gold transition-colors"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
              </svg>
              View Raid Details
            </router-link>
          </div>
        </div>
      </WowCard>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import WowCard from '@/components/common/WowCard.vue'
import ClassBadge from '@/components/common/ClassBadge.vue'
import { useTimezone } from '@/composables/useTimezone'
import { useWowIcons } from '@/composables/useWowIcons'

const tz = useTimezone()
const { getClassIcon, getClassColor } = useWowIcons()

const props = defineProps({
  records: { type: Array, default: () => [] },
  events:  { type: Array, default: () => [] }
})

function formatDate(d) {
  if (!d) return '—'
  return tz.formatGuildDate(d, { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
}

function outcomeLabel(o) {
  if (o === 'attended') return 'Attended'
  if (o === 'late') return 'Late'
  return 'Unattended'
}

function outcomeClasses(o) {
  if (o === 'attended') return 'text-green-400 bg-green-400/10'
  if (o === 'late') return 'text-yellow-400 bg-yellow-400/10'
  return 'text-red-400 bg-red-400/10'
}

const eventSections = computed(() => {
  const eventMap = new Map()
  props.events.forEach(ev => eventMap.set(ev.id, ev))

  const grouped = new Map()
  props.records.forEach(r => {
    const eid = r.raid_event_id ?? r.event_id
    if (!grouped.has(eid)) grouped.set(eid, [])
    grouped.get(eid).push(r)
  })

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
