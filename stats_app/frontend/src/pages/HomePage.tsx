import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchTopPlayers, PlayerRow, SortKey, SortOrder, Period, GameMode,
} from '../api/client'
import FilterBar from '../components/FilterBar'

interface ColumnDef {
  key: SortKey
  label: string
  align?: 'left' | 'right'
  fmt?: (r: PlayerRow) => string | number | null
}

const COLUMNS: ColumnDef[] = [
  { key: 'kills',     label: 'Kills',     align: 'right', fmt: (r) => r.kills },
  { key: 'deaths',    label: 'Deaths',    align: 'right', fmt: (r) => r.deaths },
  { key: 'teamkills', label: 'TK',        align: 'right', fmt: (r) => r.teamkills },
  { key: 'kd_ratio',  label: 'K/D',       align: 'right', fmt: (r) => r.kd_ratio ?? '—' },
  { key: 'kpm',       label: 'KPM',       align: 'right', fmt: (r) => r.kpm ?? '—' },
  { key: 'playtime',  label: 'Час гри',   align: 'right', fmt: (r) => formatPlaytime(r.total_seconds) },
  { key: 'matches',   label: 'Матчів',    align: 'right', fmt: (r) => r.matches_played },
  { key: 'level',     label: 'Lvl',       align: 'right', fmt: (r) => r.level },
]

