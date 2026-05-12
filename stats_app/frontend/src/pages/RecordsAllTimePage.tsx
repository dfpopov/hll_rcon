import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchTopPlayers, fetchWeaponClasses,
  PlayerRow, SortKey, Period, GameMode, Side, WeaponClass,
} from '../api/client'
import MiniCompareButton from '../components/MiniCompareButton'

// Per-card min_matches override. Most cards leave it at 0 — no global gate.
// K/D and KPM are ratios that need a floor to filter out single-match outliers.
const AGGREGATE_CARDS: {
  key: SortKey;
  title: string;
  valueFmt: (r: PlayerRow) => string | number;
  min_matches?: number;
}[] = [
  { key: 'kills',     title: 'Найбільше вбивств',       valueFmt: (r) => r.kills },
  { key: 'playtime',  title: 'Найбільше часу гри',      valueFmt: (r) => `${Math.floor(r.total_seconds / 3600)} год` },
  { key: 'combat',    title: 'Combat (бойова еф-сть)',  valueFmt: (r) => (r as any).combat ?? '—' },
  { key: 'support',   title: 'Support',                 valueFmt: (r) => (r as any).support ?? '—' },
  { key: 'offense',   title: 'Offense',                 valueFmt: (r) => (r as any).offense ?? '—' },
  { key: 'defense',   title: 'Defense',                 valueFmt: (r) => (r as any).defense ?? '—' },
  { key: 'kd_ratio',  title: 'K/D ratio (≥30 матчів)',  valueFmt: (r) => r.kd_ratio ?? '—', min_matches: 30 },
  { key: 'kpm',       title: 'KPM (≥30 матчів)',        valueFmt: (r) => r.kpm ?? '—', min_matches: 30 },
  { key: 'teamkills', title: 'Team kills (анти-топ)',   valueFmt: (r) => r.teamkills },
  { key: 'matches',   title: 'Найбільше матчів',        valueFmt: (r) => r.matches_played },
]

function Card({ title, rows, fmt, accent = 'amber' }: {
  title: string
  rows: PlayerRow[]
  fmt: (r: PlayerRow) => string | number
  accent?: string
}) {
  const [expanded, setExpanded] = useState(false)
  const visible = expanded ? rows : rows.slice(0, 5)
  const colorClass = accent === 'emerald' ? 'text-emerald-400' : 'text-amber-400'
  return (
    <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className={`font-semibold text-sm uppercase tracking-wide ${colorClass}`}>
          {title}
        </h3>
        {rows.length > 5 && (
          <button
            onClick={() => setExpanded((e) => !e)}
            className="text-xs text-zinc-500 hover:text-zinc-300 px-2 py-0.5 rounded bg-zinc-800/50"
          >
            {expanded ? '▲ менше' : `▼ ще ${rows.length - 5}`}
          </button>
        )}
      </div>
      <ol className="space-y-1 text-sm">
        {visible.map((r, i) => (
          <li key={r.steam_id} className="flex items-baseline gap-2">
            <span className="text-zinc-500 w-5 text-right">{i + 1}.</span>
            <Link
              to={`/player/${r.steam_id}`}
              className={`flex-1 truncate hover:${colorClass} transition-colors`}
              title={r.name}
            >
              {r.name}
            </Link>
            <MiniCompareButton steam_id={r.steam_id} name={r.name} />
            <span className="font-bold text-zinc-200 tabular-nums">{fmt(r)}</span>
          </li>
        ))}
        {rows.length === 0 && <li className="text-zinc-600 text-xs italic">немає даних</li>}
      </ol>
    </div>
  )
}

