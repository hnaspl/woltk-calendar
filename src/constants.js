/**
 * Non-expansion shared constants for the WotLK Calendar frontend.
 *
 * Expansion-specific data (classes, specs, roles, raids) is provided
 * by the expansion store / useExpansionData composable.
 *
 * Keep in sync with app/constants.py (backend Python equivalent).
 */

// Warmane realm list — static fallback until the constants store loads
// from the backend API.  The authoritative source is the Warmane plugin
// (app/plugins/warmane/plugin.py WARMANE_DEFAULT_REALMS).
// NOTE: This will be removed once all consumers use the constants store.
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

/** All valid role values, derived from ROLE_OPTIONS. */
export const ROLE_VALUES = ROLE_OPTIONS.map(r => r.value)

/**
 * Role value → lineup group key (singular → plural).
 * Keep in sync with app/constants.py ROLE_TO_GROUP.
 */
export const ROLE_TO_GROUP = {
  main_tank: 'main_tanks',
  off_tank: 'off_tanks',
  melee_dps: 'melee_dps',
  healer: 'healers',
  range_dps: 'range_dps',
}

/** Lineup group key → role value (reverse of ROLE_TO_GROUP). */
export const GROUP_TO_ROLE = Object.fromEntries(
  Object.entries(ROLE_TO_GROUP).map(([k, v]) => [v, k])
)

/** Ordered list of lineup group keys. */
export const LINEUP_GROUP_KEYS = Object.values(ROLE_TO_GROUP)

/** Default fallback role when a role is missing or unknown. */
export const DEFAULT_ROLE = 'range_dps'

/**
 * Default slot counts per role (used when raid definition is absent).
 * Keep in sync with app/constants.py DEFAULT_ROLE_SLOT_COUNTS.
 */
export const DEFAULT_ROLE_SLOT_COUNTS = {
  main_tank: 1,
  off_tank: 1,
  melee_dps: 0,
  healer: 5,
  range_dps: 18,
}

/**
 * Role → CSS style classes for RoleBadge component.
 */
export const ROLE_STYLE_MAP = {
  melee_dps: 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
  main_tank: 'bg-blue-600/20 text-blue-200 border border-blue-400/30',
  off_tank: 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30',
  healer: 'bg-green-500/20 text-green-300 border border-green-500/30',
  range_dps: 'bg-red-500/20 text-red-300 border border-red-500/30',
}

/**
 * Role → header/label CSS text-color class for lineup columns.
 */
export const ROLE_LABEL_CLASS = {
  main_tank: 'text-blue-200',
  off_tank: 'text-cyan-300',
  melee_dps: 'text-blue-300',
  healer: 'text-green-300',
  range_dps: 'text-red-300',
}

/**
 * Lineup column configuration array, derived from ROLE_OPTIONS.
 * Each entry has { key, role, label, labelClass }.
 */
export const LINEUP_COLUMNS = ROLE_OPTIONS.map(r => ({
  key: ROLE_TO_GROUP[r.value],
  role: r.value,
  label: r.label,
  labelClass: ROLE_LABEL_CLASS[r.value],
}))

/**
 * Role value → Vue prop name for slot count props.
 * Shared by LineupBoard and CompositionSummary to avoid duplication.
 */
export const ROLE_TO_SLOT_PROP = {
  main_tank: 'mainTankSlots',
  off_tank: 'offTankSlots',
  melee_dps: 'meleeDpsSlots',
  healer: 'healerSlots',
  range_dps: 'rangeDpsSlots',
}

/**
 * Role → progress bar CSS class for CompositionSummary.
 */
export const ROLE_BAR_CLASS = {
  main_tank: 'bg-blue-300',
  off_tank: 'bg-cyan-400',
  melee_dps: 'bg-blue-400',
  healer: 'bg-green-400',
  range_dps: 'bg-red-400',
}

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
