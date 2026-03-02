/**
 * useSocket – Vue composable for Socket.IO real-time event updates.
 *
 * Manages a single shared Socket.IO connection.  Components call
 * `joinEvent(eventId)` / `leaveEvent(eventId)` to subscribe to a
 * specific raid event room, and register listeners via `on` / `off`.
 *
 * Guild rooms (`joinGuild` / `leaveGuild`) are used for calendar and
 * guild-level real-time updates.
 */
import { ref, onUnmounted } from 'vue'
import { io } from 'socket.io-client'

/** Singleton socket instance (lazy-initialised on first use). */
let socket = null
let refCount = 0

function getSocket() {
  if (!socket) {
    socket = io({ path: '/socket.io', transports: ['websocket', 'polling'] })
  }
  return socket
}

export function useSocket() {
  const connected = ref(false)
  const s = getSocket()
  refCount++

  // Track connection state
  function onConnect() { connected.value = true }
  function onDisconnect() { connected.value = false }
  s.on('connect', onConnect)
  s.on('disconnect', onDisconnect)
  connected.value = s.connected

  /** Join the Socket.IO room for a given raid event. */
  function joinEvent(eventId) {
    s.emit('join_event', { event_id: Number(eventId) })
  }

  /** Leave the Socket.IO room for a given raid event. */
  function leaveEvent(eventId) {
    s.emit('leave_event', { event_id: Number(eventId) })
  }

  /** Join the Socket.IO room for a given guild (calendar / guild updates). */
  function joinGuild(guildId) {
    s.emit('join_guild', { guild_id: Number(guildId) })
  }

  /** Leave the Socket.IO room for a given guild. */
  function leaveGuild(guildId) {
    s.emit('leave_guild', { guild_id: Number(guildId) })
  }

  /** Register a listener for a Socket.IO event. */
  function on(event, handler) {
    s.on(event, handler)
  }

  /** Remove a listener for a Socket.IO event. */
  function off(event, handler) {
    s.off(event, handler)
  }

  onUnmounted(() => {
    s.off('connect', onConnect)
    s.off('disconnect', onDisconnect)
    refCount = Math.max(0, refCount - 1)
    if (refCount === 0 && socket) {
      socket.disconnect()
      socket = null
    }
  })

  return { connected, joinEvent, leaveEvent, joinGuild, leaveGuild, on, off }
}
