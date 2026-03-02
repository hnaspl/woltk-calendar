/**
 * Wowhead tooltip integration.
 *
 * Loads the Wowhead tooltip script once and exposes a refresh function that
 * re-scans the DOM for new item links after Vue updates.
 *
 * Graceful degradation: if the script fails to load (e.g. Wowhead is down),
 * items still display their names — the tooltip is a progressive enhancement.
 */
import { nextTick } from 'vue'

let loaded = false
let loading = false

function ensureLoaded() {
  if (loaded || loading) return
  loading = true

  // Configure Wowhead tooltip behavior before loading the script
  window.whTooltips = {
    colorLinks: true,
    iconizeLinks: true,
    renameLinks: false,  // keep our own item names
    iconSize: 'small',
  }

  const script = document.createElement('script')
  script.src = 'https://wow.zamimg.com/js/tooltips.js'
  script.async = true
  script.onload = () => { loaded = true; loading = false }
  script.onerror = () => { loading = false }  // graceful degradation
  document.head.appendChild(script)
}

/**
 * Refresh Wowhead tooltips after Vue has rendered new item links.
 * Call this in onMounted / onUpdated / watch callbacks.
 */
export function refreshWowheadTooltips() {
  ensureLoaded()
  nextTick(() => {
    if (window.$WowheadPower?.refreshLinks) {
      window.$WowheadPower.refreshLinks()
    }
  })
}
