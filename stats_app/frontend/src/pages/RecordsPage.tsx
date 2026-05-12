import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchTopPlayers, fetchBestSingleGame, PlayerRow, SingleGameRow,
  SortKey, SingleGameMetric,
} from '../api/client'

// All-time aggregated leaderboards
const AGGREGATE_CARDS: { key: SortKey; title: string; valueLabel: string }[] = [
  { key: 'kills',     title: 'Найбільше вбивств',       valueLabel: 'K' },
  { key: 'playtime',  title: 'Найбільше часу гри',      valueLabel: 'год' },
  { key: 'combat',    title: 'Combat (бойова еф-сть)',  valueLabel: '' },
  { key: 'support',   title: 'Support',                 valueLabel: '' },
  { key: 'offense',   title: 'Offense',                 valueLabel: '' },
  { key: 'defense',   title: 'Defense',                 valueLabel: '' },
  { key: 'kd_ratio',  title: 'K/D ratio',               valueLabel: '' },
  { key: 'kpm',       title: 'Kills per minute',        valueLabel: '' },
  { key: 'teamkills', title: 'Team kills (анти-топ)',   valueLabel: 'TK' },
  { key: 'matches',   title: 'Найбільше матчів',        valueLabel: '' },
]

// Single-game records (max value in one match)
const SINGLE_CARDS: { metric: SingleGameMetric; title: string }[] = [
  { metric: 'kills',           title: 'Найбільше вбивств за гру' },
  { metric: 'kills_streak',    title: 'Найдовша серія вбивств' },
  { metric: 'combat',          title: 'Combat за гру' },
  { metric: 'support',         title: 'Support за гру' },
  { metric: 'offense',         title: 'Offense за гру' },
  { metric: 'defense',         title: 'Defense за гру' },
  { metric: 'kill_death_ratio', title: 'K/D за гру (single match)' },
  { metric: 'teamkills',       title: 'Найгірший TK за гру' },
]

function formatValue(v: number, key: string): string {
  if (key === 'playtime') return `${Math.floor(v / 3600)} год`
  if (v >= 100000) return v.toLocaleString('uk-UA')
  return String(v)
}

function AggregateCard({ card, rows }: {
  card: typeof AGGREGATE_CARDS[number]
  rows: PlayerRow[]
}) {
  return (
    <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
      <h3 className="text-amber-400 font-semibold text-sm uppercase tracking-wide mb-3">
        {card.title}
      </h3>
      <ol className="space-y-1 text-sm">
        {rows.map((r, i) => {
          const v: any =
            card.key === 'playtime' ? r.total_seconds :
            card.key === 'matches'  ? r.matches_played :
            (r as any)[card.key]
          return (
            <li key={r.steam_id} className="flex items-baseline gap-2">
              <span className="text-zinc-500 w-5 text-right">{i + 1}.</span>
              <Link
                to={`/player/${r.steam_id}`}
                className="flex-1 truncate hover:text-amber-400 transition-colors"
                title={r.name}
              >
                {r.name}
              </Link>
              <span className="font-bold text-zinc-200 tabular-nums">
                {v != null ? formatValue(Number(v), card.key) : '—'}
              </span>
            </li>
          )
        })}
        {rows.length === 0 && <li className="text-zinc-600 text-xs italic">немає даних</li>}
      </ol>
    </div>
  )
}

function SingleGameCard({ card, rows }: {
  card: typeof SINGLE_CARDS[number]
  rows: SingleGameRow[]
}) {
  return (
    <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
      <h3 className="text-emerald-400 font-semibold text-sm uppercase tracking-wide mb-3">
        ⚡ {card.title}
      </h3>
      <ol className="space-y-1 text-sm">
        {rows.map((r, i) => (
          <li key={`${r.steam_id}-${i}`} className="flex items-baseline gap-2">
            <span className="text-zinc-500 w-5 text-right">{i + 1}.</span>
            <Link
              to={`/player/${r.steam_id}`}
              className="flex-1 truncate hover:text-emerald-400 transition-colors"
              title={`${r.name} on ${r.map_name}`}
            >
              {r.name}
            </Link>
            <span className="font-bold text-zinc-200 tabular-nums">
              {Number(r.value).toLocaleString('uk-UA')}
            </span>
          </li>
        ))}
        {rows.length === 0 && <li className="text-zinc-600 text-xs italic">немає даних</li>}
      </ol>
    </div>
  )
}

export default function RecordsPage() {
  const [aggData, setAggData] = useState<Record<string, PlayerRow[]>>({})
  const [singleData, setSingleData] = useState<Record<string, SingleGameRow[]>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Fetch all aggregate leaderboards in parallel
    const aggPromises = AGGREGATE_CARDS.map((c) =>
      fetchTopPlayers({ sort: c.key, limit: 10, min_matches: 50 })
        .then((r) => [c.key, r.results] as const)
        .catch(() => [c.key, []] as const)
    )
    // And single-game records in parallel
    const singlePromises = SINGLE_CARDS.map((c) =>
      fetchBestSingleGame(c.metric, 10)
        .then((r) => [c.metric, r.results] as const)
        .catch(() => [c.metric, []] as const)
    )

    Promise.all([Promise.all(aggPromises), Promise.all(singlePromises)])
      .then(([agg, single]) => {
        setAggData(Object.fromEntries(agg))
        setSingleData(Object.fromEntries(single))
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-7xl mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold mb-1">Рекорди</h1>
        <p className="text-zinc-400 text-sm">
          Топ-10 в кожній категорії за весь час • Single-match record позначено ⚡
        </p>
      </header>

      {loading && <div className="text-zinc-400 py-12 text-center">Завантаження…</div>}

      {!loading && (
        <>
          <section className="mb-8">
            <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3">
              За весь час
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {AGGREGATE_CARDS.map((c) => (
                <AggregateCard key={c.key} card={c} rows={aggData[c.key] ?? []} />
              ))}
            </div>
          </section>

          <section>
            <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3">
              Рекорди за один матч
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {SINGLE_CARDS.map((c) => (
                <SingleGameCard key={c.metric} card={c} rows={singleData[c.metric] ?? []} />
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
