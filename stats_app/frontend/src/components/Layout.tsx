import { NavLink } from 'react-router-dom'
import { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import CompareBar from './CompareBar'
import NavSearch from './NavSearch'
import LanguageSelector from './LanguageSelector'

function navClass({ isActive }: { isActive: boolean }) {
  return `text-sm hover:text-amber-400 transition-colors ${
    isActive ? 'text-amber-400 font-medium' : 'text-zinc-300'
  }`
}

// Cross-app links into the embedded rcongui_public at /live/* are plain <a>
// (route is outside React Router). Styled identically to NavLinks so visual
// unity is preserved. The matching `UnifiedHeader` inside rcongui_public
// highlights the same entry amber while you're at /live/*.
const liveLinkClass = 'text-sm text-zinc-300 hover:text-amber-400 transition-colors'

export default function Layout({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  return (
    <div className="min-h-screen flex flex-col">
      <nav className="bg-zinc-950 border-b border-zinc-800 sticky top-0 z-10">
        {/* gap-3 + compact labels keep all items + search + language picker
            on a single row down to ~1280px. English labels are slightly
            wider than Ukrainian, so the tighter spacing helps avoid wraps. */}
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-3 flex-wrap">
          <span className="text-amber-500 font-bold text-lg">{t('nav.brand')}</span>
          {/* Live items first — they're the most "active" / time-sensitive
              destinations and should be top of mind. */}
          <a href="/live/" className={liveLinkClass} title={t('nav.liveCurrentTitle')}>{t('nav.liveCurrent')}</a>
          <a href="/live/games" className={liveLinkClass} title={t('nav.liveGamesTitle')}>{t('nav.liveGames')}</a>
          <NavLink to="/" className={navClass} end>{t('nav.leaderboard')}</NavLink>
          <NavLink to="/records/all-time" className={navClass} title={t('nav.recordsAllTimeTitle')}>{t('nav.recordsAllTime')}</NavLink>
          <NavLink to="/records/single-game" className={navClass} title={t('nav.recordsSingleGameTitle')}>{t('nav.recordsSingleGame')}</NavLink>
          <NavLink to="/achievements" className={navClass}>{t('nav.achievements')}</NavLink>
          <NavLink to="/playstyles" className={navClass}>{t('nav.playstyles')}</NavLink>
          <NavLink to="/compare" className={navClass}>{t('nav.compare')}</NavLink>
          <NavLink to="/hall-of-shame" className={navClass} title={t('nav.hallOfShameTitle')}>{t('nav.hallOfShame')}</NavLink>
          <NavLink to="/server/countries" className={navClass}>{t('nav.worldMap')}</NavLink>
          <NavSearch />
          <LanguageSelector />
        </div>
      </nav>
      <main className="flex-1 pb-24">{children}</main>
      <footer className="text-center text-zinc-600 text-xs py-4">
        {t('nav.brand')} • {t('footer.tagline')}
      </footer>
      <CompareBar />
    </div>
  )
}
