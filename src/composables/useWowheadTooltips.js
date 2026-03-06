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
let loadedDomain = null

const EXPANSION_DOMAIN_MAP = {
  classic: 'classic',
  tbc: 'tbc',
  wotlk: 'wotlk',
  cata: 'cata',
}

function ensureLoaded(expansion) {
  const domain = EXPANSION_DOMAIN_MAP[expansion] || null
  const scriptName = domain || 'tooltips'

  // Already loaded for this domain
  if (loaded && loadedDomain === scriptName) return
  if (loading) return
  loading = true

  // Configure Wowhead tooltip behavior before loading the script
  window.whTooltips = {
    colorLinks: true,
    iconizeLinks: true,
    renameLinks: false,  // keep our own item names
    iconSize: 'small',
  }

  const script = document.createElement('script')
  script.src = `https://wow.zamimg.com/js/${domain ? domain + '.js' : 'tooltips.js'}`
  script.async = true
  script.onload = () => { loaded = true; loading = false; loadedDomain = scriptName }
  script.onerror = () => { loading = false }  // graceful degradation
  document.head.appendChild(script)
}

/**
 * Get the Wowhead domain prefix for item/NPC links in a given expansion.
 * Returns empty string for retail, or 'classic', 'tbc', 'wotlk', 'cata'.
 */
export function getWowheadDomain(expansion) {
  return EXPANSION_DOMAIN_MAP[expansion] || ''
}

/**
 * Refresh Wowhead tooltips after Vue has rendered new item links.
 * Call this in onMounted / onUpdated / watch callbacks.
 *
 * @param {string} [expansion] - Optional expansion slug for domain-specific tooltips.
 */
export function refreshWowheadTooltips(expansion) {
  ensureLoaded(expansion)
  nextTick(() => {
    if (window.$WowheadPower?.refreshLinks) {
      window.$WowheadPower.refreshLinks()
    }
  })
}
