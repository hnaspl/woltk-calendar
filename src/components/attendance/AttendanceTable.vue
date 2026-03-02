<template>
  <div class="space-y-6">
    <div v-if="dateSections.length === 0" class="px-4 py-8 text-center text-text-muted">
      {{ t('attendance.noData') }}
    </div>

    <div v-for="section in dateSections" :key="section.dateKey">
      <!-- Date header -->
      <div class="mb-2">
        <h3 class="text-base font-semibold text-border-gold">{{ section.dateLabel }}</h3>
      </div>

      <WowCard :padded="false">
        <!-- Desktop table (hidden on small screens) -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="w-full text-sm table-fixed">
            <thead>
              <tr class="bg-bg-tertiary border-b border-border-default">
                <th class="text-left px-4 py-3 text-xs text-text-muted uppercase tracking-wider w-[28%]">{{ t('attendance.raidColumn') }}</th>
                <th class="text-left px-4 py-3 text-xs text-text-muted uppercase tracking-wider w-[22%]">{{ t('attendance.character') }}</th>
                <th class="text-left px-4 py-3 text-xs text-text-muted uppercase tracking-wider w-[15%]">{{ t('attendance.class') }}</th>
                <th class="text-left px-4 py-3 text-xs text-text-muted uppercase tracking-wider w-[12%]">{{ t('attendance.statusColumn') }}</th>
                <th class="text-left px-4 py-3 text-xs text-text-muted uppercase tracking-wider w-[23%]">{{ t('attendance.note') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border-default">
              <tr
                v-for="row in section.rows"
                :key="row.recordId"
                class="hover:bg-bg-tertiary/50 transition-colors"
              >
                <td class="px-4 py-2.5">
                  <router-link :to="`/raids/${row.eventId}`" class="flex items-center gap-2 hover:text-accent-gold transition-colors group">
                    <img
                      :src="getRaidIcon(row.raidType)"
                      :alt="row.raidTitle"
                      class="w-6 h-6 rounded border border-border-default flex-shrink-0"
                    />
                    <span class="font-medium truncate text-accent-gold">{{ row.raidTitle }}</span>
                  </router-link>
                </td>
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
            </tbody>
          </table>
        </div>

        <!-- Mobile card layout (hidden on larger screens) -->
        <div class="sm:hidden divide-y divide-border-default">
          <div
            v-for="row in section.rows"
            :key="`m-${row.recordId}`"
            class="px-4 py-3 flex items-center gap-3"
          >
            <img
              :src="getRaidIcon(row.raidType)"
              :alt="row.raidTitle"
              class="w-8 h-8 rounded border border-border-default flex-shrink-0"
            />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <router-link :to="`/raids/${row.eventId}`" class="font-medium text-sm truncate text-accent-gold">{{ row.raidTitle }}</router-link>
                <span
                  class="text-[10px] font-semibold px-1.5 py-0.5 rounded"
                  :class="outcomeClasses(row.outcome)"
                >{{ outcomeLabel(row.outcome) }}</span>
              </div>
              <div class="flex items-center gap-1.5 mt-0.5">
                <img :src="getClassIcon(row.className)" :alt="row.className" class="w-4 h-4 rounded flex-shrink-0" />
                <span class="text-xs truncate" :style="{ color: getClassColor(row.className) }">{{ row.characterName }}</span>
                <span class="text-text-muted text-xs">·</span>
                <span class="text-text-muted text-xs">{{ row.className }}</span>
              </div>
              <div v-if="row.note" class="text-text-muted text-[10px] italic mt-0.5">{{ row.note }}</div>
            </div>
          </div>
        </div>
      </WowCard>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import WowCard from '@/components/common/WowCard.vue'
import ClassBadge from '@/components/common/ClassBadge.vue'
import { useTimezone } from '@/composables/useTimezone'
import { useWowIcons } from '@/composables/useWowIcons'

const { t } = useI18n()

const tz = useTimezone()
const { getClassIcon, getClassColor, getRaidIcon } = useWowIcons()

const props = defineProps({
  records: { type: Array, default: () => [] },
  events:  { type: Array, default: () => [] }
})

function formatDate(d) {
  if (!d) return '—'
  return tz.formatGuildDate(d, { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
}

/** Get guild-timezone date string (YYYY-MM-DD) for grouping. */
function guildDateKey(isoStr) {
  if (!isoStr) return 'no-date'
  return tz.formatGuildDate(isoStr, { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function outcomeLabel(o) {
  if (o === 'attended') return t('attendance.attended')
  if (o === 'late') return t('attendance.late')
  return t('attendance.unattended')
}

function outcomeClasses(o) {
  if (o === 'attended') return 'text-green-400 bg-green-400/10'
  if (o === 'late') return 'text-yellow-400 bg-yellow-400/10'
  return 'text-red-400 bg-red-400/10'
}

/**
 * Group attendance records by guild-timezone date so that multiple raids on
 * the same day appear under one date header.  Each row carries the raid title
 * and icon so the "Raid" column can distinguish them.
 */
const dateSections = computed(() => {
  const eventMap = new Map()
  props.events.forEach(ev => eventMap.set(ev.id, ev))

  // Build flat rows with event metadata attached
  const rows = props.records.map(r => {
    const eid = r.raid_event_id ?? r.event_id
    const ev = eventMap.get(eid)
    return {
      eventId: eid,
      recordId: r.id ?? `${eid}-${r.character_id}`,
      raidTitle: ev?.title ?? 'Unknown Raid',
      raidType: ev?.raid_type ?? null,
      dateUtc: ev?.starts_at_utc ?? null,
      dateKey: guildDateKey(ev?.starts_at_utc),
      characterId: r.character_id,
      characterName: r.character?.name ?? 'Unknown',
      className: r.character?.class_name ?? '',
      outcome: r.outcome,
      note: r.note,
    }
  })

  // Group by guild-timezone date
  const grouped = new Map()
  rows.forEach(row => {
    if (!grouped.has(row.dateKey)) grouped.set(row.dateKey, [])
    grouped.get(row.dateKey).push(row)
  })

  return Array.from(grouped.entries())
    .map(([dateKey, dateRows]) => {
      return {
        dateKey,
        dateLabel: dateRows[0]?.dateUtc ? formatDate(dateRows[0].dateUtc) : 'Unknown Date',
        rows: dateRows,
      }
    })
    .sort((a, b) => {
      // Sort by newest date first
      const da = a.rows[0]?.dateUtc
      const db = b.rows[0]?.dateUtc
      if (!da || !db) return 0
      return new Date(db) - new Date(da)
    })
})
</script>
