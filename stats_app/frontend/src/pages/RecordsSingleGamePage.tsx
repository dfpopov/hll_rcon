import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchBestSingleGame, fetchBestSingleGameByClass, SingleGameRow, SingleGameMetric } from '../api/client'
import MiniCompareButton from '../components/MiniCompareButton'
import { formatMapName } from '../components/mapNames'

const CARDS: { metric: SingleGameMetric; title: string; valueFmt?: (n: number) => string }[] = [
  { metric: 'kills',            title: 'Найбільше вбивств за гру' },
  { metric: 'kills_streak',     title: 'Найдовша серія вбивств' },
  { metric: 'combat',           title: 'Combat за гру' },
  { metric: 'support',          title: 'Support за гру' },
  { metric: 'offense',          title: 'Offense за гру' },
  { metric: 'defense',          title: 'Defense за гру' },
  { metric: 'kill_death_ratio', title: 'K/D за гру', valueFmt: (n) => n.toFixed(2) },
  { metric: 'kills_per_minute', title: 'K/хв за гру', valueFmt: (n) => n.toFixed(2) },
  { metric: 'teamkills',        title: 'Найгірший TK за гру' },
  { metric: 'deaths',           title: 'Найгірша гра (deaths)' },
]

// Per-weapon-class single-game cards. Mirrors HLL Records "MOST KILLS IN ONE
// GAME (FLARE GUN/MELEE/MINES/...)" — the narrow classes are the meme-worthy
// ones; generic Rifle/SMG are excluded since they overlap with overall kills.
const CLASS_CARDS: { weapon_class: string; title: string }[] = [
  { weapon_class: 'Sniper Rifle', title: 'Sniper за гру' },
  { weapon_class: 'Machine Gun',  title: 'MG за гру' },
  { weapon_class: 'Anti-Tank',    title: 'AT за гру' },
  { weapon_class: 'Tank Gun',     title: 'Танковий бій за гру' },
  { weapon_class: 'Artillery',    title: 'Артилерія за гру' },
  { weapon_class: 'Mine',         title: 'Міни за гру' },
  { weapon_class: 'Explosive',    title: 'Вибухівка за гру' },
  { weapon_class: 'Flame',        title: 'Вогнемет за гру' },
  { weapon_class: 'Melee',        title: 'Ближній бій за гру' },
]

const CRCON_PUBLIC_BASE = 'http://95.111.230.75:7010'

function SingleGameCard({ title, rows, fmt }: {
  title: string
  rows: SingleGameRow[]
  fmt?: (n: number) => string
}) {
  const [expanded, setExpanded] = useState(false)
  const visible = expanded ? rows : rows.slice(0, 5)
  return (
    <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-emerald-400 font-semibold text-sm uppercase tracking-wide">⚡ {title}</h3>
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
          <li key={`${r.steam_id}-${i}`} className="flex items-baseline gap-2">
            <span className="text-zinc-500 w-5 text-right">{i + 1}.</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1">
                <Link to={`/player/${r.steam_id}`} className="hover:text-emerald-400 transition-colors truncate flex-1">
                  {r.name}
                </Link>
                <MiniCompareButton steam_id={r.steam_id} name={r.name} />
              </div>
              <a href={`${CRCON_PUBLIC_BASE}/games/${r.match_id}`}
                target="_blank" rel="noopener noreferrer"
                className="text-xs text-zinc-500 hover:text-amber-400 block truncate"
                title={r.map_name}>
                {formatMapName(r.map_name)}
              </a>
              {r.top_weapon && (
                <span className="text-[10px] text-zinc-600 truncate block" title={`Most used: ${r.top_weapon}`}>
                  🔫 {r.top_weapon}
                </span>
              )}
            </div>
            <span className="font-bold text-zinc-200 tabular-nums">
              {fmt ? fmt(r.value) : r.value.toLocaleString('uk-UA')}
            </span>
          </li>
        ))}
        {rows.length === 0 && <li className="text-zinc-600 text-xs italic">немає даних</li>}
      </ol>
    </div>
  )
}

export default function RecordsSingleGamePage() {
  const [data, setData] = useState<Record<string, SingleGameRow[]>>({})
  const [classData, setClassData] = useState<Record<string, SingleGameRow[]>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const metricPromises = CARDS.map((c) =>
      fetchBestSingleGame(c.metric, 20)
        .then((r) => [c.metric, r.results] as const)
        .catch(() => [c.metric, []] as const)
    )
    const classPromises = CLASS_CARDS.map((c) =>
      fetchBestSingleGameByClass(c.weapon_class, 10)
        .then((r) => [c.weapon_class, r.results] as const)
        .catch(() => [c.weapon_class, []] as const)
    )
    Promise.all([Promise.all(metricPromises), Promise.all(classPromises)])
      .then(([metrics, classes]) => {
        setData(Object.fromEntries(metrics))
        setClassData(Object.fromEntries(classes))
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-7xl mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold mb-1">Рекорди за один матч</h1>
        <p className="text-zinc-400 text-sm">
          Найвищі досягнення в одному матчі за всю історію • Натисни на карту матчу для деталей
        </p>
      </header>

      {loading && <div className="text-zinc-400 py-8 text-center">Завантаження…</div>}

      {!loading && (
        <>
          <section className="mb-6">
            <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3">Загальні метрики</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {CARDS.map((c) => (
                <SingleGameCard key={c.metric} title={c.title} rows={data[c.metric] ?? []} fmt={c.valueFmt} />
              ))}
            </div>
          </section>
          <section>
            <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3">🔫 За класом зброї</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {CLASS_CARDS.map((c) => (
                <SingleGameCard key={c.weapon_class} title={c.title} rows={classData[c.weapon_class] ?? []} />
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
