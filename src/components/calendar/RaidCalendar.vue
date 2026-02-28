<template>
  <div class="wow-calendar-wrapper">
    <FullCalendar
      ref="calendarRef"
      :options="calendarOptions"
    />
    <!-- Hover tooltip -->
    <div
      v-if="tooltip.visible"
      class="wow-event-tooltip"
      :style="{ top: tooltip.y + 'px', left: tooltip.x + 'px' }"
    >
      <div class="tooltip-header">
        <img :src="tooltip.icon" class="tooltip-raid-icon" alt="" />
        <div>
          <div class="tooltip-title">{{ tooltip.title }}</div>
          <div class="tooltip-time">{{ tooltip.time }}</div>
        </div>
      </div>
      <div class="tooltip-details">
        <div class="tooltip-row">
          <span class="tooltip-label">Status:</span>
          <span :class="['tooltip-status', `status-${tooltip.status}`]">{{ tooltip.statusLabel }}</span>
        </div>
        <div class="tooltip-row">
          <span class="tooltip-label">Size:</span>
          <span>{{ tooltip.size }}-man {{ tooltip.difficulty }}</span>
        </div>
        <div v-if="tooltip.signupCount != null" class="tooltip-row">
          <span class="tooltip-label">Signups:</span>
          <span>{{ tooltip.signupCount }} / {{ tooltip.size }}</span>
        </div>
        <div v-if="tooltip.signupExpired" class="tooltip-row tooltip-warning">
          ⚠ Signup time expired
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, reactive } from 'vue'
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

// Hover tooltip state
const tooltip = reactive({
  visible: false,
  x: 0,
  y: 0,
  title: '',
  time: '',
  icon: '',
  status: '',
  statusLabel: '',
  size: 25,
  difficulty: 'normal',
  signupCount: null,
  signupExpired: false
})

let tooltipTimeout = null

const statusLabels = {
  open: 'Open',
  locked: 'Locked',
  completed: 'Completed',
  cancelled: 'Cancelled',
  draft: 'Draft'
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false
  })
}

function showTooltip(info) {
  clearTimeout(tooltipTimeout)
  const ev = info.event.extendedProps
  const rect = info.el.getBoundingClientRect()
  const wrapperRect = calendarRef.value?.$el?.getBoundingClientRect() ?? { left: 0, top: 0 }

  tooltip.title = info.event.title
  tooltip.time = formatTime(ev.starts_at_utc)
  tooltip.icon = getRaidIcon(ev.raid_type)
  tooltip.status = ev.status ?? 'open'
  tooltip.statusLabel = statusLabels[tooltip.status] ?? tooltip.status
  tooltip.size = ev.raid_size ?? 25
  tooltip.difficulty = ev.difficulty ?? 'normal'
  tooltip.signupCount = ev.signup_count ?? null

  // Check if signup time has expired
  const closeAt = ev.close_signups_at ? new Date(ev.close_signups_at) : null
  const startsAt = ev.starts_at_utc ? new Date(ev.starts_at_utc) : null
  const now = new Date()
  tooltip.signupExpired = (closeAt && now > closeAt) || (startsAt && now > startsAt)

  // Position relative to wrapper
  tooltip.x = rect.left - wrapperRect.left + rect.width / 2
  tooltip.y = rect.bottom - wrapperRect.top + 4
  tooltip.visible = true
}

function hideTooltip() {
  tooltipTimeout = setTimeout(() => {
    tooltip.visible = false
  }, 100)
}

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
  props.events.map(ev => {
    const status = ev.status ?? 'open'
    const baseColor = getRaidColor(ev.raid_type)
    return {
      id: String(ev.id),
      title: ev.title ?? ev.name ?? 'Raid',
      start: ev.starts_at_utc ?? ev.start_time ?? ev.date,
      end: ev.ends_at_utc ?? ev.end_time ?? null,
      backgroundColor: 'transparent',
      borderColor: 'transparent',
      textColor: '#e2e8f0',
      classNames: ['wow-raid-event', `wow-raid-${status}`],
      extendedProps: { ...ev, _raidIcon: getRaidIcon(ev.raid_type), _raidColor: baseColor }
    }
  })
)

