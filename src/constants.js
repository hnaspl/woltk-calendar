/**
 * Shared constants for the WotLK Calendar frontend.
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
  { value: 'os', label: 'Obsidian Sanctum' },
  { value: 'eoe', label: 'Eye of Eternity' },
  { value: 'voa', label: 'Vault of Archavon' },
  { value: 'ulduar', label: 'Ulduar' },
  { value: 'toc', label: 'Trial of the Crusader' },
  { value: 'icc', label: 'Icecrown Citadel' },
  { value: 'rs', label: 'Ruby Sanctum' },
]

export const ROLE_OPTIONS = [
  { value: 'tank', label: 'Melee DPS' },
  { value: 'main_tank', label: 'Main Tank' },
  { value: 'off_tank', label: 'Off Tank' },
  { value: 'healer', label: 'Heal' },
  { value: 'dps', label: 'Range DPS' },
]

export const CLASS_SPECS = {
  'Warrior':       ['Arms', 'Fury', 'Protection'],
  'Paladin':       ['Holy', 'Protection', 'Retribution'],
  'Hunter':        ['Beast Mastery', 'Marksmanship', 'Survival'],
  'Rogue':         ['Assassination', 'Combat', 'Subtlety'],
  'Priest':        ['Discipline', 'Holy', 'Shadow'],
  'Shaman':        ['Elemental', 'Enhancement', 'Restoration'],
  'Mage':          ['Arcane', 'Fire', 'Frost'],
  'Warlock':       ['Affliction', 'Demonology', 'Destruction'],
  'Druid':         ['Balance', 'Feral', 'Restoration'],
  'Death Knight':  ['Blood', 'Frost', 'Unholy'],
}

/** Class → allowed roles (backend role values) */
export const CLASS_ROLES = {
  'Death Knight':  ['main_tank', 'off_tank', 'tank'],
  'Druid':         ['main_tank', 'off_tank', 'healer', 'tank', 'dps'],
  'Hunter':        ['dps'],
  'Mage':          ['dps'],
  'Paladin':       ['main_tank', 'off_tank', 'healer', 'tank'],
  'Priest':        ['healer', 'dps'],
  'Rogue':         ['tank'],
  'Shaman':        ['healer', 'tank', 'dps'],
  'Warlock':       ['dps'],
  'Warrior':       ['main_tank', 'off_tank', 'tank'],
}