export default function RecordsAllTimePage() {
  // Filters subset (no map_name — would be too narrow for records grid).
  // No min_matches slider — most cards run unfiltered, only K/D and KPM
  // cards hardcode a 30-match floor to filter ratio outliers.
  const [period, setPeriod] = useState<Period>('')
  const [gameMode, setGameMode] = useState<GameMode>('')
  const [weaponClass, setWeaponClass] = useState<string>('')
  const [side, setSide] = useState<Side>('')
  // Search is split into local (input value, immediate) + committed (debounced,
  // used in queries) — mirrors the pattern in FilterBar.tsx.
  const [localSearch, setLocalSearch] = useState('')
  const [search, setSearch] = useState('')
  const [classes, setClasses] = useState<WeaponClass[]>([])
  const [aggData, setAggData] = useState<Record<string, PlayerRow[]>>({})
  const [classData, setClassData] = useState<Record<string, PlayerRow[]>>({})
  const [loading, setLoading] = useState(true)

  // Debounce: commit localSearch → search after 300ms of inactivity.
  useEffect(() => {
    if (localSearch === search) return
    const t = setTimeout(() => setSearch(localSearch), 300)
    return () => clearTimeout(t)
  }, [localSearch])  // eslint-disable-line react-hooks/exhaustive-deps

  const filtersKey = useMemo(
    () => `${period}|${gameMode}|${weaponClass}|${search}|${side}`,
    [period, gameMode, weaponClass, search, side],
  )

  useEffect(() => { fetchWeaponClasses().then(setClasses).catch(() => {}) }, [])

  useEffect(() => {
    setLoading(true)
    const baseOpts = {
      limit: 10,
      period: period || undefined,
      game_mode: gameMode || undefined,
      weapon_class: weaponClass || undefined,
      search: search || undefined,
      side: side || undefined,
    }
    // Per-card min_matches: K/D and KPM cards floor at 30, everything else 0.
    const aggPromises = AGGREGATE_CARDS.map((c) =>
      fetchTopPlayers({ ...baseOpts, sort: c.key, min_matches: c.min_matches ?? 0 })
        .then((r) => [c.key, r.results] as const)
        .catch(() => [c.key, []] as const)
    )
    // Per-class top kills (only when classes loaded and no weapon_class filter)
    const classPromises = (weaponClass ? [] : classes).map((cls) =>
      fetchTopPlayers({ ...baseOpts, sort: 'kills', weapon_class: cls.name, limit: 5, min_matches: 0 })
        .then((r) => [cls.name, r.results] as const)
        .catch(() => [cls.name, []] as const)
    )

    Promise.all([Promise.all(aggPromises), Promise.all(classPromises)])
      .then(([agg, cls]) => {
        setAggData(Object.fromEntries(agg))
        setClassData(Object.fromEntries(cls))
      })
      .finally(() => setLoading(false))
  }, [filtersKey, classes.length])  // eslint-disable-line react-hooks/exhaustive-deps

  const handleReset = () => {
    setPeriod('')
    setGameMode('')
    setWeaponClass('')
    setLocalSearch('')
    setSearch('')
    setSide('')
  }

  const hasActive = period || gameMode || weaponClass || search || side

  return (
    <div className="max-w-7xl mx-auto p-6">
      <header className="mb-4">
        <h1 className="text-3xl font-bold mb-1">Рекорди за весь час</h1>
        <p className="text-zinc-400 text-sm">
          Топ-10 в кожній категорії за всю історію матчів • Розгорни картку для топ-N
        </p>
      </header>

      {/* Subset of FilterBar — only what makes sense for records grid */}
      <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 mb-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-grow min-w-[220px] max-w-md">
            <label className="block text-xs text-zinc-400 mb-1">
              Пошук гравця <span className="text-zinc-600">(мін. 2 символи)</span>
            </label>
            <div className="relative">
              <input
                type="text"
                value={localSearch}
                onChange={(e) => setLocalSearch(e.target.value)}
                placeholder="Heartattack, Пакет, BaNnY..."
                className="w-full bg-zinc-800 text-zinc-100 px-3 py-2 pr-8 rounded text-sm placeholder-zinc-500
                           focus:outline-none focus:ring-2 focus:ring-amber-500/50"
              />
              {localSearch && (
                <button
                  onClick={() => setLocalSearch('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-200"
                  title="Очистити"
                >✕</button>
              )}
            </div>
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Період</label>
            <select value={period} onChange={(e) => setPeriod(e.target.value as Period)}
              className="bg-zinc-800 text-zinc-100 px-3 py-2 rounded text-sm min-w-[160px]">
              <option value="">Увесь час</option>
              <option value="7d">Останні 7 днів</option>
              <option value="30d">Останні 30 днів</option>
              <option value="90d">Останні 90 днів</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Сторона / фракція</label>
            <select value={side} onChange={(e) => setSide(e.target.value as Side)}
              className={`px-3 py-2 rounded text-sm min-w-[160px] border ${
                side === 'Allies' || side === 'US' || side === 'GB' || side === 'USSR'
                  ? 'bg-blue-900/60 border-blue-500/50' :
                side === 'Axis' || side === 'Wehrmacht' || side === 'DAK'
                  ? 'bg-red-900/60 border-red-500/50' :
                'bg-zinc-800 border-transparent'
              }`}
              title="Фракція = сторона + театр">
              <option value="">Будь-яка</option>
              <optgroup label="Сторона">
                <option value="Allies">🟦 Allies (усі)</option>
                <option value="Axis">🟥 Axis (усі)</option>
              </optgroup>
              <optgroup label="Фракція (Allies)">
                <option value="US">🇺🇸 US</option>
                <option value="GB">🇬🇧 GB / Commonwealth</option>
                <option value="USSR">☭ USSR</option>
              </optgroup>
              <optgroup label="Фракція (Axis)">
                <option value="Wehrmacht">🦅 Wehrmacht</option>
                <option value="DAK">🐪 DAK (Африка)</option>
              </optgroup>
            </select>
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Режим</label>
            <select value={gameMode} onChange={(e) => setGameMode(e.target.value as GameMode)}
              className={`px-3 py-2 rounded text-sm min-w-[140px] border ${
                gameMode === 'warfare'   ? 'bg-sky-900/60 border-sky-500/50' :
                gameMode === 'offensive' ? 'bg-orange-900/60 border-orange-500/50' :
                gameMode === 'skirmish'  ? 'bg-emerald-900/60 border-emerald-500/50' :
                'bg-zinc-800 border-transparent'
              }`}>
              <option value="">Усі режими</option>
              <option value="warfare">⚔️ Warfare</option>
              <option value="offensive">🗡 Offensive</option>
              <option value="skirmish">🎯 Skirmish</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Клас зброї</label>
            <select value={weaponClass} onChange={(e) => setWeaponClass(e.target.value)}
              className="bg-zinc-800 text-zinc-100 px-3 py-2 rounded text-sm min-w-[180px]">
              <option value="">Усі класи</option>
              {classes.map((c) => <option key={c.name} value={c.name}>{c.name} ({c.count})</option>)}
            </select>
          </div>
          {hasActive && (
            <button onClick={handleReset}
              className="px-3 py-2 rounded bg-zinc-700 hover:bg-zinc-600 text-sm self-end">
              ✕ Скинути
            </button>
          )}
        </div>
      </div>

      {loading && <div className="text-zinc-400 py-8 text-center">Завантаження…</div>}

      {!loading && (
        <>
          <section className="mb-8">
            <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3">
              Аґреговано за весь час
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {AGGREGATE_CARDS.map((c) => (
                <Card key={c.key} title={c.title} rows={aggData[c.key] ?? []} fmt={c.valueFmt} />
              ))}
            </div>
          </section>

          {!weaponClass && (
            <section>
              <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3">
                Топ по класу зброї
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {classes.map((cls) => (
                  <Card key={cls.name} title={`🔫 ${cls.name}`}
                    rows={classData[cls.name] ?? []}
                    fmt={(r) => r.kills}
                    accent="emerald" />
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}
