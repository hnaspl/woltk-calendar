/**
 * Non-expansion shared constants for the WotLK Calendar frontend.
 *
 * Expansion-specific data (classes, specs, roles, raids) is provided
 * by the expansion store / useExpansionData composable.
 *
 * Keep in sync with app/constants.py (backend Python equivalent).
 */

export const WARMANE_REALMS = [
  'Icecrown',
  'Lordaeron',
  'Onyxia',
  'Blackrock',
  'Frostwolf',
  'Frostmourne',
  'Neltharion',
]

export const ROLE_OPTIONS = [
  { value: 'melee_dps', label: 'Melee DPS' },
  { value: 'main_tank', label: 'Main Tank' },
  { value: 'off_tank', label: 'Off Tank' },
  { value: 'healer', label: 'Heal' },
  { value: 'range_dps', label: 'Range DPS' },
]

/** Role value → display label map. Derived from ROLE_OPTIONS to stay in sync. */
export const ROLE_LABEL_MAP = Object.fromEntries(
  ROLE_OPTIONS.map(r => [r.value, r.label])
)

/** Valid event status values. Keep in sync with app/enums.py EventStatus. */
export const EVENT_STATUSES = ['draft', 'open', 'locked', 'completed', 'cancelled']

/** Valid attendance outcome values. Keep in sync with app/enums.py AttendanceOutcome. */
export const ATTENDANCE_OUTCOMES = ['attended', 'late', 'no_show', 'benched', 'backup']

/**
 * Map a Warmane talent-tree name to the canonical spec name.
 * Handles quirks like "Feral" → "Feral Combat".
 *
 * Keep in sync with app/constants.py normalize_spec_name().
 */
export function normalizeSpecName(treeName, className, classSpecs = {}) {
  if (!treeName) return treeName
  const tree = treeName.trim()
  const specs = classSpecs[className] || []
  // Exact match
  const exact = specs.find(s => s.toLowerCase() === tree.toLowerCase())
  if (exact) return exact
  // Prefix match (e.g. "Feral" matches "Feral Combat")
  const prefix = specs.find(s => s.toLowerCase().startsWith(tree.toLowerCase()))
  if (prefix) return prefix
  // Suffix match (e.g. "Combat" matches "Feral Combat")
  const suffix = specs.find(s => s.toLowerCase().endsWith(tree.toLowerCase()))
  if (suffix) return suffix
  // Contains match (e.g. "Beast" matches "Beast Mastery")
  const contains = specs.find(s => s.toLowerCase().includes(tree.toLowerCase()))
  if (contains) return contains
  return tree
}

/** Format a duration in minutes to a human-readable string like "3h" or "2h 30m". */
export function formatDuration(minutes) {
  if (!minutes) return '?'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h > 0 && m > 0) return `${h}h ${m}m`
  if (h > 0) return `${h}h`
  return `${m}m`
}

/** WoW item quality CSS classes, keyed by quality integer (0–6). */
export const ITEM_QUALITY_COLORS = {
  0: { text: 'text-gray-500',   border: 'border-gray-600/40',   bg: 'bg-gray-900/40' },   // Poor
  1: { text: 'text-gray-300',   border: 'border-gray-500/40',   bg: 'bg-gray-800/30' },   // Common
  2: { text: 'text-green-400',  border: 'border-green-500/40',  bg: 'bg-green-900/20' },   // Uncommon
  3: { text: 'text-blue-400',   border: 'border-blue-500/40',   bg: 'bg-blue-900/20' },    // Rare
  4: { text: 'text-purple-400', border: 'border-purple-500/50', bg: 'bg-purple-900/20' },   // Epic
  5: { text: 'text-orange-400', border: 'border-orange-500/50', bg: 'bg-orange-900/20' },   // Legendary
  6: { text: 'text-red-400',    border: 'border-red-500/50',    bg: 'bg-red-900/20' },      // Artifact
}

/** WoW item quality display labels, keyed by quality integer (0–6). */
export const ITEM_QUALITY_LABELS = {
  0: 'Poor', 1: 'Common', 2: 'Uncommon', 3: 'Rare', 4: 'Epic', 5: 'Legendary', 6: 'Artifact',
}

/** Resolve the full quality color object ({text, border, bg}) for an equipment item. */
export function getItemQuality(item) {
  if (item.quality != null) return ITEM_QUALITY_COLORS[item.quality] ?? ITEM_QUALITY_COLORS[4]
  // Fallback: items with an ID but no quality field default to Rare (blue)
  if (item.item) return ITEM_QUALITY_COLORS[3]
  return ITEM_QUALITY_COLORS[1]
}

/** Get just the text-color CSS class for an equipment item's quality. */
export function getItemQualityText(item) {
  return getItemQuality(item).text
}

/** Get the display label for a quality integer. */
export function getItemQualityLabel(q) {
  return ITEM_QUALITY_LABELS[q] ?? ''
}

/** Get human-readable label for a raid type code. */
export function raidTypeLabel(raidType, raidTypes = []) {
  if (!raidType) return raidType
  const found = raidTypes.find(r => r.value === raidType)
  return found ? found.label : raidType
}
