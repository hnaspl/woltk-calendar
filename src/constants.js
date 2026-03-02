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

/** Get human-readable label for a raid type code. */
export function raidTypeLabel(raidType) {
  if (!raidType) return raidType
  const found = RAID_TYPES.find(r => r.value === raidType)
  return found ? found.label : raidType
}
