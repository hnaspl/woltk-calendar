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

// Status indicators for calendar readability
const statusIndicators = {
  cancelled: { prefix: '✗ ', opacity: 0.5 },
  completed: { prefix: '✓ ', opacity: 0.7 },
  locked:    { prefix: '🔒 ', opacity: 1 },
  draft:     { prefix: '📝 ', opacity: 0.6 },
}

function getStatusPrefix(status) {
  return statusIndicators[status]?.prefix ?? ''
}

function getStatusOpacity(status) {
  return statusIndicators[status]?.opacity ?? 1
}

// Transform backend events to FullCalendar format
const fcEvents = computed(() =>
  props.events.map(ev => {
    const status = ev.status ?? 'open'
    const prefix = getStatusPrefix(status)
    const opacity = getStatusOpacity(status)
    const baseColor = getRaidColor(ev.raid_type)
    return {
      id: String(ev.id),
      title: `${prefix}${ev.title ?? ev.name ?? 'Raid'}`,
      start: ev.starts_at_utc ?? ev.start_time ?? ev.date,
      end: ev.ends_at_utc ?? ev.end_time ?? null,
      backgroundColor: baseColor,
      borderColor: status === 'cancelled' ? '#e53e3e' : status === 'completed' ? '#48bb78' : status === 'locked' ? '#ecc94b' : 'transparent',
      textColor: '#0a0e17',
      classNames: status !== 'open' ? [`fc-event-${status}`] : [],
      extendedProps: { ...ev }
    }
  })
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

<style>
/* Calendar event status styles (unscoped for FullCalendar) */
.fc-event-cancelled {
  opacity: 0.5;
  text-decoration: line-through;
}
.fc-event-completed {
  opacity: 0.7;
}
.fc-event-locked {
  border-width: 2px !important;
}
.fc-event-draft {
  opacity: 0.6;
  border-style: dashed !important;
  border-color: #a0aec0 !important;
}
</style>
