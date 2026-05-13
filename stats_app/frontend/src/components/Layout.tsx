import { NavLink } from 'react-router-dom'
import { ReactNode } from 'react'
import CompareBar from './CompareBar'
import NavSearch from './NavSearch'

function navClass({ isActive }: { isActive: boolean }) {
  return `text-sm hover:text-amber-400 transition-colors ${
    isActive ? 'text-amber-400 font-medium' : 'text-zinc-300'
  }`
}

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <nav className="bg-zinc-950 border-b border-zinc-800 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-6 flex-wrap">
          <span className="text-amber-500 font-bold text-lg">HLL Stats</span>
          <NavLink to="/" className={navClass} end>Лідерборд</NavLink>
          <NavLink to="/records/all-time" className={navClass}>Рекорди (весь час)</NavLink>
          <NavLink to="/records/single-game" className={navClass}>Рекорди (1 матч)</NavLink>
          <NavLink to="/achievements" className={navClass}>Досягнення</NavLink>
          <NavLink to="/playstyles" className={navClass}>🎭 Стилі</NavLink>
          <NavLink to="/compare" className={navClass}>Порівняння</NavLink>
          <NavLink to="/hall-of-shame" className={navClass}>💀 Hall of Shame</NavLink>
          <NavLink to="/server/countries" className={navClass}>🌍 Карта</NavLink>
          {/* Single cross-app link into the embedded rcongui_public at /live/.
              From there its own navbar handles "Поточний матч ↔ Історія матчів".
              Plain <a> because /live/ is served by nginx outside React Router. */}
          <a
            href="/live/"
            className="text-sm text-zinc-300 hover:text-amber-400 transition-colors border-l border-zinc-700 pl-4 ml-1"
            title="Поточний матч і історія — rcongui_public"
          >
            🎮 Live
          </a>
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
