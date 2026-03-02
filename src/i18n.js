/**
 * Vue i18n plugin — loads translations from the shared translations/ directory.
 *
 * Both the Flask backend and Vue frontend use the same JSON files located
 * at /translations/en.json and /translations/pl.json.
 *
 * Language is determined by:
 *   1. Authenticated user's `language` preference from their profile
 *   2. Browser's navigator.language (for unauthenticated users)
 *   3. Falls back to 'en'
 */
import { createI18n } from 'vue-i18n'

import en from '@translations/en.json'
import pl from '@translations/pl.json'

/**
 * Detect browser language, mapped to supported locales.
 */
export function detectBrowserLocale() {
  const browserLang = navigator.language || navigator.userLanguage || 'en'
  const short = browserLang.split('-')[0].toLowerCase()
  if (short === 'pl') return 'pl'
  return 'en'
}

const i18n = createI18n({
  legacy: false,            // use Composition API mode
  locale: detectBrowserLocale(),
  fallbackLocale: 'en',
  messages: { en, pl },
})

export default i18n
