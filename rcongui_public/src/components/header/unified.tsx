/**
 * Unified header rendered at the top of every rcongui_public page when this
 * app is embedded inside stats_app at /live/*.
 *
 * Goal: when a user clicks `🎮 Live` in stats_app and lands here, the page
 * chrome (background, brand, nav items, colors) is visually IDENTICAL to
 * stats_app's Layout.tsx — so the two SPAs feel like a single site even
 * though navigation between them is a full reload.
 *
 * Strategy:
 *   • Mirror stats_app's navbar styling token-for-token (zinc-950 bg,
 *     amber-500 brand, amber-400 active accent, zinc-300 inactive).
 *   • Top row = same items as stats_app, plus the `🎮 Live` entry which is
 *     active when on `/live/*`.
 *   • Second row appears only on `/live/*` and holds rcongui_public's own
 *     sections (Поточний матч / Історія матчів) plus the language/theme
 *     selectors and server status (which were in the old Header).
 *   • Cross-app links use plain `<a>` because the destinations
 *     (/records/all-time etc.) are routes in stats_app, not rcongui_public.
 *     React Router would mis-handle them.
 *   • Active state is computed from `window.location.pathname` so it stays
 *     correct across full page navigations.
 */
import { DropdownLanguageSelector } from '../language-selector'
import { DropdownThemeToggle } from '../theme-toggle'
import { ServerName } from './server-name'
import { ServerStatus } from './server-status'

type NavItem = { href: string; label: string; exact?: boolean }

// Primary nav — identical set & order to stats_app/frontend/src/components/Layout.tsx
const PRIMARY_NAV: NavItem[] = [
  { href: '/', label: 'Лідерборд', exact: true },
  { href: '/records/all-time', label: 'Рекорди (весь час)' },
  { href: '/records/single-game', label: 'Рекорди (1 матч)' },
  { href: '/achievements', label: 'Досягнення' },
  { href: '/playstyles', label: '🎭 Стилі' },
  { href: '/compare', label: 'Порівняння' },
  { href: '/hall-of-shame', label: '💀 Hall of Shame' },
  { href: '/server/countries', label: '🌍 Карта' },
  { href: '/live/', label: '🎮 Live' },
]

// Sub-nav shown only when current URL is under /live/.
const LIVE_SUBNAV: NavItem[] = [
  { href: '/live/', label: 'Поточний матч', exact: true },
  { href: '/live/games', label: 'Історія матчів' },
]

function navClass(active: boolean): string {
  return `text-sm hover:text-amber-400 transition-colors ${
    active ? 'text-amber-400 font-medium' : 'text-zinc-300'
  }`
}

function isActive(item: NavItem, pathname: string): boolean {
  if (item.exact) return pathname === item.href
  // Treat /live/ as active for any /live/* path
  if (item.href === '/live/') return pathname.startsWith('/live')
  return pathname.startsWith(item.href)
}

export function UnifiedHeader() {
  // window.location.pathname is always full path including basename.
  // React Router's useLocation strips basename when basename is set.
  const pathname =
    typeof window !== 'undefined' ? window.location.pathname : '/live/'
  const isOnLive = pathname.startsWith('/live')

  return (
    <header className="bg-zinc-950 border-b border-zinc-800 sticky top-0 z-50">
      {/* Primary row — same items everywhere */}
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-6 flex-wrap">
        <a href="/" className="text-amber-500 font-bold text-lg">
          HLL Stats
        </a>
        {PRIMARY_NAV.map((item) => (
          <a key={item.href} href={item.href} className={navClass(isActive(item, pathname))}>
            {item.label}
          </a>
        ))}
        <div className="ml-auto flex items-center gap-1 [&_button]:size-8">
          <DropdownLanguageSelector />
          <DropdownThemeToggle />
        </div>
      </div>

      {/* Secondary row — only visible while on /live/* */}
      {isOnLive && (
        <div className="border-t border-zinc-800">
          <div className="max-w-7xl mx-auto px-6 py-2 flex items-center gap-4 flex-wrap">
            <span className="text-zinc-500 text-xs uppercase tracking-wider">
              Live
            </span>
            {LIVE_SUBNAV.map((item) => (
              <a key={item.href} href={item.href} className={navClass(isActive(item, pathname))}>
                {item.label}
              </a>
            ))}
            <div className="ml-auto flex items-center gap-3 text-xs text-zinc-400">
              <ServerStatus />
              <span className="truncate max-w-xs">
                <ServerName />
              </span>
            </div>
          </div>
        </div>
      )}
    </header>
  )
}
