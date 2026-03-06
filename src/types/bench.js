/**
 * JSDoc type definitions for bench/queue data structures.
 *
 * These types describe the data flowing between backend and frontend
 * for the bench/queue system.  Since the frontend uses plain JavaScript
 * (not TypeScript), we use JSDoc `@typedef` annotations so editors
 * that support JSDoc (VS Code, WebStorm) can provide IntelliSense.
 *
 * Backend equivalents live in:
 *   - app/services/lineup_service.py  (get_bench_info, get_lineup_grouped)
 *   - app/services/signup_service.py  (lineup_status field)
 *   - app/utils/bench_formatter.py    (format_bench_entries)
 *
 * @module types/bench
 */

/**
 * Bench information attached to a signup when the player is on the bench.
 * Returned by `lineup_service.get_bench_info()`.
 *
 * @typedef {Object} BenchInfo
 * @property {string} waiting_for - The role value the player is queued for
 *   (e.g. "healer", "main_tank", "range_dps").
 * @property {number} queue_position - 1-based position in the bench queue
 *   for that role.
 */

/**
 * A signup object as returned by the API.
 * Only bench-relevant fields are documented here.
 *
 * @typedef {Object} SignupEntry
 * @property {number} id - Signup ID.
 * @property {number} event_id - Associated event ID.
 * @property {number} character_id - Character used for this signup.
 * @property {string} chosen_role - Role value chosen by the player.
 * @property {string} lineup_status - One of "going", "bench", "waitlist".
 * @property {string} attendance_status - One of "going", "tentative",
 *   "late", "not_going", "alt", "did_not_show".
 * @property {BenchInfo|null} bench_info - Populated when
 *   `lineup_status === "bench"`.
 * @property {CharacterInfo} character - Nested character data.
 */

/**
 * Character info embedded inside a signup.
 *
 * @typedef {Object} CharacterInfo
 * @property {number} id - Character ID.
 * @property {string} name - Character name.
 * @property {string} class_name - WoW class (e.g. "Paladin").
 * @property {string|null} spec_name - Specialization name.
 * @property {number|null} level - Character level.
 */

/**
 * A bench queue entry as stored in `LineupBoard.benchQueue` ref.
 * Each entry is a signup object augmented with display helpers.
 *
 * @typedef {Object} BenchQueueEntry
 * @property {number} signup_id - Signup ID (matches SignupEntry.id).
 * @property {string} character_name - Display name of the character.
 * @property {string} class_name - WoW class name.
 * @property {string} chosen_role - Role the player signed up for.
 * @property {number} queue_position - 1-based queue position.
 * @property {string} waiting_for - Role being queued for.
 */

/**
 * Grouped lineup data as returned by `lineup_service.get_lineup_grouped()`.
 *
 * @typedef {Object} GroupedLineup
 * @property {SignupEntry[]} main_tanks - Main tank signups.
 * @property {SignupEntry[]} off_tanks - Off-tank signups.
 * @property {SignupEntry[]} healers - Healer signups.
 * @property {SignupEntry[]} melee_dps - Melee DPS signups.
 * @property {SignupEntry[]} range_dps - Ranged DPS signups.
 * @property {BenchQueueEntry[]} bench_queue - Ordered bench queue.
 */

/**
 * Result from `format_bench_entries()` (backend utility).
 *
 * @typedef {Object} BenchFormatResult
 * @property {string} text - Formatted text block (newline-separated entries,
 *   optionally ending with "+X more on bench").
 * @property {number} count - Total number of bench players.
 */

export {}
