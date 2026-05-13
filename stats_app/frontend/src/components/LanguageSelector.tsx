/**
 * Globe-icon dropdown language switcher for the navbar.
 *
 * Style mirrors rcongui_public's DropdownLanguageSelector so the two SPAs
 * feel like one. Native-script labels come from Intl.DisplayNames (e.g.
 * "Українська", "Deutsch", "日本語"). Click-outside and Escape close.
 *
 * Cross-app sync: i18next-browser-languagedetector persists to localStorage
 * key `i18nextLng`, which rcongui_public also reads — switching language
 * here also switches it on /live/* after reload.
 */
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { LANGUAGES, type Language } from '../i18n/config'

// Languages with a translation.json shipped under src/i18n/locales/<code>/.
// Others fall back to English via i18next's fallbackLng. Add more by
// dropping a JSON file and appending the code here.
const TRANSLATED: Language[] = ['uk', 'en', 'de', 'ru', 'pl']

function nativeName(code: string): string {
  // Intl.DisplayNames returns the language name in the target locale itself,
  // so de → "Deutsch", ja → "日本語". Falls back to the code if unsupported.
  try {
    const name = new Intl.DisplayNames([code], { type: 'language' }).of(code)
    if (!name) return code
    return name.charAt(0).toLocaleUpperCase(code) + name.slice(1)
  } catch {
    return code
  }
}

export default function LanguageSelector() {
  const { i18n, t } = useTranslation()
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const current = (i18n.resolvedLanguage || i18n.language || 'en') as Language
  const available = LANGUAGES.filter((l) => TRANSLATED.includes(l))

  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="size-8 inline-flex items-center justify-center rounded text-zinc-400 hover:text-amber-400 hover:bg-zinc-800/60 transition-colors"
        title={t('common.language')}
        aria-label={t('common.language')}
        aria-expanded={open}
      >
        {/* "Languages" icon from lucide-react — matches rcongui_public's
            DropdownLanguageSelector trigger so both apps look identical. */}
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="m5 8 6 6" />
          <path d="m4 14 6-6 2-3" />
          <path d="M2 5h12" />
          <path d="M7 2h1" />
          <path d="m22 22-5-10-5 10" />
          <path d="M14 18h6" />
        </svg>
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl z-50 min-w-[160px] py-1">
          {available.map((lang) => {
            const active = current === lang || current.startsWith(lang + '-')
            return (
              <button
                key={lang}
                onClick={() => { i18n.changeLanguage(lang); setOpen(false) }}
                className={`w-full text-left px-3 py-1.5 text-sm transition-colors ${
                  active
                    ? 'text-amber-400 bg-zinc-800/70 font-medium'
                    : 'text-zinc-200 hover:bg-zinc-800/60 hover:text-amber-300'
                }`}
              >
                {nativeName(lang)}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
