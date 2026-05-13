/**
 * i18next setup for HLL Stats.
 *
 * Languages match rcongui_public/src/i18n/config.ts so cross-app navigation
 * between stats_app (7012) and rcongui_public (/live/) preserves the user's
 * language preference automatically — both apps share localStorage key
 * `i18nextLng` (the default for `i18next-browser-languagedetector`).
 *
 * Scope of current translation work (see stats_app/I18N_PLAN.md):
 *   Tier 1 (UI chrome): navbar, page titles, table headers, filter labels.
 *
 * Strings that are part of the community brand — achievement names,
 * playstyle archetypes, match titles, the kick reason `ПТН ПНХ` — remain
 * Ukrainian regardless of selected language. Their UI surroundings translate.
 *
 * Languages without a JSON file under ./locales fall back to English per
 * the `fallbackLng` rule. Ukrainian is the source language so its JSON is
 * effectively the schema for all others.
 */
import i18next from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import resourcesToBackend from 'i18next-resources-to-backend'

export const LANGUAGES = [
  'uk', 'en', 'de', 'ru', 'pl',
  'fr', 'es', 'it', 'pt', 'cs',
  'zh-Hans', 'zh-Hant', 'ja', 'ko',
] as const
export type Language = (typeof LANGUAGES)[number]

// Display names — shown in the language selector. Use each language's own
// name (the way the speaker reads it).
export const LANGUAGE_LABELS: Record<Language, string> = {
  uk: 'Українська',
  en: 'English',
  de: 'Deutsch',
  ru: 'Русский',
  pl: 'Polski',
  fr: 'Français',
  es: 'Español',
  it: 'Italiano',
  pt: 'Português',
  cs: 'Čeština',
  'zh-Hans': '简体中文',
  'zh-Hant': '繁體中文',
  ja: '日本語',
  ko: '한국어',
}

i18next
  .use(LanguageDetector)
  .use(initReactI18next)
  .use(
    resourcesToBackend((language: string, namespace: string) => {
      if (language === 'dev') return Promise.reject('no dev language')
      return import(`./locales/${language}/${namespace}.json`)
    }),
  )
  .init({
    debug: import.meta.env.DEV,
    fallbackLng: 'en',
    defaultNS: 'translation',
    interpolation: {
      escapeValue: false, // React already escapes
    },
    detection: {
      // Same key as rcongui_public so language is shared across both SPAs.
      lookupLocalStorage: 'i18nextLng',
      caches: ['localStorage'],
    },
  })

export default i18next
