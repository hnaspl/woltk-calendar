/**
 * Wowhead tooltip integration.
 *
 * Always loads the universal tooltips.js script (NOT expansion-specific ones
 * like wotlk.js) because only tooltips.js supports iconizeLinks which injects
 * actual item icons into links.  The expansion is specified per-link via the
 * ``domain`` parameter in ``data-wowhead`` attributes (e.g. ``domain=wotlk``).
 *
 * Graceful degradation: if the script fails to load (e.g. Wowhead is down),
 * items still display their names — the tooltip is a progressive enhancement.
 */
import { nextTick } from 'vue'

let loaded = false
let loading = false

const EXPANSION_DOMAIN_MAP = {
  classic: 'classic',
  tbc: 'tbc',
  wotlk: 'wotlk',
  cata: 'cata',
}

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
 * Get the Wowhead domain prefix for item/NPC links in a given expansion.
 * Returns empty string for retail, or 'classic', 'tbc', 'wotlk', 'cata'.
 */
export function getWowheadDomain(expansion) {
  return EXPANSION_DOMAIN_MAP[expansion] || ''
}

/**
 * Get the Wowhead base URL for a given expansion.
 * E.g. 'wotlk' → 'https://www.wowhead.com/wotlk'
 */
export function getWowheadBase(expansion) {
  const domain = EXPANSION_DOMAIN_MAP[expansion]
  return domain ? `https://www.wowhead.com/${domain}` : 'https://www.wowhead.com'
}

/**
 * Refresh Wowhead tooltips after Vue has rendered new item links.
 * Call this in onMounted / onUpdated / watch callbacks.
 *
 * @param {string} [expansion] - Optional expansion slug (kept for API compat, not used for script loading).
 */
export function refreshWowheadTooltips(expansion) {
  ensureLoaded()
  nextTick(() => {
    if (window.$WowheadPower?.refreshLinks) {
      window.$WowheadPower.refreshLinks()
    }
  })
}
