// Real WoW icon imports — downloaded from Wowhead CDN (public game assets)
import classicon_warrior from '@/assets/icons/wow/classicon_warrior.jpg'
import classicon_paladin from '@/assets/icons/wow/classicon_paladin.jpg'
import classicon_hunter from '@/assets/icons/wow/classicon_hunter.jpg'
import classicon_rogue from '@/assets/icons/wow/classicon_rogue.jpg'
import classicon_priest from '@/assets/icons/wow/classicon_priest.jpg'
import classicon_shaman from '@/assets/icons/wow/classicon_shaman.jpg'
import classicon_mage from '@/assets/icons/wow/classicon_mage.jpg'
import classicon_warlock from '@/assets/icons/wow/classicon_warlock.jpg'
import classicon_druid from '@/assets/icons/wow/classicon_druid.jpg'
import classicon_deathknight from '@/assets/icons/wow/classicon_deathknight.jpg'

import icon_tank from '@/assets/icons/wow/ability_warrior_defensivestance.jpg'
import icon_healer from '@/assets/icons/wow/spell_holy_flashheal.jpg'
import icon_dps from '@/assets/icons/wow/ability_dualwield.jpg'

import raid_naxx from '@/assets/icons/wow/spell_shadow_shadesofdarkness.jpg'
import raid_os from '@/assets/icons/wow/inv_misc_head_dragon_black.jpg'
import raid_eoe from '@/assets/icons/wow/inv_misc_head_dragon_blue.jpg'
import raid_voa from '@/assets/icons/wow/achievement_bg_killxenemies_generalsroom.jpg'
import raid_ulduar from '@/assets/icons/wow/achievement_dungeon_ulduarraid_misc_04.jpg'
import raid_toc from '@/assets/icons/wow/achievement_reputation_argentcrusader.jpg'
import raid_icc from '@/assets/icons/wow/achievement_dungeon_icecrown_frostmourne.jpg'
import raid_rs from '@/assets/icons/wow/inv_misc_head_dragon_red.jpg'

import icon_fallback from '@/assets/icons/wow/inv_misc_questionmark.jpg'

// Profession icons
import prof_alchemy from '@/assets/icons/wow/trade_alchemy.jpg'
import prof_blacksmithing from '@/assets/icons/wow/trade_blacksmithing.jpg'
import prof_enchanting from '@/assets/icons/wow/trade_engraving.jpg'
import prof_engineering from '@/assets/icons/wow/trade_engineering.jpg'
import prof_herbalism from '@/assets/icons/wow/trade_herbalism.jpg'
import prof_jewelcrafting from '@/assets/icons/wow/inv_misc_gem_01.jpg'
import prof_leatherworking from '@/assets/icons/wow/trade_leatherworking.jpg'
import prof_mining from '@/assets/icons/wow/trade_mining.jpg'
import prof_skinning from '@/assets/icons/wow/inv_misc_armorkit_17.jpg'
import prof_tailoring from '@/assets/icons/wow/trade_tailoring.jpg'
import prof_inscription from '@/assets/icons/wow/inv_misc_herb_07.jpg'
import prof_cooking from '@/assets/icons/wow/inv_misc_food_15.jpg'
import prof_first_aid from '@/assets/icons/wow/spell_holy_sealofsacrifice.jpg'
import prof_fishing from '@/assets/icons/wow/spell_nature_thunderclap.jpg'

import spec_arms from '@/assets/icons/wow/ability_warrior_savageblow.jpg'
import spec_fury from '@/assets/icons/wow/ability_warrior_innerrage.jpg'
import spec_holy_paladin from '@/assets/icons/wow/spell_holy_holybolt.jpg'
import spec_prot_paladin from '@/assets/icons/wow/ability_paladin_shieldofthetemplar.jpg'
import spec_retribution from '@/assets/icons/wow/spell_holy_auraoflight.jpg'
import spec_balance from '@/assets/icons/wow/spell_nature_starfall.jpg'
import spec_feral from '@/assets/icons/wow/ability_druid_catform.jpg'
import spec_resto_druid from '@/assets/icons/wow/spell_nature_healingtouch.jpg'
import spec_bm from '@/assets/icons/wow/ability_hunter_bestialdiscipline.jpg'
import spec_mm from '@/assets/icons/wow/ability_marksmanship.jpg'
import spec_survival from '@/assets/icons/wow/ability_hunter_camouflage.jpg'
import spec_arcane from '@/assets/icons/wow/spell_holy_magicalsentry.jpg'
import spec_fire from '@/assets/icons/wow/spell_fire_firebolt02.jpg'
import spec_frost_mage from '@/assets/icons/wow/spell_frost_frostbolt02.jpg'
import spec_affliction from '@/assets/icons/wow/spell_shadow_deathcoil.jpg'
import spec_demonology from '@/assets/icons/wow/spell_shadow_metamorphosis.jpg'
import spec_destruction from '@/assets/icons/wow/spell_shadow_rainoffire.jpg'
import spec_elemental from '@/assets/icons/wow/spell_nature_lightning.jpg'
import spec_enhancement from '@/assets/icons/wow/spell_shaman_improvedstormstrike.jpg'
import spec_resto_shaman from '@/assets/icons/wow/spell_nature_magicimmunity.jpg'
import spec_holy_priest from '@/assets/icons/wow/spell_holy_guardianspirit.jpg'
import spec_discipline from '@/assets/icons/wow/spell_holy_powerwordshield.jpg'
import spec_shadow from '@/assets/icons/wow/spell_shadow_shadowwordpain.jpg'
import spec_assassination from '@/assets/icons/wow/ability_rogue_eviscerate.jpg'
import spec_combat from '@/assets/icons/wow/ability_backstab.jpg'
import spec_subtlety from '@/assets/icons/wow/ability_stealth.jpg'
import spec_blood from '@/assets/icons/wow/spell_deathknight_bloodpresence.jpg'
import spec_frost_dk from '@/assets/icons/wow/spell_deathknight_frostpresence.jpg'
import spec_unholy from '@/assets/icons/wow/spell_deathknight_unholypresence.jpg'

