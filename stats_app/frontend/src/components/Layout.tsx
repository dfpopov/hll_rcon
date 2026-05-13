import { NavLink } from 'react-router-dom'
import { ReactNode } from 'react'
import CompareBar from './CompareBar'
import NavSearch from './NavSearch'

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
  return (
    <div className="min-h-screen flex flex-col">
      <nav className="bg-zinc-950 border-b border-zinc-800 sticky top-0 z-10">
        {/* gap-4 + compact labels (★ / ⚡ icons replace the "Рекорди" prefix)
            keep all 11 items + search on a single row down to ~1280px. */}
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-4 flex-wrap">
          <span className="text-amber-500 font-bold text-lg">HLL Stats</span>
          <NavLink to="/" className={navClass} end>Лідерборд</NavLink>
          <NavLink to="/records/all-time" className={navClass} title="Рекорди за весь час">★ Весь час</NavLink>
          <NavLink to="/records/single-game" className={navClass} title="Рекорди в одному матчі">⚡ 1 матч</NavLink>
          <NavLink to="/achievements" className={navClass}>Досягнення</NavLink>
          <NavLink to="/playstyles" className={navClass}>🎭 Стилі</NavLink>
          <NavLink to="/compare" className={navClass}>Порівняння</NavLink>
          <NavLink to="/hall-of-shame" className={navClass} title="Hall of Shame">💀 Сором</NavLink>
          <NavLink to="/server/countries" className={navClass}>🌍 Карта</NavLink>
          <a href="/live/" className={liveLinkClass} title="Поточний матч">🟢 Зараз</a>
          <a href="/live/games" className={liveLinkClass} title="Історія матчів">📜 Матчі</a>
          <NavSearch />
        </div>
      </nav>
      <main className="flex-1 pb-24">{children}</main>
      <footer className="text-center text-zinc-600 text-xs py-4">
        HLL Stats • All-time stats from CRCON DB
      </footer>
      <CompareBar />
    </div>
  )
}
