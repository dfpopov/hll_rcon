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

/**
 * Initial language preference resolution.
 *
 * Editorial policy: a Russian-language browser defaults to Ukrainian on first
 * visit (this is a Ukrainian community server hosting players harmed by the
 * russian invasion — see also the anti-war flag in CountryFlag.tsx and the
 * /kick ПТН ПНХ hook for Steam country=RU). Users can still switch to RU
 * manually via the language selector — the manual choice is persisted in
 * localStorage and respected on subsequent visits.
 *
 * Mechanism: we read localStorage ourselves to see if the user has ever
 * picked a language. If yes — honor it (pass to i18next via `lng`). If no
 * (first visit), look at navigator.language; map any ru-* to uk; otherwise
 * let LanguageDetector handle it normally (so en-US → en, de-DE → de, etc.).
 */
function resolveInitialLng(): string | undefined {
  if (typeof window === 'undefined') return undefined
  const stored = window.localStorage.getItem('i18nextLng')
  if (stored) return stored  // manual choice — never overwrite
  const nav = (typeof navigator !== 'undefined' && navigator.language) || 'en'
  if (nav.toLowerCase().startsWith('ru')) return 'uk'
  return undefined  // let LanguageDetector pick from navigator for other langs
}

i18next
  .use(LanguageDetector)
  .use(initReactI18next)
  .use(
    resourcesToBackend((language: string, namespace: string) => {
      if (language === 'dev') return Promise.reject('no dev language')
      // Editorial alias: when the user explicitly picks "Русский", we still
      // serve the Ukrainian content bundle. The selector shows "Русский" as
      // a visual choice, but everything below renders in Ukrainian. The
      // entry exists in LANGUAGES so the selector can offer it; only the
      // resource resolution is redirected here.
      const lang = language === 'ru' ? 'uk' : language
      return import(`./locales/${lang}/${namespace}.json`)
    }),
  )
  .init({
    debug: import.meta.env.DEV,
    lng: resolveInitialLng(),
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
