/**
 * Unified header rendered at the top of every rcongui_public page when this
 * app is embedded inside stats_app at /live/*.
 *
 * Goal: when a user clicks `🟢 Зараз` or `📜 Матчі` in stats_app and lands
 * here, the page chrome (background, brand, nav items, colors) is visually
 * IDENTICAL to stats_app's Layout.tsx — so the two SPAs feel like a single
 * site even though cross-app navigation is a full page load.
 *
 * Strategy:
 *   • Mirror stats_app's navbar token-for-token (zinc-950 bg, amber-500
 *     brand, amber-400 active accent, zinc-300 inactive, gap-4 layout).
 *   • Identical item set & order. Sub-nav for live (Поточний матч /
 *     Історія матчів) is folded into the primary nav so everything fits
 *     in a single row.
 *   • Cross-app links use plain <a> because the destinations
 *     (/records/all-time etc.) are routes in stats_app, not rcongui_public.
 *   • Override the body background (rcongui_public's index.html sets a war
 *     scene image inline) and hide the rcongui_public footer so the visual
 *     break between the two apps disappears.
 *   • Active state from `window.location.pathname` so it stays correct
 *     across full page navigations.
 */
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

// ─── Inline language selector — mirrors stats_app/LanguageSelector exactly ─────────
//
// rcongui_public's own DropdownLanguageSelector offers 14 languages and lives
// in its own DOM tree; stats_app's offers 5 with a custom dropdown. Showing
// two different selectors broke the "single site" illusion. This component
// is a self-contained copy of stats_app's variant — same icon, same 5 langs,
// same styling — embedded straight into UnifiedHeader.
//
// Language sync still works through localStorage["i18nextLng"] which both
// SPAs read on init.
const UNIFIED_LANGS = [
  { code: 'uk', name: 'Українська' },
  { code: 'en', name: 'English' },
  { code: 'de', name: 'Deutsch' },
  { code: 'ru', name: 'Русский' },
  { code: 'pl', name: 'Polski' },
] as const

function InlineLanguageSelector() {
  const { i18n, t } = useTranslation()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const current = (i18n.resolvedLanguage || i18n.language || 'en').slice(0, 7)

  useEffect(() => {
    if (!open) return
    const click = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', click)
    document.addEventListener('keydown', key)
    return () => {
      document.removeEventListener('mousedown', click)
      document.removeEventListener('keydown', key)
    }
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="size-8 inline-flex items-center justify-center rounded text-zinc-400 hover:text-amber-400 hover:bg-zinc-800/60 transition-colors"
        title={t('language', { defaultValue: 'Language' })}
        aria-label="Language"
        aria-expanded={open}
      >
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
          {UNIFIED_LANGS.map((l) => {
            const active = current === l.code || current.startsWith(l.code + '-')
            return (
              <button
                key={l.code}
                onClick={() => { i18n.changeLanguage(l.code); setOpen(false) }}
                className={`w-full text-left px-3 py-1.5 text-sm transition-colors ${
                  active
                    ? 'text-amber-400 bg-zinc-800/70 font-medium'
                    : 'text-zinc-200 hover:bg-zinc-800/60 hover:text-amber-300'
                }`}
              >
                {l.name}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

type NavItem = {
  href: string
  label: string
  title?: string
  // Match modes:
  //   exact     — pathname === href
  //   prefix    — pathname.startsWith(href)
  //   livePrefix — pathname.startsWith('/live') but only the /live/ entry, not /live/games
  match: 'exact' | 'prefix' | 'liveCurrent' | 'liveGames'
}

// Identical order to stats_app/frontend/src/components/Layout.tsx — keep in sync.
// Live items come first since they're the most "active" / time-sensitive
// destinations and the user is already on a /live/* page when seeing this.
const NAV: NavItem[] = [
  { href: '/live/',               label: '🟢 Зараз',   title: 'Поточний матч',            match: 'liveCurrent' },
  { href: '/live/games',          label: '📜 Матчі',   title: 'Історія матчів',           match: 'liveGames' },
  // Leaderboard moved off `/` — `/` is now the live current-match page
  // (nginx redirects / → /live/). /leaderboard is the canonical url for
  // the all-time top-players grid.
  { href: '/leaderboard',         label: 'Лідерборд',  match: 'prefix' },
  { href: '/records/all-time',    label: '★ Весь час', title: 'Рекорди за весь час',     match: 'prefix' },
  { href: '/records/single-game', label: '⚡ 1 матч',   title: 'Рекорди в одному матчі',   match: 'prefix' },
  { href: '/achievements',        label: 'Досягнення', match: 'prefix' },
  { href: '/playstyles',          label: '🎭 Стилі',   match: 'prefix' },
  { href: '/compare',             label: 'Порівняння', match: 'prefix' },
  { href: '/hall-of-shame',       label: '💀 Сором',   title: 'Hall of Shame',            match: 'prefix' },
  { href: '/server/countries',    label: '🌍 Карта',   match: 'prefix' },
]

function navClass(active: boolean): string {
  return `text-sm hover:text-amber-400 transition-colors ${
    active ? 'text-amber-400 font-medium' : 'text-zinc-300'
  }`
}

function isActive(item: NavItem, pathname: string): boolean {
  switch (item.match) {
    case 'exact':
      return pathname === item.href
    case 'liveCurrent':
      // "🟢 Зараз" → /live/ — active only on /live or /live/ (current match page)
      return pathname === '/live' || pathname === '/live/'
    case 'liveGames':
      // "📜 Матчі" → /live/games — active on any /live/games/* deep link
      return pathname.startsWith('/live/games')
    case 'prefix':
    default:
      return pathname.startsWith(item.href)
  }
}

export function UnifiedHeader() {
  const pathname =
    typeof window !== 'undefined' ? window.location.pathname : '/live/'

  // Override the war-scene body background that rcongui_public sets inline
  // in index.html so the embedded variant matches stats_app's dark theme.
  // Also force the `dark` class on <html> so rcongui_public's Tailwind
  // dark: variants apply — stats_app is dark-only, so we lock that here
  // and drop the theme toggle entirely.
  useLayoutEffect(() => {
    const prev = {
      bgImage: document.body.style.backgroundImage,
      bgColor: document.body.style.backgroundColor,
    }
    document.body.style.backgroundImage = 'none'
    document.body.style.backgroundColor = '#09090b' // zinc-950
    document.documentElement.classList.add('dark')
    return () => {
      document.body.style.backgroundImage = prev.bgImage
      document.body.style.backgroundColor = prev.bgColor
    }
  }, [])

  return (
    <header className="bg-zinc-950 border-b border-zinc-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-3 flex-wrap">
        {/* Brand → / which nginx redirects to /live/. */}
        <a href="/" className="text-amber-500 font-bold text-lg hover:text-amber-400 transition-colors">
          HLL Stats
        </a>
        {NAV.map((item) => (
          <a
            key={item.href}
            href={item.href}
            title={item.title}
            className={navClass(isActive(item, pathname))}
          >
            {item.label}
          </a>
        ))}
        <div className="ml-auto flex items-center">
          {/* Theme toggle removed — stats_app is dark-only and we lock dark
              mode here too to keep both apps visually consistent.
              Language selector inlined (5 langs, same as stats_app) — see
              InlineLanguageSelector above. */}
          <InlineLanguageSelector />
        </div>
      </div>
    </header>
  )
}
