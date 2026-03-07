/**
 * Shared composable for character preview/detail modal.
 *
 * Used by: GuildSettingsTab, MembersTab, SignupList, CharacterManagerView
 * Provides consistent character data preparation and modal state management.
 */
import { ref } from 'vue'

/**
 * Prepare a character object for CharacterDetailModal.
 *
 * Accepts characters from various sources (roster, signup, member list,
 * character manager) and normalises them to the modal's expected format.
 *
 * @param {Object} ch – raw character from any source
 * @param {Object} [extra] – optional overrides (e.g. guild name)
 * @returns {Object} normalised character for CharacterDetailModal
 */
export function prepareCharacterForModal(ch, extra = {}) {
  const metadata = ch.metadata ?? {}
  return {
    name: ch.name,
    class_name: ch.class_name ?? ch.class ?? metadata.class_name ?? '',
    realm_name: ch.realm_name ?? ch.realm ?? metadata.realm ?? '',
    default_role: ch.default_role ?? ch.role ?? '',
    primary_spec: ch.primary_spec ?? ch.spec ?? '',
    secondary_spec: ch.secondary_spec ?? '',
    armory_url: ch.armory_url ?? '',
    level: ch.level ?? metadata.level,
    metadata: {
      level: ch.level ?? metadata.level,
      race: ch.race ?? metadata.race ?? '',
      faction: ch.faction ?? metadata.faction ?? '',
      guild: extra.guild ?? ch.guild ?? metadata.guild ?? '',
      gear_score: ch.gear_score ?? metadata.gear_score,
      achievement_points: ch.achievement_points ?? metadata.achievement_points,
      honorable_kills: ch.honorable_kills ?? metadata.honorable_kills,
      professions: ch.professions ?? metadata.professions ?? [],
      talents: ch.talents ?? metadata.talents ?? [],
      equipment: ch.equipment ?? metadata.equipment ?? [],
      glyphs: ch.glyphs ?? metadata.glyphs ?? [],
      last_synced: ch.last_synced ?? metadata.last_synced,
      ...metadata,  // keep any additional metadata fields
    },
  }
}

/**
 * Composable providing modal state + open helper.
 *
 * @returns {{ showModal: Ref<boolean>, target: Ref<Object|null>, open: (ch, extra?) => void }}
 */
export function useCharacterPreview() {
  const showModal = ref(false)
  const target = ref(null)

  function open(ch, extra = {}) {
    target.value = prepareCharacterForModal(ch, extra)
    showModal.value = true
  }

  return { showModal, target, open }
}
