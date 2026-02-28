<template>
  <div class="wow-calendar-wrapper">
    <FullCalendar
      ref="calendarRef"
      :options="calendarOptions"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import listPlugin from '@fullcalendar/list'
import interactionPlugin from '@fullcalendar/interaction'
import { useWowIcons } from '@/composables/useWowIcons'

const props = defineProps({
  events: { type: Array, default: () => [] },
  initialView: { type: String, default: 'dayGridMonth' }
})

const emit = defineEmits(['event-click', 'date-click'])

const { getRaidIcon } = useWowIcons()
const calendarRef = ref(null)

// Raid type → accent color mapping
const raidColors = {
  naxx:    '#8788EE',
  os:      '#C41E3A',
  eoe:     '#3FC7EB',
  voa:     '#F48CBA',
  ulduar:  '#FF7C0A',
  toc:     '#FFF468',
  icc:     '#c9a930',
  rs:      '#e53e3e',
  default: '#3FC7EB'
}

function getRaidColor(raidType) {
  return raidColors[raidType?.toLowerCase()] ?? raidColors.default
}

// Transform backend events to FullCalendar format
const fcEvents = computed(() =>
  props.events.map(ev => ({
    id: String(ev.id),
    title: ev.title ?? ev.name ?? 'Raid',
    start: ev.starts_at_utc ?? ev.start_time ?? ev.date,
    end: ev.ends_at_utc ?? ev.end_time ?? null,
    backgroundColor: getRaidColor(ev.raid_type),
    borderColor: 'transparent',
    textColor: '#0a0e17',
    extendedProps: { ...ev }
  }))
)

const calendarOptions = computed(() => ({
  plugins: [dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin],
  initialView: props.initialView,
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek,listWeek'
  },
  events: fcEvents.value,
  eventClick(info) {
    emit('event-click', info.event.extendedProps)
  },
  dateClick(info) {
    emit('date-click', info.dateStr)
  },
  height: 'auto',
  nowIndicator: true,
  eventTimeFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
  firstDay: 1, // Monday
  eventDisplay: 'block'
}))

watch(() => props.events, () => {
  calendarRef.value?.getApi()?.refetchEvents()
})
</script>

<style scoped>
.wow-calendar-wrapper {
  background: var(--color-bg-secondary);
  border-radius: 0.5rem;
  overflow: hidden;
}
</style>
