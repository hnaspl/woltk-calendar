/**
 * Shared constants for the WotLK Calendar frontend.
 *
 * Keep in sync with app/constants.py (backend Python equivalent).
 * Shared data: WARMANE_REALMS, CLASS_ROLES, CLASS_SPECS, RAID_TYPES,
 *              normalizeSpecName().
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

export const WOW_CLASSES = [
  'Death Knight',
  'Druid',
  'Hunter',
  'Mage',
  'Paladin',
  'Priest',
  'Rogue',
  'Shaman',
  'Warlock',
  'Warrior',
]

export const RAID_TYPES = [
  { value: 'naxx', label: 'Naxxramas' },
  { value: 'os', label: 'The Obsidian Sanctum' },
  { value: 'eoe', label: 'The Eye of Eternity' },
  { value: 'voa', label: 'Vault of Archavon' },
  { value: 'ulduar', label: 'Ulduar' },
  { value: 'toc', label: 'Trial of the Crusader' },
  { value: 'icc', label: 'Icecrown Citadel' },
  { value: 'rs', label: 'The Ruby Sanctum' },
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

export const CLASS_SPECS = {
  'Warrior':       ['Arms', 'Fury', 'Protection'],
  'Paladin':       ['Holy', 'Protection', 'Retribution'],
  'Hunter':        ['Beast Mastery', 'Marksmanship', 'Survival'],
  'Rogue':         ['Assassination', 'Combat', 'Subtlety'],
  'Priest':        ['Discipline', 'Holy', 'Shadow'],
  'Shaman':        ['Elemental', 'Enhancement', 'Restoration'],
  'Mage':          ['Arcane', 'Fire', 'Frost'],
  'Warlock':       ['Affliction', 'Demonology', 'Destruction'],
  'Druid':         ['Balance', 'Feral Combat', 'Restoration'],
  'Death Knight':  ['Blood', 'Frost', 'Unholy'],
}

/** Class → allowed roles (backend role values) */
export const CLASS_ROLES = {
  'Death Knight':  ['main_tank', 'off_tank', 'melee_dps'],
  'Druid':         ['main_tank', 'off_tank', 'healer', 'melee_dps', 'range_dps'],
  'Hunter':        ['range_dps'],
  'Mage':          ['range_dps'],
  'Paladin':       ['main_tank', 'off_tank', 'healer', 'melee_dps'],
  'Priest':        ['healer', 'range_dps'],
  'Rogue':         ['melee_dps'],
  'Shaman':        ['healer', 'melee_dps', 'range_dps'],
  'Warlock':       ['range_dps'],
  'Warrior':       ['main_tank', 'off_tank', 'melee_dps'],
}

/**
 * Map a Warmane talent-tree name to the canonical CLASS_SPECS name.
 * Handles quirks like "Feral" → "Feral Combat".
 *
 * Keep in sync with app/constants.py normalize_spec_name().
 */
export function normalizeSpecName(treeName, className) {
  if (!treeName) return treeName
  const tree = treeName.trim()
  const specs = CLASS_SPECS[className] || []
  // Exact match
  const exact = specs.find(s => s.toLowerCase() === tree.toLowerCase())
  if (exact) return exact
  // Prefix match (e.g. "Feral" matches "Feral Combat")
  const prefix = specs.find(s => s.toLowerCase().startsWith(tree.toLowerCase()))
  if (prefix) return prefix
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
export function raidTypeLabel(raidType) {
  if (!raidType) return raidType
  const found = RAID_TYPES.find(r => r.value === raidType)
  return found ? found.label : raidType
}
