/**
 * Compact <select>-based language switcher for the stats_app navbar.
 *
 * Uses the same i18next localStorage key (`i18nextLng`) as rcongui_public,
 * so switching language here also switches it on /live/* (and vice versa).
 *
 * Only the four "Tier 1" languages with full chrome translations are shown
 * by default (uk / en / de / ru / pl). Others can be enabled in
 * i18n/config.ts → LANGUAGES once translation JSON files exist for them.
 */
import { useTranslation } from 'react-i18next'
import { LANGUAGE_LABELS, LANGUAGES, type Language } from '../i18n/config'

// Subset that currently has full translation JSON. Adding a language is
// just dropping a translation.json under src/i18n/locales/<code>/.
const TRANSLATED: Language[] = ['uk', 'en', 'de', 'ru', 'pl']

export default function LanguageSelector() {
  const { i18n, t } = useTranslation()
  const current = (i18n.resolvedLanguage || i18n.language || 'en').slice(0, 7) as Language
  const available = LANGUAGES.filter((l) => TRANSLATED.includes(l))

  return (
    <label className="text-xs text-zinc-400 flex items-center gap-1" title={t('common.language')}>
      <span aria-hidden>🌐</span>
      <select
        value={available.includes(current) ? current : 'en'}
        onChange={(e) => i18n.changeLanguage(e.target.value)}
        className="bg-zinc-900 border border-zinc-700 rounded px-1 py-0.5 text-xs text-zinc-200 hover:border-amber-500 focus:border-amber-500 focus:outline-none"
      >
        {available.map((lang) => (
          <option key={lang} value={lang}>
            {LANGUAGE_LABELS[lang]}
          </option>
        ))}
      </select>
    </label>
  )
}