function formatPlaytime(seconds: number): string {
  if (!seconds) return '—'
  const hours = Math.floor(seconds / 3600)
  if (hours >= 100) return `${hours}h`
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${hours}h ${minutes}m`
}

import LevelBadge from '../components/LevelBadge'
import Avatar from '../components/Avatar'
import CountryFlag from '../components/CountryFlag'

const PAGE_SIZE = 50
const DEFAULT_MIN_MATCHES = 50

export default function HomePage() {
  const [rows, setRows] = useState<PlayerRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [sort, setSort] = useState<SortKey>('kills')
  const [order, setOrder] = useState<SortOrder>('desc')
  const [minMatches, setMinMatches] = useState<number>(DEFAULT_MIN_MATCHES)
  const [period, setPeriod] = useState<Period>('')
  const [gameMode, setGameMode] = useState<GameMode>('')
  const [weapon, setWeapon] = useState<string>('')
  const [weaponClass, setWeaponClass] = useState<string>('')
  const [mapName, setMapName] = useState<string>('')
  const [search, setSearch] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchTopPlayers({
      sort, order, limit: PAGE_SIZE, offset: page * PAGE_SIZE,
      min_matches: minMatches, period: period || undefined,
      weapon: weapon || undefined, map_name: mapName || undefined,
      search: search || undefined,
      game_mode: gameMode || undefined,
      weapon_class: weaponClass || undefined,
    })
      .then((data) => {
        setRows(data.results)
        setTotal(data.total)
      })
      .catch((err) => setError(err?.response?.data?.detail ?? err.message ?? 'unknown error'))
      .finally(() => setLoading(false))
  }, [sort, order, page, minMatches, period, weapon, mapName, search, gameMode, weaponClass])

  const handleSort = (key: SortKey) => {
    if (key === sort) setOrder(order === 'desc' ? 'asc' : 'desc')
    else { setSort(key); setOrder('desc') }
    setPage(0)
  }

  const handleFilterChange = (next: {
    search?: string; period?: Period; gameMode?: GameMode;
    minMatches?: number; weapon?: string; weaponClass?: string; mapName?: string
  }) => {
    if (next.search !== undefined) setSearch(next.search)
    if (next.period !== undefined) setPeriod(next.period)
    if (next.gameMode !== undefined) setGameMode(next.gameMode)
    if (next.minMatches !== undefined) setMinMatches(next.minMatches)
    if (next.weapon !== undefined) setWeapon(next.weapon)
    if (next.weaponClass !== undefined) setWeaponClass(next.weaponClass)
    if (next.mapName !== undefined) setMapName(next.mapName)
    setPage(0)
  }

  const handleReset = () => {
    setMinMatches(DEFAULT_MIN_MATCHES)
    setPeriod('')
    setGameMode('')
    setWeapon('')
    setWeaponClass('')
    setMapName('')
    setSearch('')
    setPage(0)
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)
  const startIdx = page * PAGE_SIZE + 1
  const endIdx = page * PAGE_SIZE + rows.length

  return (
    <div className="max-w-7xl mx-auto p-6">
      <header className="mb-4">
        <h1 className="text-3xl font-bold mb-1">HLL Stats — All time</h1>
        <p className="text-zinc-400 text-sm">
          Топ гравці • <span className="text-zinc-200 font-medium">{total.toLocaleString('uk-UA')}</span> гравців у вибірці
        </p>
      </header>

      <FilterBar
        search={search}
        period={period}
        gameMode={gameMode}
        minMatches={minMatches}
        weapon={weapon}
        weaponClass={weaponClass}
        mapName={mapName}
        onChange={handleFilterChange}
        onReset={handleReset}
      />

      {error && (
        <div className="bg-red-900/30 border border-red-700 text-red-200 p-4 rounded mb-4">
          Помилка: {error}
        </div>
      )}

      <div className="overflow-x-auto bg-zinc-900/40 border border-zinc-800 rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-zinc-800 text-zinc-300 text-xs uppercase">
            <tr>
              <th className="p-3 text-left w-12">#</th>
              <th className="p-3 text-left">Гравець</th>
              {COLUMNS.map((c) => (
                <th
                  key={c.key}
                  onClick={() => handleSort(c.key)}
                  className={`p-3 cursor-pointer select-none hover:bg-zinc-700/50 ${
                    c.align === 'right' ? 'text-right' : 'text-left'
                  } ${sort === c.key ? 'text-amber-400' : ''}`}
                  title={`Сортувати за ${c.label}`}
                >
                  {c.label}
                  {sort === c.key && (
                    <span className="ml-1">{order === 'desc' ? '↓' : '↑'}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className={loading ? 'opacity-50' : ''}>
            {rows.map((r, i) => (
              <tr key={r.steam_id} className="border-t border-zinc-800 hover:bg-zinc-700/20">
                <td className="p-3 text-zinc-500">{page * PAGE_SIZE + i + 1}</td>
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <Avatar url={r.avatar_url} name={r.name} size={28} />
                    <LevelBadge level={r.level} />
                    <CountryFlag iso={r.country} />
                    <Link
                      to={`/player/${r.steam_id}`}
                      className="font-medium hover:text-amber-400 transition-colors"
                    >
                      {r.name}
                    </Link>
                  </div>
                </td>
                {COLUMNS.map((c) => (
                  <td
                    key={c.key}
                    className={`p-3 ${c.align === 'right' ? 'text-right' : ''} ${
                      sort === c.key ? 'text-amber-400 font-medium' : ''
                    }`}
                  >
                    {c.fmt ? c.fmt(r) : '—'}
                  </td>
                ))}
              </tr>
            ))}
            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={2 + COLUMNS.length} className="p-8 text-center text-zinc-500">
                  Немає даних — спробуйте змінити фільтри
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-4 text-sm flex-wrap gap-3">
        <div className="text-zinc-400">
          {total > 0
            ? `${startIdx}–${endIdx} з ${total.toLocaleString('uk-UA')}`
            : 'Завантаження…'}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setPage(0)} disabled={page === 0 || loading}
            className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed">
            « Перша
          </button>
          <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0 || loading}
            className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed">
            ‹ Попер.
          </button>
          <span className="text-zinc-300 px-2">
            Сторінка {page + 1} з {totalPages || 1}
          </span>
          <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1 || loading}
            className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed">
            Наст. ›
          </button>
          <button onClick={() => setPage(totalPages - 1)} disabled={page >= totalPages - 1 || loading}
            className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed">
            Остан. »
          </button>
        </div>
      </div>
    </div>
  )
}
