import { NavLink } from 'react-router-dom'
import { ReactNode } from 'react'

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <nav className="bg-zinc-950 border-b border-zinc-800 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-6">
          <span className="text-amber-500 font-bold text-lg">HLL Stats</span>
          <NavLink
            to="/"
            className={({ isActive }) =>
              `text-sm hover:text-amber-400 transition-colors ${
                isActive ? 'text-amber-400 font-medium' : 'text-zinc-300'
              }`
            }
            end
          >
            Лідерборд
          </NavLink>
          <NavLink
            to="/records"
            className={({ isActive }) =>
              `text-sm hover:text-amber-400 transition-colors ${
                isActive ? 'text-amber-400 font-medium' : 'text-zinc-300'
              }`
            }
          >
            Рекорди
          </NavLink>
        </div>
      </nav>
      <main className="flex-1">{children}</main>
      <footer className="text-center text-zinc-600 text-xs py-4">
        HLL Stats • All-time stats from CRCON DB
      </footer>
    </div>
  )
}