// WoW class icon mapping (handles both "death knight" and "death-knight" forms)
const CLASS_ICONS = {
  warrior:      classicon_warrior,
  paladin:      classicon_paladin,
  hunter:       classicon_hunter,
  rogue:        classicon_rogue,
  priest:       classicon_priest,
  shaman:       classicon_shaman,
  mage:         classicon_mage,
  warlock:      classicon_warlock,
  druid:        classicon_druid,
  'death knight': classicon_deathknight,
  'death-knight': classicon_deathknight,
  deathknight:  classicon_deathknight,
  dk:           classicon_deathknight
}

const ROLE_ICONS = {
  tank:      icon_tank,
  main_tank: icon_tank,
  off_tank:  icon_tank,
  healer:    icon_healer,
  dps:       icon_dps
}

const RAID_ICONS = {
  naxx:    raid_naxx,
  os:      raid_os,
  eoe:     raid_eoe,
  voa:     raid_voa,
  ulduar:  raid_ulduar,
  toc:     raid_toc,
  icc:     raid_icc,
  rs:      raid_rs
}

const PROFESSION_ICONS = {
  alchemy:        prof_alchemy,
  blacksmithing:  prof_blacksmithing,
  enchanting:     prof_enchanting,
  engineering:    prof_engineering,
  herbalism:      prof_herbalism,
  jewelcrafting:  prof_jewelcrafting,
  leatherworking: prof_leatherworking,
  mining:         prof_mining,
  skinning:       prof_skinning,
  tailoring:      prof_tailoring,
  inscription:    prof_inscription,
  cooking:        prof_cooking,
  'first aid':    prof_first_aid,
  fishing:        prof_fishing,
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
    return CLASS_ICONS[normalizeClass(className)] ?? icon_fallback
  }

  function getRoleIcon(role) {
    return ROLE_ICONS[role?.toLowerCase()] ?? icon_fallback
  }

  function getRaidIcon(raidCode) {
    return RAID_ICONS[raidCode?.toLowerCase()] ?? raid_ulduar
  }

  function getClassColor(className) {
    return CLASS_COLORS[normalizeClass(className)] ?? '#8b8d91'
  }

  function getSpecIcon(specName, className) {
    const specMap = {
      // Warrior
      'arms':           spec_arms,
      'fury':           spec_fury,
      // Paladin
      'retribution':    spec_retribution,
      // Druid
      'balance':        spec_balance,
      'feral':          spec_feral,
      'feral combat':   spec_feral,
      // Hunter
      'beast mastery':  spec_bm,
      'marksmanship':   spec_mm,
      'survival':       spec_survival,
      // Mage
      'arcane':         spec_arcane,
      'fire':           spec_fire,
      // Warlock
      'affliction':     spec_affliction,
      'demonology':     spec_demonology,
      'destruction':    spec_destruction,
      // Shaman
      'elemental':      spec_elemental,
      'enhancement':    spec_enhancement,
      // Priest
      'discipline':     spec_discipline,
      'shadow':         spec_shadow,
      // Rogue
      'assassination':  spec_assassination,
      'combat':         spec_combat,
      'subtlety':       spec_subtlety,
      // Death Knight
      'blood':          spec_blood,
      'unholy':         spec_unholy,
    }

    // Ambiguous specs — resolved by class context
    const ambiguous = {
      'frost':       { 'death knight': spec_frost_dk, _default: spec_frost_mage },
      'holy':        { priest: spec_holy_priest, _default: spec_holy_paladin },
      'protection':  { warrior: icon_tank, _default: spec_prot_paladin },
      'restoration': { shaman: spec_resto_shaman, _default: spec_resto_druid },
    }

    const key = specName?.toLowerCase().trim() ?? ''
    if (specMap[key]) return specMap[key]

    const amb = ambiguous[key]
    if (amb) {
      const cls = className?.toLowerCase().trim() ?? ''
      return amb[cls] ?? amb._default
    }

    return icon_fallback
  }

  function getProfessionIcon(profName) {
    return PROFESSION_ICONS[profName?.toLowerCase().trim()] ?? icon_fallback
  }

  return { getClassIcon, getRoleIcon, getRaidIcon, getClassColor, getSpecIcon, getProfessionIcon, CLASS_COLORS, RAID_ICONS, ROLE_ICONS, PROFESSION_ICONS }
}