// Custom event content renderer — shows raid icon + title
function renderEventContent(arg) {
  const ev = arg.event.extendedProps
  const icon = ev._raidIcon
  const color = ev._raidColor

  const wrapper = document.createElement('div')
  wrapper.className = 'wow-event-content'
  wrapper.style.borderLeftColor = color

  const img = document.createElement('img')
  img.src = icon
  img.className = 'wow-event-icon'
  img.alt = ''

  const text = document.createElement('span')
  text.className = 'wow-event-title'
  text.textContent = arg.event.title

  wrapper.appendChild(img)
  wrapper.appendChild(text)
  return { domNodes: [wrapper] }
}

const calendarOptions = computed(() => ({
  plugins: [dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin],
  initialView: props.initialView,
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek,listWeek'
  },
  events: fcEvents.value,
  eventContent: renderEventContent,
  eventClick(info) {
    tooltip.visible = false
    emit('event-click', info.event.extendedProps)
  },
  eventMouseEnter: showTooltip,
  eventMouseLeave: hideTooltip,
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
  position: relative;
}

/* Tooltip */
.wow-event-tooltip {
  position: absolute;
  z-index: 1000;
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: 0.5rem;
  padding: 0.75rem;
  min-width: 220px;
  max-width: 280px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.6);
  pointer-events: none;
  transform: translateX(-50%);
}
.tooltip-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #2a2a4a;
}
.tooltip-raid-icon {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  border: 1px solid #3a3a5a;
  flex-shrink: 0;
}
.tooltip-title {
  font-weight: 600;
  color: #e2e8f0;
  font-size: 0.85rem;
  line-height: 1.2;
}
.tooltip-time {
  font-size: 0.75rem;
  color: #a0aec0;
}
.tooltip-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.tooltip-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.78rem;
  color: #cbd5e0;
}
.tooltip-label {
  color: #718096;
}
.tooltip-status {
  font-weight: 600;
  text-transform: capitalize;
}
.status-open { color: #48bb78; }
.status-locked { color: #ecc94b; }
.status-completed { color: #63b3ed; }
.status-cancelled { color: #fc8181; }
.status-draft { color: #a0aec0; }
.tooltip-warning {
  color: #ecc94b;
  font-weight: 600;
  justify-content: center;
  margin-top: 0.25rem;
}
</style>

<style>
/* Custom event rendering (unscoped for FullCalendar DOM) */
.wow-event-content {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 4px;
  border-left: 3px solid;
  border-radius: 3px;
  background: rgba(26, 26, 46, 0.85);
  overflow: hidden;
  cursor: pointer;
  min-height: 22px;
}
.wow-event-content:hover {
  background: rgba(42, 42, 74, 0.95);
}
.wow-event-icon {
  width: 18px;
  height: 18px;
  border-radius: 2px;
  flex-shrink: 0;
}
.wow-event-title {
  font-size: 0.75rem;
  font-weight: 500;
  color: #e2e8f0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Status-based opacity for calendar events */
.wow-raid-cancelled .wow-event-content {
  opacity: 0.5;
  text-decoration: line-through;
}
.wow-raid-completed .wow-event-content {
  opacity: 0.7;
}
.wow-raid-locked .wow-event-content {
  border-left-width: 4px;
}
.wow-raid-draft .wow-event-content {
  opacity: 0.6;
  border-left-style: dashed;
}

/* FullCalendar event overrides */
.fc .fc-event {
  border: none !important;
  background: transparent !important;
  padding: 0 !important;
}
.fc .fc-daygrid-event {
  margin: 1px 2px !important;
}
</style>
