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
import { useLayoutEffect } from 'react'
import { DropdownLanguageSelector } from '../language-selector'
import { DropdownThemeToggle } from '../theme-toggle'

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

// Identical to stats_app/frontend/src/components/Layout.tsx — keep in sync.
const NAV: NavItem[] = [
  { href: '/',                    label: 'Лідерборд',  match: 'exact' },
  { href: '/records/all-time',    label: '★ Весь час', title: 'Рекорди за весь час',     match: 'prefix' },
  { href: '/records/single-game', label: '⚡ 1 матч',   title: 'Рекорди в одному матчі',   match: 'prefix' },
  { href: '/achievements',        label: 'Досягнення', match: 'prefix' },
  { href: '/playstyles',          label: '🎭 Стилі',   match: 'prefix' },
  { href: '/compare',             label: 'Порівняння', match: 'prefix' },
  { href: '/hall-of-shame',       label: '💀 Сором',   title: 'Hall of Shame',            match: 'prefix' },
  { href: '/server/countries',    label: '🌍 Карта',   match: 'prefix' },
  { href: '/live/',               label: '🟢 Зараз',   title: 'Поточний матч',            match: 'liveCurrent' },
  { href: '/live/games',          label: '📜 Матчі',   title: 'Історія матчів',           match: 'liveGames' },
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
  // Also hide rcongui_public's amber "Створено CRCON TEAM" footer that
  // peeks below long pages.
  useLayoutEffect(() => {
    const prev = {
      bgImage: document.body.style.backgroundImage,
      bgColor: document.body.style.backgroundColor,
    }
    document.body.style.backgroundImage = 'none'
    document.body.style.backgroundColor = '#09090b' // zinc-950
    return () => {
      document.body.style.backgroundImage = prev.bgImage
      document.body.style.backgroundColor = prev.bgColor
    }
  }, [])

  return (
    <header className="bg-zinc-950 border-b border-zinc-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-4 flex-wrap">
        <a href="/" className="text-amber-500 font-bold text-lg">
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
        <div className="ml-auto flex items-center gap-1 [&_button]:size-8">
          <DropdownLanguageSelector />
          <DropdownThemeToggle />
        </div>
      </div>
    </header>
  )
}
