/**
 * Non-expansion shared constants for the WotLK Calendar frontend.
 *
 * Expansion-specific data (classes, specs, roles, raids) is provided
 * by the expansion store / useExpansionData composable.
 *
 * Realm data is dynamic — provided by armory providers via the plugin
 * system.  There are no hardcoded realm lists.
 *
 * Keep in sync with app/constants.py (backend Python equivalent).
 */

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
 * WoW item quality → hex color.
 * Used for inline `style.color` on item names so colours match the actual game.
 * Keep in sync with Wowhead's quality definitions.
 */
export const ITEM_QUALITY_HEX = {
  0: '#9d9d9d', // Poor (gray)
  1: '#ffffff', // Common (white)
  2: '#1eff00', // Uncommon (green)
  3: '#0070dd', // Rare (blue)
  4: '#a335ee', // Epic (purple)
  5: '#ff8000', // Legendary (orange)
  6: '#e6cc80', // Artifact (gold)
}

/**
 * Signup attendance status options (informational — NOT coupled with bench/queue).
 * Keep in sync with app/api/v2/signups.py valid_statuses set.
 *
 * `label` is the English fallback; components should use the `i18nKey` with
 * the Vue i18n `t()` function so translations display correctly.
 */
export const ATTENDANCE_STATUS_OPTIONS = [
  { value: 'going',        label: 'Going',        i18nKey: 'signup.attendanceGoing' },
  { value: 'tentative',    label: 'Tentative',    i18nKey: 'signup.attendanceTentative' },
  { value: 'late',         label: 'Late',         i18nKey: 'signup.attendanceLate' },
  { value: 'not_going',    label: 'Not Going',    i18nKey: 'signup.attendanceNotGoing' },
  { value: 'alt',          label: 'Alt',          i18nKey: 'signup.attendanceAlt' },
  { value: 'did_not_show', label: 'Did Not Show', i18nKey: 'signup.attendanceDidNotShow' },
]

/** Attendance status value → i18n key for translation lookup. */
export const ATTENDANCE_STATUS_I18N_MAP = Object.fromEntries(
  ATTENDANCE_STATUS_OPTIONS.map(s => [s.value, s.i18nKey])
)

/** Attendance status value → display label (English fallback). Derived from ATTENDANCE_STATUS_OPTIONS. */
export const ATTENDANCE_STATUS_LABEL_MAP = Object.fromEntries(
  ATTENDANCE_STATUS_OPTIONS.map(s => [s.value, s.label])
)

/** Attendance status → Tailwind CSS classes for selects and badges. */
export const ATTENDANCE_STATUS_STYLE = {
  going:        { select: 'border-green-500/40 text-green-300 focus:border-green-400',  badge: 'bg-green-500/10 text-green-300 border border-green-500/30' },
  tentative:    { select: 'border-blue-500/40 text-blue-300 focus:border-blue-400',     badge: 'bg-blue-500/10 text-blue-300 border border-blue-500/30' },
  late:         { select: 'border-amber-500/40 text-amber-300 focus:border-amber-400',  badge: 'bg-amber-500/10 text-amber-300 border border-amber-500/30' },
  did_not_show: { select: 'border-red-500/40 text-red-300 focus:border-red-400',        badge: 'bg-red-500/10 text-red-300 border border-red-500/30' },
  not_going:    { select: 'border-red-500/40 text-red-300 focus:border-red-400',        badge: 'bg-red-500/10 text-red-300 border border-red-500/30' },
  alt:          { select: 'border-purple-500/40 text-purple-300 focus:border-purple-400', badge: 'bg-purple-500/10 text-purple-300 border border-purple-500/30' },
}

/**
 * Map an armory talent-tree name to the canonical spec name.
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

/**
 * Group raid definitions by expansion, sorted by expansion order (latest first).
 *
 * @param {Array} defs - Raid definitions to group (only builtin ones are grouped)
 * @param {Array} expansionSlugsDesc - Expansion slugs ordered latest→oldest
 * @param {Object} expansionLabelMap - Map of slug → display name
 * @returns {Array<{expansion: string, label: string, defs: Array}>}
 */
export function groupRaidDefsByExpansion(defs, expansionSlugsDesc = [], expansionLabelMap = {}) {
  const groups = {}
  for (const rd of defs) {
    const exp = rd.expansion || 'unknown'
    if (!groups[exp]) groups[exp] = []
    groups[exp].push(rd)
  }
  // Use API-provided order; fall back to alphabetical for unknown slugs
  const orderedSlugs = expansionSlugsDesc.length
    ? expansionSlugsDesc
    : Object.keys(groups).sort()
  return orderedSlugs
    .filter(exp => groups[exp]?.length)
    .map(exp => ({ expansion: exp, label: expansionLabelMap[exp] || exp, defs: groups[exp] }))
}
