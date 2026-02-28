const BASE = 'https://wow.zamimg.com/images/wow/icons/large'

// WoW class icon mapping (handles both "death knight" and "death-knight" forms)
const CLASS_ICONS = {
  warrior:      `${BASE}/classicon_warrior.jpg`,
  paladin:      `${BASE}/classicon_paladin.jpg`,
  hunter:       `${BASE}/classicon_hunter.jpg`,
  rogue:        `${BASE}/classicon_rogue.jpg`,
  priest:       `${BASE}/classicon_priest.jpg`,
  shaman:       `${BASE}/classicon_shaman.jpg`,
  mage:         `${BASE}/classicon_mage.jpg`,
  warlock:      `${BASE}/classicon_warlock.jpg`,
  druid:        `${BASE}/classicon_druid.jpg`,
  'death knight': `${BASE}/classicon_deathknight.jpg`,
  'death-knight': `${BASE}/classicon_deathknight.jpg`,
  deathknight:  `${BASE}/classicon_deathknight.jpg`,
  dk:           `${BASE}/classicon_deathknight.jpg`
}

const ROLE_ICONS = {
  tank:   `${BASE}/ability_warrior_defensivestance.jpg`,
  healer: `${BASE}/spell_holy_flashheal.jpg`,
  dps:    `${BASE}/ability_dualwield.jpg`
}

const RAID_ICONS = {
  naxx:    `${BASE}/spell_shadow_shadesofdarkness.jpg`,
  os:      `${BASE}/inv_misc_head_dragon_black.jpg`,
  eoe:     `${BASE}/inv_misc_head_dragon_blue.jpg`,
  voa:     `${BASE}/achievement_bg_killxenemies_generalsroom_av.jpg`,
  ulduar:  `${BASE}/achievement_dungeon_ulduarraid_25man.jpg`,
  toc:     `${BASE}/achievement_dungeon_tocrraid_25man.jpg`,
  icc:     `${BASE}/achievement_dungeon_icecrown_25man.jpg`,
  rs:      `${BASE}/inv_misc_head_dragon_red.jpg`
}

// WoW class hex colors
const CLASS_COLORS = {
  warrior:       '#C69B6D',
  paladin:       '#F48CBA',
  hunter:        '#AAD372',
  rogue:         '#FFF468',
  priest:        '#FFFFFF',
  shaman:        '#0070DD',
  mage:          '#3FC7EB',
  warlock:       '#8788EE',
  druid:         '#FF7C0A',
  'death knight': '#C41E3A',
  'death-knight': '#C41E3A',
  deathknight:   '#C41E3A',
  dk:            '#C41E3A'
}

export function useWowIcons() {
  function normalizeClass(name) {
    return name?.toLowerCase().trim() ?? ''
  }

  function getClassIcon(className) {
    return CLASS_ICONS[normalizeClass(className)] ?? `${BASE}/inv_misc_questionmark.jpg`
  }

  function getRoleIcon(role) {
    return ROLE_ICONS[role?.toLowerCase()] ?? `${BASE}/inv_misc_questionmark.jpg`
  }

  function getRaidIcon(raidCode) {
    return RAID_ICONS[raidCode?.toLowerCase()] ?? `${BASE}/achievement_dungeon_ulduarraid_25man.jpg`
  }

  function getClassColor(className) {
    return CLASS_COLORS[normalizeClass(className)] ?? '#8b8d91'
  }

  function getSpecIcon(specName) {
    // Normalise spec name to a zamimg-style slug for common WotLK specs
    const specMap = {
      'arms':           `${BASE}/ability_warrior_savageblow.jpg`,
      'fury':           `${BASE}/ability_warrior_innerrage.jpg`,
      'protection warrior': `${BASE}/ability_warrior_defensivestance.jpg`,
      'holy paladin':   `${BASE}/spell_holy_holybolt.jpg`,
      'protection paladin': `${BASE}/ability_paladin_shieldofthetemplar.jpg`,
      'retribution':    `${BASE}/spell_holy_auraoflight.jpg`,
      'balance':        `${BASE}/spell_nature_starfall.jpg`,
      'feral':          `${BASE}/ability_druid_catform.jpg`,
      'restoration druid': `${BASE}/spell_nature_healingtouch.jpg`,
      'beast mastery':  `${BASE}/ability_hunter_bestialdiscipline.jpg`,
      'marksmanship':   `${BASE}/ability_marksmanship.jpg`,
      'survival':       `${BASE}/ability_hunter_camouflage.jpg`,
      'arcane':         `${BASE}/spell_holy_magicalsentry.jpg`,
      'fire':           `${BASE}/spell_fire_firebolt02.jpg`,
      'frost mage':     `${BASE}/spell_frost_frostbolt02.jpg`,
      'affliction':     `${BASE}/spell_shadow_deathcoil.jpg`,
      'demonology':     `${BASE}/spell_shadow_metamorphosis.jpg`,
      'destruction':    `${BASE}/spell_shadow_rainoffire.jpg`,
      'elemental':      `${BASE}/spell_nature_lightning.jpg`,
      'enhancement':    `${BASE}/spell_shaman_improvedstormstrike.jpg`,
      'restoration shaman': `${BASE}/spell_nature_magicimmunity.jpg`,
      'holy priest':    `${BASE}/spell_holy_guardianspirit.jpg`,
      'discipline':     `${BASE}/spell_holy_powerwordshield.jpg`,
      'shadow':         `${BASE}/spell_shadow_shadowwordpain.jpg`,
      'assassination':  `${BASE}/ability_rogue_eviscerate.jpg`,
      'combat':         `${BASE}/ability_backstab.jpg`,
      'subtlety':       `${BASE}/ability_stealth.jpg`,
      'blood':          `${BASE}/spell_deathknight_bloodpresence.jpg`,
      'frost dk':       `${BASE}/spell_deathknight_frostpresence.jpg`,
      'unholy':         `${BASE}/spell_deathknight_unholypresence.jpg`
    }
    const key = specName?.toLowerCase().trim() ?? ''
    return specMap[key] ?? `${BASE}/inv_misc_questionmark.jpg`
  }

  return { getClassIcon, getRoleIcon, getRaidIcon, getClassColor, getSpecIcon, CLASS_COLORS, RAID_ICONS, ROLE_ICONS }
}
